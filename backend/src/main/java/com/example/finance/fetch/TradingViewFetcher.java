package com.example.finance.fetch;

import com.example.finance.model.StockPrice;
import java.io.IOException;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.jsoup.Connection;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import tools.jackson.databind.json.JsonMapper;

/**
 * Today's EGX prices from TradingView's screener API (unofficial, no key needed).
 * It gives the current price only, which replaces each ticker's saved price.
 */
@Component
public class TradingViewFetcher {
    private static final Logger log = LoggerFactory.getLogger(TradingViewFetcher.class);
    static final String SCAN = "https://scanner.tradingview.com/%s/scan";
    static final List<String> COLUMNS = List.of("open", "high", "low", "close", "volume");
    private static final ZoneId CAIRO = ZoneId.of("Africa/Cairo");
    // EGX trades Sunday to Thursday, 10:00 to 14:30 Cairo time.
    private static final LocalTime MARKET_OPEN = LocalTime.of(10, 0);

    private final JsonMapper json;

    public TradingViewFetcher(JsonMapper json) {
        this.json = json;
    }

    /**
     * Prices for our tickers ("COMI.CA" or "EGX30"). Asks the Egypt screener first, and the
     * global one for anything it did not return (indices may only be listed there).
     */
    public List<StockPrice> fetch(List<String> tickers) throws IOException {
        Map<String, String> bySymbol = new LinkedHashMap<>();  // "EGX:COMI" -> "COMI.CA"
        for (String t : tickers) bySymbol.put(symbol(t), t);

        LocalDate day = sessionDate(ZonedDateTime.now(CAIRO));
        List<StockPrice> out = new ArrayList<>();
        Map<String, String> missing = new LinkedHashMap<>(bySymbol);
        for (String market : List.of("egypt", "global")) {
            if (missing.isEmpty()) break;
            String body = scan(market, List.copyOf(missing.keySet()), COLUMNS);
            for (StockPrice p : parse(body, missing, day)) {
                out.add(p);
                missing.values().remove(p.ticker);
            }
        }
        if (!missing.isEmpty()) log.warn("TradingView has no data for {}", missing.values());
        return out;
    }

    private String scan(String market, List<String> symbols, List<String> columns) throws IOException {
        String request = json.writeValueAsString(Map.of(
                "symbols", Map.of("tickers", symbols, "query", Map.of("types", List.of())),
                "columns", columns));
        Connection.Response r = Http.connect(String.format(SCAN, market))
                .method(Connection.Method.POST)
                .requestBody(request)
                .header("Content-Type", "application/json")
                .header("Origin", "https://www.tradingview.com")
                .referrer("https://www.tradingview.com/")
                .ignoreHttpErrors(true)
                .execute();
        if (r.statusCode() != 200) {
            String b = r.body().replaceAll("\\s+", " ");
            throw new IOException("TradingView " + market + " answered " + r.statusCode() + ": "
                    + b.substring(0, Math.min(200, b.length())));
        }
        return r.body();
    }

    /** Answer: {"data":[{"s":"EGX:COMI","d":[open, high, low, close, volume]}, ...]} */
    @SuppressWarnings("unchecked")
    List<StockPrice> parse(String body, Map<String, String> bySymbol, LocalDate day) {
        Map<String, Object> answer = json.readValue(body, Map.class);
        List<StockPrice> out = new ArrayList<>();
        Object data = answer.get("data");
        if (!(data instanceof List<?> rows)) return out;
        for (Object o : rows) {
            if (!(o instanceof Map<?, ?> row)) continue;
            String ticker = bySymbol.get(String.valueOf(row.get("s")));
            if (ticker == null || !(row.get("d") instanceof List<?> d) || d.size() < COLUMNS.size()) continue;
            Double close = Numbers.parse(d.get(3));
            if (close == null) continue;
            Double volume = Numbers.parse(d.get(4));
            out.add(new StockPrice(day, ticker, Numbers.parse(d.get(0)), Numbers.parse(d.get(1)),
                    Numbers.parse(d.get(2)), close, volume == null ? null : Math.round(volume), "tradingview"));
        }
        return out;
    }

    /** "COMI.CA" -> "EGX:COMI", "EGX30" -> "EGX:EGX30". */
    static String symbol(String ticker) {
        return "EGX:" + ticker.replaceFirst("\\.CA$", "");
    }

    /**
     * The trading day the current price belongs to: before 10:00, or on Friday and Saturday,
     * TradingView still shows the last session's close.
     */
    static LocalDate sessionDate(ZonedDateTime nowCairo) {
        LocalDate d = nowCairo.toLocalDate();
        if (nowCairo.toLocalTime().isBefore(MARKET_OPEN)) d = d.minusDays(1);
        while (d.getDayOfWeek() == DayOfWeek.FRIDAY || d.getDayOfWeek() == DayOfWeek.SATURDAY) {
            d = d.minusDays(1);
        }
        return d;
    }
}
