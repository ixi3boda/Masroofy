package com.example.finance;

import static org.assertj.core.api.Assertions.assertThat;

import com.example.finance.api.ApiController;
import com.example.finance.model.FxRate;
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

    @Test
    void savingTheSameDayTwiceUpdatesTheRow() {
        LocalDate d = LocalDate.of(2026, 11, 20);
        updates.saveFx(List.of(new FxRate(d, "US Dollar", 47.5, 47.6)));
        updates.saveFx(List.of(new FxRate(d, "US Dollar", 47.55, 47.65)));  // a later run, same day

        List<FxRate> rows = api.fxHistory(Optional.of("US Dollar"), Optional.of(d), Optional.of(d));
        assertThat(rows).hasSize(1);
        assertThat(rows.getFirst().buy).isEqualTo(47.55);
        assertThat(api.fxLatest()).hasSize(1);

        String out = json.writeValueAsString(rows.getFirst());
        assertThat(out).contains("\"date\":\"2026-11-20\"").doesNotContain("\"id\"");
    }

    @Test
    void holidayPriceThatDidNotChangeIsNotSavedAsANewDay() {
        var thu = new com.example.finance.model.StockPrice(LocalDate.of(2026, 11, 19), "ETEL.CA",
                null, null, null, 40.5, 1000L, "tradingview");
        updates.saveStocks(List.of(thu));
        var holiday = new com.example.finance.model.StockPrice(LocalDate.of(2026, 11, 22), "ETEL.CA",
                null, null, null, 40.5, 1000L, "tradingview");
        var traded = new com.example.finance.model.StockPrice(LocalDate.of(2026, 11, 22), "ETEL.CA",
                null, null, null, 41.0, 2500L, "tradingview");
        assertThat(updates.skipUnchanged(List.of(holiday))).isEmpty();
        assertThat(updates.skipUnchanged(List.of(traded))).hasSize(1);
    }


    @Test
    void goldAndSilverComeTogetherInOneApi() throws Exception {
        LocalDate day = LocalDate.of(2026, 11, 22);
        updates.saveMetals(List.of(com.example.finance.update.MetalCalculator.calculate(
                day, LocalDateTime.of(2026, 11, 22, 4, 0), 3530.0, 41.0, 53.81, LocalDate.of(2026, 11, 19))));
        // A later run on the same day replaces the day's prices.
        updates.saveMetals(List.of(com.example.finance.update.MetalCalculator.calculate(
                day, LocalDateTime.of(2026, 11, 22, 4, 24, 9), 3539.0, 41.080002, 53.81, LocalDate.of(2026, 11, 19))));

        assertThat(api.metalsHistory(Optional.of(day), Optional.of(day))).hasSize(1);
        String out = json.writeValueAsString(api.metalsLatest().getBody());
        assertThat(out)
                .contains("\"date\":\"2026-11-22\"", "\"pricedAt\":\"2026-11-22T04:24:09\"")
                .contains("\"gold\":{\"ounceUsd\":3539.0,\"24\":")
                .contains("\"silver\":{\"ounceUsd\":41.08,\"999\":")
                .contains("\"usdEgp\":53.81", "\"usdEgpDate\":\"2026-11-19\"", "\"source\":\"gold-api.com\"")
                .doesNotContain("\"id\"");
    }

}
