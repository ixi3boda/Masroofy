package com.example.finance;

import static org.assertj.core.api.Assertions.assertThat;

import com.example.finance.api.ApiController;
import com.example.finance.model.FxRate;
import com.example.finance.model.FxRateRepository;
import com.example.finance.model.MetalPriceRepository;
import com.example.finance.model.StockPrice;
import com.example.finance.model.StockPriceRepository;
import com.example.finance.update.HistoryCleanup;
import com.example.finance.update.MetalCalculator;
import com.example.finance.update.UpdateService;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.scheduling.support.CronExpression;
import tools.jackson.databind.json.JsonMapper;

@SpringBootTest(properties = {
        "app.update.on-startup=false",
        "spring.datasource.url=jdbc:h2:mem:test;DB_CLOSE_DELAY=-1",
        "spring.datasource.username=sa",
        "spring.datasource.password="})
class ScheduleAndApiTest {
    @Value("${app.update.cron}") String cron;
    @Autowired ApiController api;
    @Autowired UpdateService updates;
    @Autowired JsonMapper json;
    @Autowired FxRateRepository fxRepo;
    @Autowired StockPriceRepository stockRepo;
    @Autowired MetalPriceRepository metalRepo;
    @Autowired HistoryCleanup cleanup;

    @Test
    void runsAt9_15_21CairoTime() {
        CronExpression c = CronExpression.parse(cron);
        ZoneId cairo = ZoneId.of("Africa/Cairo");
        ZonedDateTime t = LocalDateTime.of(2026, 11, 22, 0, 0).atZone(cairo);
        List<Integer> hours = new java.util.ArrayList<>();
        for (int i = 0; i < 4; i++) {
            t = c.next(t);
            hours.add(t.getHour());
        }
        assertThat(hours).containsExactly(9, 15, 21, 9);
        // Summer time: still 09:00 Cairo (06:00 UTC instead of 07:00 UTC).
        ZonedDateTime summer = c.next(LocalDateTime.of(2026, 7, 1, 0, 0).atZone(cairo));
        assertThat(summer.getHour()).isEqualTo(9);
        assertThat(summer.withZoneSameInstant(ZoneId.of("UTC")).getHour()).isEqualTo(6);
    }

    private List<FxRate> rows(String currency) {
        return fxRepo.findAll().stream().filter(r -> r.currency.equals(currency)).toList();
    }

    @Test
    void aNewerRateReplacesTheSavedOneAndAnOlderOneIsIgnored() {
        LocalDate d = LocalDate.of(2026, 11, 20);
        updates.saveFx(List.of(new FxRate(d, "USD", 47.5, 47.5)));
        updates.saveFx(List.of(new FxRate(d, "USD", 47.55, 47.55)));                // a later run, same day
        updates.saveFx(List.of(new FxRate(d.plusDays(1), "USD", 47.7, 47.7)));      // next day
        updates.saveFx(List.of(new FxRate(d.minusDays(5), "USD", 46.0, 46.0)));     // older: ignored

        assertThat(rows("USD")).singleElement().satisfies(r -> {
            assertThat(r.date).isEqualTo(d.plusDays(1));
            assertThat(r.buy).isEqualTo(47.7);
        });
        assertThat(api.fxLatest()).filteredOn(r -> r.currency.equals("USD")).hasSize(1);
        String out = json.writeValueAsString(rows("USD").getFirst());
        assertThat(out).contains("\"date\":\"2026-11-21\"").doesNotContain("\"id\"");
    }

    private List<ApiController.Point> chart(String kind, String item) {
        return api.history(kind, item, Optional.empty(), Optional.empty()).getBody();
    }

    @Test
    void historyKeepsOnePricePerDayTheLatest() {
        LocalDate d = LocalDate.of(2026, 11, 24);
        updates.saveFx(List.of(new FxRate(d, "ZAR", 3.0, 3.0)));
        updates.saveFx(List.of(new FxRate(d, "ZAR", 3.1, 3.1)));             // later run, same day
        updates.saveFx(List.of(new FxRate(d.plusDays(1), "ZAR", 3.2, 3.2)));
        updates.saveFx(List.of(new FxRate(d.minusDays(3), "ZAR", 9.9, 9.9)));  // older than saved: ignored

        assertThat(chart("currencies", "ZAR")).containsExactly(
                new ApiController.Point(d, 3.1), new ApiController.Point(d.plusDays(1), 3.2));
        assertThat(api.history("currencies", "ZAR", Optional.of(d.plusDays(1)), Optional.empty()).getBody())
                .extracting(ApiController.Point::price).containsExactly(3.2);
        assertThat(api.history("nonsense", "ZAR", Optional.empty(), Optional.empty()).getStatusCode().value()).isEqualTo(400);
        assertThat(chart("currencies", "NOPE")).isEmpty();
    }

    @Test
    void aNewRatesTableDropsCurrenciesItNoLongerHas() {
        LocalDate d = LocalDate.of(2026, 11, 26);
        updates.saveFxSnapshot(List.of(new FxRate(d, "AAA", 1.0, 1.0), new FxRate(d, "BBB", 2.0, 2.0)));
        updates.saveFxSnapshot(List.of(new FxRate(d.plusDays(1), "AAA", 1.1, 1.1)));
        assertThat(rows("BBB")).isEmpty();
        assertThat(rows("AAA")).singleElement().extracting(r -> r.buy).isEqualTo(1.1);
    }

    @Test
    void holidayPriceThatDidNotChangeIsNotSavedAsANewDay() {
        var thu = new StockPrice(LocalDate.of(2026, 11, 19), "ETEL.CA", null, null, null, 40.5, 1000L, "tradingview");
        updates.saveStocks(List.of(thu));
        var holiday = new StockPrice(LocalDate.of(2026, 11, 22), "ETEL.CA", null, null, null, 40.5, 1000L, "tradingview");
        var traded = new StockPrice(LocalDate.of(2026, 11, 22), "ETEL.CA", null, null, null, 41.0, 2500L, "tradingview");
        assertThat(updates.skipUnchanged(List.of(holiday))).isEmpty();
        assertThat(updates.skipUnchanged(List.of(traded))).hasSize(1);

        updates.saveStocks(updates.skipUnchanged(List.of(traded)));
        assertThat(api.stocksLatest()).filteredOn(s -> s.ticker.equals("ETEL.CA")).singleElement()
                .satisfies(s -> assertThat(s.close).isEqualTo(41.0));
    }

    @Test
    void goldAndSilverComeTogetherInOneApi() throws Exception {
        LocalDate day = LocalDate.of(2026, 11, 22);
        updates.saveMetals(List.of(MetalCalculator.calculate(
                day.minusDays(1), LocalDateTime.of(2026, 11, 21, 21, 0), 3500.0, 40.0, 53.81, LocalDate.of(2026, 11, 19))));
        updates.saveMetals(List.of(MetalCalculator.calculate(
                day, LocalDateTime.of(2026, 11, 22, 4, 0), 3530.0, 41.0, 53.81, LocalDate.of(2026, 11, 19))));
        // A later run replaces the saved prices.
        updates.saveMetals(List.of(MetalCalculator.calculate(
                day, LocalDateTime.of(2026, 11, 22, 4, 24, 9), 3539.0, 41.080002, 53.81, LocalDate.of(2026, 11, 19))));

        assertThat(metalRepo.count()).isEqualTo(1);
        // The charts keep both days; the 22nd has its later price.
        assertThat(chart("gold", "21")).extracting(ApiController.Point::date).containsExactly(day.minusDays(1), day);
        assertThat(chart("gold", "24").getLast().price()).isEqualTo(6122.58);
        assertThat(chart("silver", "999")).hasSize(2);
        assertThat(chart("gold", "pound")).hasSize(2);
        String out = json.writeValueAsString(api.metalsLatest().getBody());
        assertThat(out)
                .contains("\"date\":\"2026-11-22\"", "\"pricedAt\":\"2026-11-22T04:24:09\"")
                .contains("\"gold\":{\"ounceUsd\":3539.0,\"24\":")
                .contains("\"silver\":{\"ounceUsd\":41.08,\"999\":")
                .contains("\"usdEgp\":53.81", "\"usdEgpDate\":\"2026-11-19\"", "\"source\":\"gold-api.com\"")
                .doesNotContain("\"id\"");
    }

    @Test
    void daysSavedByEarlierVersionsMoveIntoTheChartsAtStartup() {
        // Rows the way earlier versions kept them: every day, and old CBE names.
        LocalDate d = LocalDate.of(2026, 10, 1);
        fxRepo.saveAll(List.of(new FxRate(d, "CHF", 60.0, 60.0), new FxRate(d.plusDays(1), "CHF", 61.0, 61.0),
                new FxRate(d.plusDays(2), "CHF", 62.0, 62.0), new FxRate(d, "Swiss Franc", 59.0, 59.2)));
        stockRepo.saveAll(List.of(new StockPrice(d, "SWDY.CA", null, null, null, 50.0, 1L, "t"),
                new StockPrice(d.plusDays(1), "SWDY.CA", null, null, null, 51.0, 1L, "t")));

        cleanup.run(null);

        assertThat(rows("Swiss Franc")).isEmpty();
        assertThat(rows("CHF")).singleElement().extracting(r -> r.buy).isEqualTo(62.0);
        assertThat(stockRepo.findAll()).filteredOn(s -> s.ticker.equals("SWDY.CA")).singleElement()
                .extracting(s -> s.close).isEqualTo(51.0);
        // Nothing is lost: every old day is in the charts.
        assertThat(chart("currencies", "CHF")).extracting(ApiController.Point::price).containsExactly(60.0, 61.0, 62.0);
        assertThat(chart("stocks", "SWDY.CA")).extracting(ApiController.Point::price).containsExactly(50.0, 51.0);
        assertThat(chart("currencies", "Swiss Franc")).isEmpty();
        cleanup.run(null);  // a second start adds nothing twice
        assertThat(chart("currencies", "CHF")).hasSize(3);
    }
}
