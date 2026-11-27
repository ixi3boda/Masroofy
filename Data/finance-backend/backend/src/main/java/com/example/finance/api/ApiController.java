package com.example.finance.api;

import com.example.finance.model.*;
import com.example.finance.update.PriceHistory;
import com.example.finance.update.UpdateService;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.format.annotation.DateTimeFormat.ISO;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * Read-only JSON API for the Android app. The /latest endpoints give the current price of
 * everything of their kind; /api/history gives one item's price per day, for charts.
 */
@RestController
@RequestMapping("/api")
public class ApiController {
    private final FxRateRepository fx;
    private final StockPriceRepository stocks;
    private final MetalPriceRepository metals;
    private final UpdateService updates;
    private final PriceHistory history;

    /** One day's price in a chart. */
    public record Point(LocalDate date, double price) { }

    static final Set<String> KINDS = Set.of(PricePoint.GOLD, PricePoint.SILVER, PricePoint.CURRENCIES, PricePoint.STOCKS);

    public ApiController(FxRateRepository fx, StockPriceRepository stocks, MetalPriceRepository metals,
                         UpdateService updates, PriceHistory history) {
        this.history = history;
        this.metals = metals;
        this.fx = fx;
        this.stocks = stocks;
        this.updates = updates;
    }

    /** GET /api/fx/latest : the current rate of every currency. */
    @GetMapping("/fx/latest")
    public List<FxRate> fxLatest() {
        return fx.findAllByOrderByCurrencyAsc();
    }

    /** GET /api/stocks/latest : the current price of every ticker and index. */
    @GetMapping("/stocks/latest")
    public List<StockPrice> stocksLatest() {
        return stocks.findAllByOrderByTickerAsc();
    }

    /** GET /api/metals/latest : current gold and silver prices together (404 before the first). */
    @GetMapping("/metals/latest")
    public ResponseEntity<Metals> metalsLatest() {
        return ResponseEntity.of(metals.findTopByOrderByDateDesc().map(Metals::of));
    }

    /**
     * GET /api/history?kind=gold&item=21&from=2026-01-01&to=2026-11-27 : one item's price per day,
     * oldest first. kind is gold, silver, currencies or stocks; item is the key /api/prices uses
     * (24, 21, 18, pound; 999, 925, 800; USD, EUR, ...; COMI.CA, ..., EGX30). from and to are optional
     * (no from: from the first saved day). 400 for an unknown kind.
     */
    @GetMapping("/history")
    public ResponseEntity<List<Point>> history(@RequestParam String kind, @RequestParam String item,
                                               @RequestParam @DateTimeFormat(iso = ISO.DATE) Optional<LocalDate> from,
                                               @RequestParam @DateTimeFormat(iso = ISO.DATE) Optional<LocalDate> to) {
        if (!KINDS.contains(kind)) return ResponseEntity.badRequest().build();
        return ResponseEntity.ok(history.points(kind, item, from.orElse(null), to.orElse(null)).stream()
                .map(p -> new Point(p.date, p.price)).toList());
    }

    /** GET /api/status : how each source did in the last update run. */
    @GetMapping("/status")
    public List<UpdateService.SourceResult> status() {
        return updates.lastResults();
    }
}
