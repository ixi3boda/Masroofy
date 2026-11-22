package com.example.finance.api;

import com.example.finance.model.*;
import com.example.finance.update.UpdateService;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.List;
import java.util.Optional;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.format.annotation.DateTimeFormat.ISO;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * Read-only JSON API for the Android app. Dates are YYYY-MM-DD; "from" and "to" default
 * to the last 30 days.
 */
@RestController
@RequestMapping("/api")
public class ApiController {
    private static final ZoneId CAIRO = ZoneId.of("Africa/Cairo");
    private final FxRateRepository fx;
    private final StockPriceRepository stocks;
    private final MetalPriceRepository metals;
    private final UpdateService updates;

    public ApiController(FxRateRepository fx, StockPriceRepository stocks, MetalPriceRepository metals,
                         UpdateService updates) {
        this.metals = metals;
        this.fx = fx;
        this.stocks = stocks;
        this.updates = updates;
    }

    /** GET /api/fx/latest : the newest rate for every currency. */
    @GetMapping("/fx/latest")
    public List<FxRate> fxLatest() {
        return fx.findTopByOrderByDateDesc().map(r -> fx.findByDateOrderByCurrencyAsc(r.date)).orElse(List.of());
    }

    /** GET /api/fx?currency=US Dollar&from=2026-11-01&to=2026-11-22 (currency optional) */
    @GetMapping("/fx")
    public List<FxRate> fxHistory(@RequestParam Optional<String> currency,
                                  @RequestParam @DateTimeFormat(iso = ISO.DATE) Optional<LocalDate> from,
                                  @RequestParam @DateTimeFormat(iso = ISO.DATE) Optional<LocalDate> to) {
        LocalDate end = to.orElse(LocalDate.now(CAIRO)), start = from.orElse(end.minusDays(30));
        return currency.map(c -> fx.findByCurrencyAndDateBetweenOrderByDateAsc(c, start, end))
                .orElseGet(() -> fx.findByDateBetweenOrderByDateAscCurrencyAsc(start, end));
    }

    /** GET /api/stocks/latest : the newest price for every ticker and index. */
    @GetMapping("/stocks/latest")
    public List<StockPrice> stocksLatest() {
        return stocks.findTickers().stream()
                .flatMap(t -> stocks.findTopByTickerOrderByDateDesc(t).stream()).toList();
    }

    /** GET /api/stocks?ticker=COMI.CA&from=2026-11-01&to=2026-11-22 */
    @GetMapping("/stocks")
    public List<StockPrice> stockHistory(@RequestParam String ticker,
                                         @RequestParam @DateTimeFormat(iso = ISO.DATE) Optional<LocalDate> from,
                                         @RequestParam @DateTimeFormat(iso = ISO.DATE) Optional<LocalDate> to) {
        LocalDate end = to.orElse(LocalDate.now(CAIRO)), start = from.orElse(end.minusDays(30));
        return stocks.findByTickerAndDateBetweenOrderByDateAsc(ticker, start, end);
    }

    /** GET /api/metals/latest : newest gold and silver prices together (404 before the first). */
    @GetMapping("/metals/latest")
    public ResponseEntity<Metals> metalsLatest() {
        return ResponseEntity.of(metals.findTopByOrderByDateDesc().map(Metals::of));
    }

    /** GET /api/metals?from=2026-11-01&to=2026-11-22 : gold and silver, one entry per day. */
    @GetMapping("/metals")
    public List<Metals> metalsHistory(@RequestParam @DateTimeFormat(iso = ISO.DATE) Optional<LocalDate> from,
                                      @RequestParam @DateTimeFormat(iso = ISO.DATE) Optional<LocalDate> to) {
        LocalDate end = to.orElse(LocalDate.now(CAIRO)), start = from.orElse(end.minusDays(30));
        return metals.findByDateBetweenOrderByDateAsc(start, end).stream().map(Metals::of).toList();
    }

    /** GET /api/status : how each source did in the last update run. */
    @GetMapping("/status")
    public List<UpdateService.SourceResult> status() {
        return updates.lastResults();
    }
}
