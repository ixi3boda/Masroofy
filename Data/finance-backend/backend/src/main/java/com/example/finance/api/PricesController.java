package com.example.finance.api;

import com.example.finance.model.*;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.function.Function;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * GET /api/prices : the current price of everything (no history is kept, so there is no change
 * since the previous day).
 * <pre>
 * {"gold":       {"date":"2026-11-26","pricedAt":"...","ounceUsd":3539.0,"items":[
 *                   {"key":"21","name":"Gold 21K","unit":"g","price":5357.26,"date":"2026-11-26"}]},
 *  "silver":     {... items 999, 925, 800 (EGP per gram)},
 *  "currencies": {"date":"2026-11-26","items":[{"key":"USD","name":"US Dollar","price":54.8438,"buy":54.8438,"sell":54.8438,...}]},
 *  "stocks":     {"date":"2026-11-26","items":[{"key":"COMI.CA","name":"Commercial International Bank","unit":"share","price":126.5,...}]}}
 * </pre>
 * {@code price} is what one unit is worth: per gram for gold and silver (per coin for the gold pound),
 * the EGP rate of one unit of a currency (AllRatesToday daily reference rate, so buy and sell are equal),
 * the last price for a stock.
 */
@RestController
@RequestMapping("/api")
public class PricesController {

    /** One thing with a price. {@code buy}/{@code sell} are only set for currencies. */
    public record Item(String key, String name, String unit, Double price, Double buy, Double sell, LocalDate date) { }

    /** One kind (gold, silver, currencies, stocks). {@code pricedAt} and {@code ounceUsd}: gold and silver only. */
    public record Group(LocalDate date, LocalDateTime pricedAt, Double ounceUsd, String source, List<Item> items) { }

    public record Prices(Group gold, Group silver, Group currencies, Group stocks) { }

    static final Map<String, String> CURRENCY_NAMES = Map.ofEntries(
            Map.entry("USD", "US Dollar"), Map.entry("EUR", "Euro"), Map.entry("GBP", "British Pound"),
            Map.entry("SAR", "Saudi Riyal"), Map.entry("AED", "UAE Dirham"), Map.entry("KWD", "Kuwaiti Dinar"),
            Map.entry("QAR", "Qatari Riyal"), Map.entry("BHD", "Bahraini Dinar"), Map.entry("OMR", "Omani Rial"),
            Map.entry("JOD", "Jordanian Dinar"), Map.entry("CNY", "Chinese Yuan"), Map.entry("JPY", "Japanese Yen"),
            Map.entry("CHF", "Swiss Franc"), Map.entry("CAD", "Canadian Dollar"), Map.entry("AUD", "Australian Dollar"),
            Map.entry("SEK", "Swedish Krona"), Map.entry("DKK", "Danish Krone"), Map.entry("NOK", "Norwegian Krone"));
    /** Shown first, in this order; the rest follow by code. */
    static final List<String> CURRENCY_ORDER = List.of("USD", "EUR", "GBP", "SAR", "AED", "KWD");

    /** A currency's English name: the short names above, else the ISO 4217 name, else the code itself. */
    static String currencyName(String code) {
        String known = CURRENCY_NAMES.get(code);
        if (known != null) return known;
        try {
            return java.util.Currency.getInstance(code).getDisplayName(Locale.ENGLISH);
        } catch (IllegalArgumentException e) {
            return code;
        }
    }

    static final Map<String, String> STOCK_NAMES = Map.of(
            "COMI.CA", "Commercial International Bank", "TMGH.CA", "Talaat Moustafa Group",
            "EAST.CA", "Eastern Company", "SWDY.CA", "Elsewedy Electric", "HRHO.CA", "EFG Holding",
            "ETEL.CA", "Telecom Egypt", "EGX30", "EGX 30 index");

    private final FxRateRepository fx;
    private final StockPriceRepository stocks;
    private final MetalPriceRepository metals;

    public PricesController(FxRateRepository fx, StockPriceRepository stocks, MetalPriceRepository metals) {
        this.fx = fx;
        this.stocks = stocks;
        this.metals = metals;
    }

    @GetMapping("/prices")
    public Prices prices() {
        Optional<MetalPrice> metal = metals.findTopByOrderByDateDesc();
        return new Prices(metalGroup(metal, true), metalGroup(metal, false), currencies(), stocks());
    }

    private Group metalGroup(Optional<MetalPrice> now, boolean gold) {
        if (now.isEmpty()) return new Group(null, null, null, null, List.of());
        MetalPrice m = now.get();
        List<Item> items = new ArrayList<>();
        if (gold) {
            items.add(metal("24", "Gold 24K", "g", m, x -> x.gold24));
            items.add(metal("21", "Gold 21K", "g", m, x -> x.gold21));
            items.add(metal("18", "Gold 18K", "g", m, x -> x.gold18));
            items.add(metal("pound", "Gold pound (8 g of 21K)", "coin", m, x -> x.goldPound));
        } else {
            items.add(metal("999", "Silver 999", "g", m, x -> x.silver999));
            items.add(metal("925", "Silver 925", "g", m, x -> x.silver925));
            items.add(metal("800", "Silver 800", "g", m, x -> x.silver800));
        }
        items.removeIf(i -> i.price() == null);
        return new Group(m.date, m.pricedAt, gold ? m.goldOunceUsd : m.silverOunceUsd, m.source, items);
    }

    private static Item metal(String key, String name, String unit, MetalPrice m, Function<MetalPrice, Double> value) {
        return new Item(key, name, unit, value.apply(m), null, null, m.date);
    }

    private Group currencies() {
        List<FxRate> rates = fx.findAllByOrderByCurrencyAsc();
        if (rates.isEmpty()) return new Group(null, null, null, null, List.of());
        List<Item> items = new ArrayList<>();
        LocalDate newestDay = null;
        for (FxRate r : rates) {
            items.add(new Item(r.currency, currencyName(r.currency), r.currency, r.buy, r.buy, r.sell, r.date));
            if (newestDay == null || r.date.isAfter(newestDay)) newestDay = r.date;
        }
        items.sort(Comparator.comparingInt((Item i) -> {
            int at = CURRENCY_ORDER.indexOf(i.key());
            return at < 0 ? CURRENCY_ORDER.size() : at;
        }).thenComparing(Item::key));
        return new Group(newestDay, null, null, rates.getFirst().source, items);
    }

    private Group stocks() {
        List<Item> items = new ArrayList<>();
        LocalDate newestDay = null;
        for (StockPrice p : stocks.findAllByOrderByTickerAsc()) {
            boolean index = p.ticker.startsWith("EGX");
            items.add(new Item(p.ticker, STOCK_NAMES.getOrDefault(p.ticker, p.ticker), index ? "points" : "share",
                    p.close, null, null, p.date));
            if (newestDay == null || p.date.isAfter(newestDay)) newestDay = p.date;
        }
        // Stocks first, the index last.
        items.sort(Comparator.comparing((Item i) -> i.unit().equals("points")).thenComparing(Item::key));
        return new Group(newestDay, null, null, null, items);
    }
}
