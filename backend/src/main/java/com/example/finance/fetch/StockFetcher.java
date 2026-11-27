package com.example.finance.fetch;

import com.example.finance.model.StockPrice;
import java.io.IOException;
import java.net.URI;
import java.net.URLEncoder;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.jsoup.Connection;
import org.jsoup.Jsoup;
import org.jsoup.parser.Parser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

/**
 * EGX stocks from Yahoo Finance's chart API, and EGX indices from the EGX website
 * (the same endpoint the Python "egx" package uses). Both are unofficial.
 */
@Component
public class StockFetcher {
    private static final Logger log = LoggerFactory.getLogger(StockFetcher.class);
    static final String YAHOO_CHART = "https://query2.finance.yahoo.com/v8/finance/chart/";
    static final String YAHOO_CRUMB = "https://query2.finance.yahoo.com/v1/test/getcrumb";
    static final String EGX = "https://www.egx.com.eg/WebService.asmx/getIndexChartData";

    private final JsonMapper json;
    // Yahoo answers 429 without a session cookie and a "crumb" token (yfinance does the same).
    private Map<String, String> yahooCookies = Map.of();
    private String yahooCrumb;
    private boolean yahooBlocked;

    public StockFetcher(JsonMapper json) {
        this.json = json;
    }

    /** Call once at the start of each update run: forgets that Yahoo was blocking us last time. */
    public synchronized void newRun() {
        yahooBlocked = false;
    }

    /**
     * Prices for one ticker. When Yahoo blocks us (429), the rest of the tickers in this run are
     * skipped straight away instead of each waiting through retries; the next run tries again.
     */
    public synchronized List<StockPrice> fetchYahoo(String ticker, int days) throws IOException, InterruptedException {
        if (yahooBlocked) {
            throw new IOException("skipped: Yahoo is blocking requests from this connection (429); will try next run");
        }
        long to = Instant.now().getEpochSecond();
        long from = Instant.now().minus(days, ChronoUnit.DAYS).getEpochSecond();
        if (yahooCrumb == null && !yahooSession()) {
            yahooBlocked = true;
            throw new IOException("Yahoo is blocking requests from this connection (429 on its token page); "
                    + "skipping the other tickers until the next run");
        }
        Thread.sleep(1500);  // stay well under Yahoo's rate limit

        for (int attempt = 1; ; attempt++) {
            String url = YAHOO_CHART + ticker + "?period1=" + from + "&period2=" + to
                    + "&interval=1d&events=history"
                    + (yahooCrumb != null ? "&crumb=" + URLEncoder.encode(yahooCrumb, StandardCharsets.UTF_8) : "");
            Connection.Response r = Http.connect(url).cookies(yahooCookies).ignoreHttpErrors(true).execute();
            if (r.statusCode() == 200) {
                return parseYahoo(json.readValue(r.body(), YahooChart.class), ticker);
            }
            boolean limited = r.statusCode() == 429 || r.statusCode() == 401;
            if (limited && attempt == 1) {
                // One retry with a fresh session: an expired crumb also gives 401/429.
                log.info("Yahoo said {} for {}; new session and one retry in 5s", r.statusCode(), ticker);
                Thread.sleep(5_000);
                if (yahooSession()) continue;
            }
            if (limited) {
                yahooBlocked = true;
                yahooCrumb = null;
                throw new IOException("Yahoo is blocking requests from this connection (" + r.statusCode()
                        + "); skipping the other tickers until the next run");
            }
            throw new IOException("Yahoo " + r.statusCode() + " for " + ticker + ": " + snippet(r.body()));
        }
    }

    /** Gets Yahoo's cookies, then the crumb that goes with them. Returns false if Yahoo refused. */
    private boolean yahooSession() {
        Map<String, String> cookies = new HashMap<>();
        for (String page : List.of("https://fc.yahoo.com", "https://finance.yahoo.com/")) {
            try {
                cookies.putAll(Http.connect(page).ignoreHttpErrors(true).execute().cookies());
            } catch (IOException e) {
                log.debug("Yahoo cookie page {} failed: {}", page, e.toString());
            }
            if (!cookies.isEmpty()) break;
        }
        yahooCookies = cookies;
        yahooCrumb = null;
        try {
            Connection.Response r = Http.connect(YAHOO_CRUMB).cookies(cookies).ignoreHttpErrors(true).execute();
            String crumb = r.body().trim();
            if (r.statusCode() == 200 && !crumb.isEmpty() && !crumb.contains("<") && !crumb.contains("{")) {
                yahooCrumb = crumb;
                return true;
            }
            log.warn("No Yahoo crumb ({}): {}", r.statusCode(), snippet(r.body()));
            return r.statusCode() != 429;  // other answers: still try the chart without a crumb
        } catch (IOException e) {
            log.warn("No Yahoo crumb: {}", e.toString());
            return true;
        }
    }

    /**
     * EGX sometimes closes the connection without answering, so try up to three ways:
     * like the Python egx package, then with Java's HTTP/2 client, then as a JSON (AJAX) request.
     */
    public List<StockPrice> fetchEgxIndex(String index, int days) throws IOException, InterruptedException {
        String url = EGX + "?index=" + URLEncoder.encode(index, StandardCharsets.UTF_8) + "&period=" + days + "&gtk=0";
        List<String> problems = new ArrayList<>();
        for (int way = 1; way <= 3; way++) {
            try {
                String body = switch (way) {
                    case 1 -> egxJsoup(url, false);
                    case 2 -> egxJavaHttp(url);
                    default -> egxJsoup(url, true);
                };
                if (way > 1) log.info("EGX answered on try {}", way);
                return parseEgx(readEgxRows(body), index);
            } catch (IOException e) {
                log.info("EGX try {} failed: {}", way, e.toString());
                problems.add("try " + way + ": " + e.getMessage());
                if (way < 3) Thread.sleep(2000);
            }
        }
        throw new IOException("EGX did not answer (" + String.join("; ", problems) + ")");
    }

    private static String egxJsoup(String url, boolean asJson) throws IOException {
        Connection c = Http.connect(url).ignoreHttpErrors(true);
        if (asJson) {
            // ASMX web services only answer in JSON for some clients when asked for it explicitly.
            c.referrer("https://www.egx.com.eg/en/Indices.aspx")
                    .header("Content-Type", "application/json; charset=utf-8")
                    .header("Accept", "application/json, text/javascript, */*; q=0.01")
                    .header("X-Requested-With", "XMLHttpRequest");
        } else {
            c.referrer("https://www.google.com/").header("Accept", "*/*");
        }
        Connection.Response r = c.execute();
        return checked(r.statusCode(), r.contentType(), r.body());
    }

    private static String egxJavaHttp(String url) throws IOException, InterruptedException {
        HttpClient client = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(30))
                .followRedirects(HttpClient.Redirect.NORMAL)
                .build();
        HttpRequest req = HttpRequest.newBuilder(URI.create(url))
                .timeout(Duration.ofSeconds(30))
                .header("User-Agent", Http.USER_AGENT)
                .header("Referer", "https://www.google.com/")
                .header("Accept", "*/*")
                .GET().build();
        HttpResponse<String> r = client.send(req, HttpResponse.BodyHandlers.ofString());
        return checked(r.statusCode(), r.headers().firstValue("content-type").orElse("?"), r.body());
    }

    private static String checked(int status, String contentType, String body) throws IOException {
        if (status != 200 || body == null || body.isBlank()) {
            throw new IOException("answered " + status + " (" + contentType + ") with "
                    + (body == null || body.isBlank() ? "an empty body" : snippet(body)));
        }
        return body;
    }

    /** EGX sends a JSON list, or the same list inside XML: {@code <string>[{...}]</string>}. */
    List<Map<String, Object>> readEgxRows(String body) throws IOException {
        String text = body.trim();
        if (text.startsWith("<")) text = Jsoup.parse(text, Parser.xmlParser()).text().trim();
        if (text.startsWith("{")) {  // {"d": [...]} from ASP.NET JSON services
            Map<String, Object> wrapper = json.readValue(text, new TypeReference<Map<String, Object>>() { });
            Object d = wrapper.getOrDefault("d", List.of());
            text = (d instanceof String s ? s : json.writeValueAsString(d)).trim();
        }
        if (!text.startsWith("[")) throw new IOException("EGX answer is not a list: " + snippet(body));
        return json.readValue(text, new TypeReference<List<Map<String, Object>>>() { });
    }

    private static String snippet(String body) {
        String s = body == null ? "" : body.replaceAll("\\s+", " ").trim();
        return s.length() > 200 ? s.substring(0, 200) + "..." : s;
    }

    static List<StockPrice> parseYahoo(YahooChart chart, String ticker) {
        if (chart.chart() == null || chart.chart().result() == null || chart.chart().result().isEmpty()) {
            throw new IllegalStateException("Yahoo returned no data for " + ticker
                    + (chart.chart() != null ? ": " + chart.chart().error() : ""));
        }
        YahooResult r = chart.chart().result().getFirst();
        if (r.timestamp() == null || r.indicators() == null || r.indicators().quote().isEmpty()) {
            return List.of();
        }
        ZoneId zone = ZoneId.of(r.meta() != null && r.meta().exchangeTimezoneName() != null
                ? r.meta().exchangeTimezoneName() : "Africa/Cairo");
        YahooQuote q = r.indicators().quote().getFirst();
        List<StockPrice> out = new ArrayList<>();
        for (int i = 0; i < r.timestamp().size(); i++) {
            Double close = at(q.close(), i);
            if (close == null) continue;  // a day with no trades
            LocalDate day = Instant.ofEpochSecond(r.timestamp().get(i)).atZone(zone).toLocalDate();
            Long volume = at(q.volume(), i);
            out.add(new StockPrice(day, ticker, at(q.open(), i), at(q.high(), i), at(q.low(), i),
                    close, volume, "yahoo"));
        }
        return out;
    }

    /** EGX answers with rows like {"CDAY": "...", "INDEX_VALUE": 41234.5}. */
    static List<StockPrice> parseEgx(List<Map<String, Object>> rows, String index) {
        List<StockPrice> out = new ArrayList<>();
        for (Map<String, Object> row : rows) {
            Double value = Numbers.parse(row.get("INDEX_VALUE"));
            Object day = row.get("CDAY");
            if (value == null || day == null) continue;
            out.add(new StockPrice(Dates.parse(day.toString(), false), index, null, null, null,
                    value, null, "egx"));
        }
        return out;
    }

    private static <T> T at(List<T> list, int i) {
        return list != null && i < list.size() ? list.get(i) : null;
    }

    // Only the parts of Yahoo's answer that we use.
    record YahooChart(YahooBody chart) { }
    record YahooBody(List<YahooResult> result, Object error) { }
    record YahooResult(YahooMeta meta, List<Long> timestamp, YahooIndicators indicators) { }
    record YahooMeta(String exchangeTimezoneName) { }
    record YahooIndicators(List<YahooQuote> quote) { }
    record YahooQuote(List<Double> open, List<Double> high, List<Double> low,
                      List<Double> close, List<Long> volume) { }
}
