package com.example.finance.fetch;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.example.finance.model.FxRate;
import com.example.finance.model.StockPrice;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;

class ParsersTest {



    @Test
    void yahooChart() {
        String body = """
            {"chart":{"result":[{"meta":{"exchangeTimezoneName":"Africa/Cairo","currency":"EGP"},
              "timestamp":[1763622000,1763708400,1763794800],
              "indicators":{"quote":[{"open":[100.5,101.0,null],"high":[102.0,103.0,null],
                "low":[99.0,100.0,null],"close":[101.2,102.5,null],"volume":[1200000,900000,null]}]}}],
              "error":null}}""";
        var chart = JsonMapper.builder().build().readValue(body, StockFetcher.YahooChart.class);
        List<StockPrice> rows = StockFetcher.parseYahoo(chart, "COMI.CA");
        assertThat(rows).hasSize(2);  // the day with no close is skipped
        assertThat(rows.getFirst().date).isEqualTo(LocalDate.of(2025, 11, 20));
        assertThat(rows.getFirst().close).isEqualTo(101.2);
        assertThat(rows.getFirst().volume).isEqualTo(1_200_000L);
    }

    @Test
    void egxIndex() {
        List<StockPrice> rows = StockFetcher.parseEgx(List.of(
                Map.of("CDAY", "2026-11-19T00:00:00", "INDEX_VALUE", 41234.5),
                Map.of("CDAY", "11/20/2026 12:00:00 AM", "INDEX_VALUE", "41,300.10")), "EGX30");
        assertThat(rows).extracting(r -> r.date)
                .containsExactly(LocalDate.of(2026, 11, 19), LocalDate.of(2026, 11, 20));
        assertThat(rows.get(1).close).isEqualTo(41300.10);
        assertThat(rows.get(1).open).isNull();
    }

    @Test
    void egxAnswerFormats() throws Exception {
        StockFetcher f = new StockFetcher(JsonMapper.builder().build());
        String list = "[{\"CDAY\":\"2026-11-19T00:00:00\",\"INDEX_VALUE\":41234.5}]";
        String xml = "<?xml version=\"1.0\"?><string xmlns=\"http://tempuri.org/\">" + list + "</string>";
        String wrapped = "{\"d\":" + list + "}";
        String wrappedString = "{\"d\":\"" + list.replace("\"", "\\\"") + "\"}";
        for (String body : List.of(list, xml, wrapped, wrappedString)) {
            assertThat(StockFetcher.parseEgx(f.readEgxRows(body), "EGX30"))
                    .as(body).singleElement().extracting(r -> r.close).isEqualTo(41234.5);
        }
    }

    @Test
    void yahooBlockedSkipsTheRestOfTheRunWithoutWaiting() throws Exception {
        StockFetcher f = new StockFetcher(JsonMapper.builder().build());
        var blocked = StockFetcher.class.getDeclaredField("yahooBlocked");
        blocked.setAccessible(true);
        blocked.set(f, true);
        long start = System.nanoTime();
        assertThatThrownBy(() -> f.fetchYahoo("TMGH.CA", 30)).hasMessageContaining("skipped");
        assertThat(System.nanoTime() - start).isLessThan(1_000_000_000L);  // no network, no retries
        f.newRun();
        assertThat(blocked.get(f)).isEqualTo(false);
    }



    @Test
    void tradingViewAnswer() {
        TradingViewFetcher f = new TradingViewFetcher(JsonMapper.builder().build());
        String body = """
            {"totalCount":3,"data":[
              {"s":"EGX:COMI","d":[100.5,102.0,99.0,101.25,1234567.0]},
              {"s":"EGX:EGX30","d":[41000.1,41500.0,40900.0,41234.5,null]},
              {"s":"EGX:TMGH","d":[null,null,null,null,null]}]}""";
        Map<String, String> bySymbol = Map.of("EGX:COMI", "COMI.CA", "EGX:EGX30", "EGX30", "EGX:TMGH", "TMGH.CA");
        LocalDate day = LocalDate.of(2026, 11, 22);
        List<StockPrice> rows = f.parse(body, bySymbol, day);
        assertThat(rows).extracting(r -> r.ticker).containsExactly("COMI.CA", "EGX30");  // no close -> skipped
        assertThat(rows.getFirst().close).isEqualTo(101.25);
        assertThat(rows.getFirst().volume).isEqualTo(1_234_567L);
        assertThat(rows.getFirst().date).isEqualTo(day);
        assertThat(rows.get(1).volume).isNull();
        assertThat(TradingViewFetcher.symbol("COMI.CA")).isEqualTo("EGX:COMI");
        assertThat(TradingViewFetcher.symbol("EGX30")).isEqualTo("EGX:EGX30");
    }

    @Test
    void tradingDayOfTheCurrentPrice() {
        java.time.ZoneId cairo = java.time.ZoneId.of("Africa/Cairo");
        // Sunday 22 Nov 2026 09:00, before the market opens -> Thursday's close.
        assertThat(TradingViewFetcher.sessionDate(java.time.ZonedDateTime.of(2026, 11, 22, 9, 0, 0, 0, cairo)))
                .isEqualTo(LocalDate.of(2026, 11, 19));
        // Sunday 15:00 and 21:00 -> Sunday.
        assertThat(TradingViewFetcher.sessionDate(java.time.ZonedDateTime.of(2026, 11, 22, 15, 0, 0, 0, cairo)))
                .isEqualTo(LocalDate.of(2026, 11, 22));
        // Friday and Saturday -> Thursday.
        assertThat(TradingViewFetcher.sessionDate(java.time.ZonedDateTime.of(2026, 11, 20, 21, 0, 0, 0, cairo)))
                .isEqualTo(LocalDate.of(2026, 11, 19));
        assertThat(TradingViewFetcher.sessionDate(java.time.ZonedDateTime.of(2026, 11, 21, 15, 0, 0, 0, cairo)))
                .isEqualTo(LocalDate.of(2026, 11, 19));
        // Monday 09:00 -> Sunday.
        assertThat(TradingViewFetcher.sessionDate(java.time.ZonedDateTime.of(2026, 11, 23, 9, 0, 0, 0, cairo)))
                .isEqualTo(LocalDate.of(2026, 11, 22));
    }





    @Test
    void goldApiAnswers() throws Exception {
        GoldApiFetcher f = new GoldApiFetcher(JsonMapper.builder().build());
        // Real answers from https://api.gold-api.com/price/XAU and /XAG on 22 Nov 2026.
        var gold = f.parse("""
            {"currency":"USD","currencySymbol":"$","exchangeRate":1.0,"name":"Gold","price":3539.0,"symbol":"XAU",\
            "updatedAt":"2026-11-22T02:24:09Z","updatedAtReadable":"a few seconds ago"}""", "XAU");
        var silver = f.parse("""
            {"currency":"USD","currencySymbol":"$","exchangeRate":1.0,"name":"Silver","price":41.080002,"symbol":"XAG",\
            "updatedAt":"2026-11-22T02:24:08Z","updatedAtReadable":"a few seconds ago"}""", "XAG");
        assertThat(gold.usd()).isEqualTo(3539.0);
        assertThat(gold.updatedAt()).isEqualTo(java.time.Instant.parse("2026-11-22T02:24:09Z"));
        assertThat(silver.usd()).isEqualTo(41.080002);
        org.assertj.core.api.Assertions.assertThatThrownBy(() -> f.parse("{\"error\":\"x\"}", "XAU"))
                .hasMessageContaining("no price");
        org.assertj.core.api.Assertions.assertThatThrownBy(() -> f.parse("{\"currency\":\"EUR\",\"price\":3000}", "XAU"))
                .hasMessageContaining("not USD");
    }

    @Test
    void egyptianPricesFromWorldPrices() {
        var m = com.example.finance.update.MetalCalculator.calculate(LocalDate.of(2026, 11, 22),
                java.time.LocalDateTime.of(2026, 11, 22, 4, 24), 3539.0, 41.080002, 53.81, LocalDate.of(2026, 11, 19));
        // 3539 * 53.81 / 31.1035 = 6122.58 EGP per gram of pure gold.
        assertThat(m.gold24).isEqualTo(6122.58);
        assertThat(m.gold21).isEqualTo(5357.26);   // 21/24
        assertThat(m.gold18).isEqualTo(4591.94);   // 18/24
        assertThat(m.goldPound).isEqualTo(42858.07); // 8 g of 21K
        // 41.08 * 53.81 / 31.1035 = 71.07 EGP per gram of pure silver.
        assertThat(m.silver999).isEqualTo(71.0);
        assertThat(m.silver925).isEqualTo(65.74);
        assertThat(m.silver800).isEqualTo(56.86);
        assertThat(m.goldOunceUsd).isEqualTo(3539.0);
        assertThat(m.silverOunceUsd).isEqualTo(41.08);
    }

    private static final org.assertj.core.data.Offset<Double> TINY = org.assertj.core.data.Offset.offset(1e-9);

    private static AllRatesFetcher allRates() {
        return new AllRatesFetcher(JsonMapper.builder().build(), "unused", java.time.ZoneId.of("Africa/Cairo"));
    }

    @Test
    void referenceRateIsTurnedIntoEgpPerUnit() throws Exception {
        // Shape of https://allratestoday.com/api/open/reference-rate (values from 26 Nov 2026).
        String body = """
            {"rate_date":"2026-11-26","time":"16:00 London","base":"USD","published_at":"2026-11-26T16:02:26.847Z",
             "rates":[{"base":"USD","quote":"AED","value":3.67305},
                      {"base":"USD","quote":"EGP","value":54.8438},
                      {"base":"USD","quote":"EUR","value":0.911245},
                      {"base":"USD","quote":"JPY","value":159.2975},
                      {"base":"USD","quote":"XXX","value":0},
                      {"base":"EUR","quote":"GBP","value":0.8}],
             "attribution":{"source":"AllRatesToday Daily Reference Rate (16:00 London)",
                            "url":"https://allratestoday.com/reference-rate/"}}""";
        List<FxRate> rows = allRates().parse(body);

        // Every currency is kept, plus USD (the base); EGP itself, zero rates and other bases are not.
        assertThat(rows).extracting(r -> r.currency).containsExactlyInAnyOrder("AED", "EUR", "JPY", "USD");
        assertThat(rows).allSatisfy(r -> {
            assertThat(r.date).isEqualTo(LocalDate.of(2026, 11, 26));
            assertThat(r.source).isEqualTo(AllRatesFetcher.SOURCE);
            assertThat(r.buy).isEqualTo(r.sell);   // one reference rate: no spread
        });
        java.util.function.Function<String, Double> egp =
                c -> rows.stream().filter(r -> r.currency.equals(c)).findFirst().orElseThrow().buy;
        assertThat(egp.apply("USD")).isCloseTo(54.8438, TINY);                         // 1 USD in EGP
        assertThat(egp.apply("EUR")).isCloseTo(60.18557029, org.assertj.core.data.Offset.offset(1e-8));
        assertThat(egp.apply("JPY")).isCloseTo(0.34428538, org.assertj.core.data.Offset.offset(1e-8)); // per 1 yen
        assertThat(egp.apply("AED")).isCloseTo(14.93140578, org.assertj.core.data.Offset.offset(1e-8));
    }

    @Test
    void referenceRateDateFallsBackToPublishedAt() throws Exception {
        String body = """
            {"base":"USD","published_at":"2026-11-26T23:30:00Z","rates":[{"quote":"EGP","value":50},{"quote":"SAR","value":3.75}]}""";
        List<FxRate> rows = allRates().parse(body);
        // 23:30 UTC is already the next day in Cairo.
        assertThat(rows).extracting(r -> r.currency).containsExactlyInAnyOrder("USD", "SAR");
        assertThat(rows.getFirst().date).isEqualTo(LocalDate.of(2026, 11, 27));
        assertThat(rows).filteredOn(r -> r.currency.equals("SAR")).singleElement()
                .extracting(r -> r.buy).isEqualTo(13.33333333);
    }

    @Test
    void referenceRateWithoutRatesOrEgpIsAnError() {
        assertThatThrownBy(() -> allRates().parse("{\"error\":\"x\"}")).hasMessageContaining("no rates");
        assertThatThrownBy(() -> allRates().parse("""
            {"base":"USD","rates":[{"base":"USD","quote":"EUR","value":0.9}]}"""))
                .hasMessageContaining("no rates for EGP");
    }
}
