package com.example.finance.update;

import com.example.finance.fetch.CbeFxFetcher;
import com.example.finance.fetch.GoldApiFetcher;
import com.example.finance.fetch.StockFetcher;
import com.example.finance.fetch.TradingViewFetcher;
import com.example.finance.model.*;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/**
 * Fetches every source and saves the rows, replacing rows that already exist for the
 * same day (and currency or ticker). One failing source does not stop the others.
 */
@Service
public class UpdateService {
    private static final Logger log = LoggerFactory.getLogger(UpdateService.class);

    /** What happened to one source in the last run; served at /api/status. */
    public record SourceResult(String source, boolean ok, int rows, String error, Instant at) { }

    private final CbeFxFetcher fx;
    private final StockFetcher stocks;
    private final TradingViewFetcher tradingView;
    private final boolean tradingViewEnabled;
    private final GoldApiFetcher goldApi;
    private final FxRateRepository fxRepo;
    private final StockPriceRepository stockRepo;
    private final MetalPriceRepository metalRepo;
    private final ZoneId zone;
    private final int fxDays;
    private final int stockDays;
    private final List<String> tickers;
    private final List<String> indices;
    private final Map<String, SourceResult> lastResults = new LinkedHashMap<>();

    public UpdateService(CbeFxFetcher fx, StockFetcher stocks, TradingViewFetcher tradingView, GoldApiFetcher goldApi,
                         FxRateRepository fxRepo, StockPriceRepository stockRepo, MetalPriceRepository metalRepo,
                         @Value("${app.update.zone}") ZoneId zone,
                         @Value("${app.fx.days}") int fxDays,
                         @Value("${app.stocks.days}") int stockDays,
                         @Value("${app.stocks.tickers}") List<String> tickers,
                         @Value("${app.stocks.indices}") List<String> indices,
                         @Value("${app.stocks.tradingview:true}") boolean tradingViewEnabled) {
        this.fx = fx;
        this.stocks = stocks;
        this.tradingView = tradingView;
        this.tradingViewEnabled = tradingViewEnabled;
        this.goldApi = goldApi;
        this.fxRepo = fxRepo;
        this.stockRepo = stockRepo;
        this.metalRepo = metalRepo;
        this.zone = zone;
        this.fxDays = fxDays;
        this.stockDays = stockDays;
        this.tickers = tickers;
        this.indices = indices;
    }

    /** Runs all sources. synchronized: the startup run and a scheduled run never overlap. */
    public synchronized void updateAll() {
        log.info("Update started");
        LocalDate today = LocalDate.now(zone);
        run("fx", () -> saveFx(fx.fetch(today.minusDays(fxDays), today)));
        stocks.newRun();
        for (String t : tickers) {
            run("stock " + t, () -> saveStocks(stocks.fetchYahoo(t, stockDays)));
        }
        for (String i : indices) {
            run("index " + i, () -> saveStocks(stocks.fetchEgxIndex(i, stockDays)));
        }
        // Today's prices for every ticker and index in one request. Runs after Yahoo/EGX,
        // which (when they work) also fill in the days before.
        if (tradingViewEnabled) {
            List<String> all = new ArrayList<>(tickers);
            all.addAll(indices);
            run("stocks today (TradingView)", () -> saveStocks(skipUnchanged(tradingView.fetch(all))));
        }
        run("gold & silver (gold-api.com)", this::saveGoldApi);
        log.info("Update finished");
    }

    public synchronized List<SourceResult> lastResults() {
        return List.copyOf(lastResults.values());
    }

    private interface Job { int call() throws Exception; }

    private void run(String source, Job job) {
        try {
            int rows = job.call();
            if (rows == 0) log.warn("{}: nothing fetched; keeping existing data", source);
            else log.info("{}: {} rows saved", source, rows);
            lastResults.put(source, new SourceResult(source, rows > 0, rows, rows == 0 ? "no rows" : null, Instant.now()));
        } catch (Exception e) {
            log.error("{} failed: {}", source, e.toString());
            lastResults.put(source, new SourceResult(source, false, 0, e.toString(), Instant.now()));
        }
    }

    /**
     * On a market holiday TradingView still shows the last session's price; that is not a new day,
     * so drop rows whose close and volume equal the ticker's last saved earlier day.
     */
    public List<StockPrice> skipUnchanged(List<StockPrice> rows) {
        List<StockPrice> out = new ArrayList<>();
        for (StockPrice r : rows) {
            var last = stockRepo.findTopByTickerAndDateBeforeOrderByDateDesc(r.ticker, r.date);
            boolean same = last.isPresent() && last.get().close == r.close
                    && java.util.Objects.equals(last.get().volume, r.volume);
            if (same) log.info("{}: same price as {}, probably a market holiday; not saved", r.ticker, last.get().date);
            else out.add(r);
        }
        return out;
    }

    /**
     * World gold (XAU) and silver (XAG) prices from gold-api.com, turned into EGP per gram with the
     * newest CBE dollar rate. Saved under the Cairo date of the gold price; a day keeps its latest prices.
     */
    public int saveGoldApi() throws java.io.IOException {
        FxRate usd = fxRepo.findTopByCurrencyOrderByDateDesc("US Dollar")
                .orElseThrow(() -> new IllegalStateException("No CBE US Dollar rate saved yet"));
        GoldApiFetcher.Quote gold = goldApi.gold();
        GoldApiFetcher.Quote silver = goldApi.silver();
        java.time.LocalDateTime at = java.time.LocalDateTime.ofInstant(gold.updatedAt(), zone);
        double rate = (usd.buy + usd.sell) / 2;
        MetalPrice m = MetalCalculator.calculate(at.toLocalDate(), at, gold.usd(), silver.usd(), rate, usd.date);
        log.info("gold ${} / silver ${} per ounce x EGP {} (CBE {}) -> gold 21K {}, silver 999 {} per gram",
                gold.usd(), silver.usd(), rate, usd.date, m.gold21, m.silver999);
        return saveMetals(List.of(m));
    }

    public int saveMetals(List<MetalPrice> rows) {
        Instant now = Instant.now();
        for (MetalPrice r : rows) {
            metalRepo.findByDate(r.date).ifPresent(old -> r.id = old.id);
            r.fetchedAt = now;
            metalRepo.save(r);
        }
        return rows.size();
    }

    public int saveFx(List<FxRate> rows) {
        Instant now = Instant.now();
        for (FxRate r : rows) {
            fxRepo.findByDateAndCurrency(r.date, r.currency).ifPresent(old -> r.id = old.id);
            r.fetchedAt = now;
            fxRepo.save(r);
        }
        return rows.size();
    }

    public int saveStocks(List<StockPrice> rows) {
        Instant now = Instant.now();
        for (StockPrice r : rows) {
            stockRepo.findByDateAndTicker(r.date, r.ticker).ifPresent(old -> r.id = old.id);
            r.fetchedAt = now;
            stockRepo.save(r);
        }
        return rows.size();
    }
}
