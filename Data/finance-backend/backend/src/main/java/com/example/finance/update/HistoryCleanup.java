package com.example.finance.update;

import com.example.finance.model.FxRate;
import com.example.finance.model.FxRateRepository;
import com.example.finance.model.MetalPrice;
import com.example.finance.model.MetalPriceRepository;
import com.example.finance.model.PricePoint;
import com.example.finance.model.PricePointRepository;
import com.example.finance.model.StockPrice;
import com.example.finance.model.StockPriceRepository;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * Runs once at startup, before the first update. The tables fx_rates, stock_prices and metal_prices
 * hold only the newest price of each thing; the per-day prices for the charts are in price_history.
 * Earlier versions kept every day in those tables, so this first copies any day that price_history
 * does not have yet into it (nothing is lost), then deletes the old days from them. Rows under old
 * CBE names ("US Dollar", ...) are deleted. Does nothing when there is nothing to do.
 */
@Component
public class HistoryCleanup implements ApplicationRunner {
    private static final Logger log = LoggerFactory.getLogger(HistoryCleanup.class);
    private final FxRateRepository fx;
    private final StockPriceRepository stocks;
    private final MetalPriceRepository metals;
    private final PricePointRepository history;

    public HistoryCleanup(FxRateRepository fx, StockPriceRepository stocks, MetalPriceRepository metals,
                          PricePointRepository history) {
        this.fx = fx;
        this.stocks = stocks;
        this.metals = metals;
        this.history = history;
    }

    @Override
    @Transactional
    public void run(ApplicationArguments args) {
        long old = fx.countOlderRates() + stocks.countOlderPrices() + metals.countOlderPrices();
        if (old > 0 || history.count() == 0) {
            int copied = copyIntoHistory();
            if (copied > 0) log.info("Copied {} saved prices into price_history for the charts", copied);
        }
        int fxRows = fx.deleteNonCodeCurrencies() + fx.deleteOlderRates();
        int stockRows = stocks.deleteOlderPrices();
        int metalRows = metals.deleteOlderPrices();
        if (fxRows + stockRows + metalRows > 0) {
            log.info("Removed old days from the current-price tables: {} exchange rates, {} stock prices, "
                    + "{} gold/silver days (kept in price_history)", fxRows, stockRows, metalRows);
        }
    }

    /** Adds every saved price whose day price_history does not have yet. Returns how many. */
    private int copyIntoHistory() {
        Set<String> have = new HashSet<>();
        for (Object[] k : history.findAllKeys()) have.add(id(k[0], k[1], k[2]));
        List<PricePoint> add = new ArrayList<>();
        for (FxRate r : fx.findAll()) {
            if (r.currency == null || !r.currency.matches("[A-Z]{3}")) continue;  // old CBE names
            addIfNew(add, have, new PricePoint(PricePoint.CURRENCIES, r.currency, r.date, r.buy, r.fetchedAt));
        }
        for (StockPrice s : stocks.findAll()) {
            addIfNew(add, have, new PricePoint(PricePoint.STOCKS, s.ticker, s.date, s.close, s.fetchedAt));
        }
        for (MetalPrice m : metals.findAll()) {
            for (PricePoint p : PriceHistory.points(m, m.fetchedAt)) addIfNew(add, have, p);
        }
        history.saveAll(add);
        return add.size();
    }

    private static void addIfNew(List<PricePoint> add, Set<String> have, PricePoint p) {
        if (p.date != null && have.add(id(p.kind, p.item, p.date))) add.add(p);
    }

    private static String id(Object kind, Object item, Object date) {
        return kind + "|" + item + "|" + date;
    }
}
