package com.example.finance.update;

import com.example.finance.fetch.AllRatesFetcher;
import com.example.finance.fetch.GoldApiFetcher;
import com.example.finance.fetch.StockFetcher;
import com.example.finance.fetch.TradingViewFetcher;
import com.example.finance.model.*;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/**
 * Fetches every source and saves the newest price of everything: one row per currency, one per
 * ticker and one for gold and silver. A newer price replaces the saved one; an older one is ignored.
 * Each saved price is also kept per day in {@link PriceHistory} for the charts.
 * One failing source does not stop the others.
 */
@Service
public class UpdateService {
    private static final Logger log = LoggerFactory.getLogger(UpdateService.class);

    /** What happened to one source in the last run; served at /api/status. */
    public record SourceResult(String source, boolean ok, int rows, String error, Instant at) { }

    private final AllRatesFetcher allRates;
    private final StockFetcher stocks;
    private final TradingViewFetcher tradingView;
    private final boolean tradingViewEnabled;
    private final GoldApiFetcher goldApi;
    private final FxRateRepository fxRepo;
    private final StockPriceRepository stockRepo;
    private final MetalPriceRepository metalRepo;
    private final PriceHistory history;
    private final ZoneId zone;
    private final int stockDays;
    private final List<String> tickers;
    private final List<String> indices;
    private final Map<String, SourceResult> lastResults = new LinkedHashMap<>();

    public UpdateService(AllRatesFetcher allRates, StockFetcher stocks, TradingViewFetcher tradingView, GoldApiFetcher goldApi,
                         FxRateRepository fxRepo, StockPriceRepository stockRepo, MetalPriceRepository metalRepo,
                         PriceHistory history,
                         @Value("${app.update.zone}") ZoneId zone,
                         @Value("${app.stocks.days}") int stockDays,
                         @Value("${app.stocks.tickers}") List<String> tickers,
                         @Value("${app.stocks.indices}") List<String> indices,
                         @Value("${app.stocks.tradingview:true}") boolean tradingViewEnabled) {
        this.allRates = allRates;
        this.stocks = stocks;
        this.tradingView = tradingView;
        this.tradingViewEnabled = tradingViewEnabled;
        this.goldApi = goldApi;
        this.fxRepo = fxRepo;
        this.stockRepo = stockRepo;
        this.metalRepo = metalRepo;
        this.history = history;
        this.zone = zone;
        this.stockDays = stockDays;
        this.tickers = tickers;
        this.indices = indices;
    }

    /** Runs all sources. synchronized: the startup run and a scheduled run never overlap. */
    public synchronized void updateAll() {
        log.info("Update started");
        // Exchange rates: every currency from the AllRatesToday daily reference rate (EGP per 1 unit).
        run("fx (AllRatesToday)", () -> saveFxSnapshot(allRates.fetch()));
        stocks.newRun();
        for (String t : tickers) {
            run("stock " + t, () -> saveStocks(newestPerTicker(stocks.fetchYahoo(t, stockDays))));
        }
        for (String i : indices) {
            run("index " + i, () -> saveStocks(newestPerTicker(stocks.fetchEgxIndex(i, stockDays))));
        }
        // Today's prices for every ticker and index in one request. Runs after Yahoo/EGX, so it
        // replaces their (usually older) last close when it has a newer one.
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

    /** Yahoo and EGX answer with several days; only the newest of each ticker is kept. */
    static List<StockPrice> newestPerTicker(List<StockPrice> rows) {
        Map<String, StockPrice> newest = new LinkedHashMap<>();
        for (StockPrice r : rows) {
            newest.merge(r.ticker, r, (a, b) -> b.date.isAfter(a.date) ? b : a);
        }
        return new ArrayList<>(newest.values());
    }

    /**
     * On a market holiday TradingView still shows the last session's price; that is not a new day,
     * so drop rows whose close and volume equal the ticker's saved price of an earlier day
     * (the saved row then keeps its real trading date).
     */
    public List<StockPrice> skipUnchanged(List<StockPrice> rows) {
        List<StockPrice> out = new ArrayList<>();
        for (StockPrice r : rows) {
            var last = stockRepo.findTopByTickerOrderByDateDesc(r.ticker).filter(p -> p.date.isBefore(r.date));
            boolean same = last.isPresent() && last.get().close == r.close
                    && java.util.Objects.equals(last.get().volume, r.volume);
            if (same) log.info("{}: same price as {}, probably a market holiday; not saved", r.ticker, last.get().date);
            else out.add(r);
        }
        return out;
    }

    /**
     * World gold (XAU) and silver (XAG) prices from gold-api.com, turned into EGP per gram with the
     * current dollar rate. Replaces the saved prices; pricedAt is when gold-api.com updated gold (Cairo time).
     */
    public int saveGoldApi() throws java.io.IOException {
        FxRate usd = fxRepo.findTopByCurrencyOrderByDateDesc("USD")
                .orElseThrow(() -> new IllegalStateException("No US Dollar rate saved yet"));
        GoldApiFetcher.Quote gold = goldApi.gold();
        GoldApiFetcher.Quote silver = goldApi.silver();
        java.time.LocalDateTime at = java.time.LocalDateTime.ofInstant(gold.updatedAt(), zone);
        double rate = (usd.buy + usd.sell) / 2;
        MetalPrice m = MetalCalculator.calculate(at.toLocalDate(), at, gold.usd(), silver.usd(), rate, usd.date);
        log.info("gold ${} / silver ${} per ounce x EGP {} ({}) -> gold 21K {}, silver 999 {} per gram",
                gold.usd(), silver.usd(), rate, usd.date, m.gold21, m.silver999);
        return saveMetals(List.of(m));
    }


    /** Replaces the saved gold and silver prices unless they are for a later day. Returns the number of rows given. */
    public int saveMetals(List<MetalPrice> rows) {
        Instant now = Instant.now();
        for (MetalPrice r : rows) {
            var old = metalRepo.findTopByOrderByDateDesc();
            if (old.isPresent() && old.get().date.isAfter(r.date)) continue;  // keep the newer one
            old.ifPresent(o -> r.id = o.id);
            r.fetchedAt = now;
            metalRepo.save(r);
            history.record(r);
        }
        return rows.size();
    }

    /** Replaces each currency's saved rate unless the saved one is for a later day. Returns the number of rows given. */
    public int saveFx(List<FxRate> rows) {
        Instant now = Instant.now();
        for (FxRate r : rows) {
            var old = fxRepo.findTopByCurrencyOrderByDateDesc(r.currency);
            if (old.isPresent() && old.get().date.isAfter(r.date)) continue;
            old.ifPresent(o -> r.id = o.id);
            r.fetchedAt = now;
            fxRepo.save(r);
            history.record(r);
        }
        return rows.size();
    }

    /**
     * A full table from the rates API: saves it and deletes currencies it no longer has, so the
     * saved rates are exactly the newest table.
     */
    public int saveFxSnapshot(List<FxRate> rows) {
        saveFx(rows);
        if (rows.isEmpty()) return 0;
        Set<String> codes = new HashSet<>();
        for (FxRate r : rows) codes.add(r.currency);
        List<FxRate> gone = fxRepo.findAll().stream().filter(r -> !codes.contains(r.currency)).toList();
        if (!gone.isEmpty()) {
            log.info("AllRatesToday no longer has {}; deleted", gone.stream().map(r -> r.currency).toList());
            fxRepo.deleteAll(gone);
        }
        return rows.size();
    }

    /** Replaces each ticker's saved price unless the saved one is for a later day. Returns the number of rows given. */
    public int saveStocks(List<StockPrice> rows) {
        Instant now = Instant.now();
        for (StockPrice r : rows) {
            var old = stockRepo.findTopByTickerOrderByDateDesc(r.ticker);
            if (old.isPresent() && old.get().date.isAfter(r.date)) continue;
            old.ifPresent(o -> r.id = o.id);
            r.fetchedAt = now;
            stockRepo.save(r);
            history.record(r);
        }
        return rows.size();
    }
}
