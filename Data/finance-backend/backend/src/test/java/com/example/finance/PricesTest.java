package com.example.finance;

import static org.assertj.core.api.Assertions.assertThat;

import com.example.finance.api.PricesController;
import com.example.finance.model.FxRate;
import com.example.finance.model.StockPrice;
import com.example.finance.update.MetalCalculator;
import com.example.finance.update.UpdateService;
import java.time.LocalDate;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import tools.jackson.databind.json.JsonMapper;

@SpringBootTest(properties = {
        "app.update.on-startup=false",
        "spring.datasource.url=jdbc:h2:mem:prices;DB_CLOSE_DELAY=-1",
        "spring.datasource.username=sa",
        "spring.datasource.password="})
class PricesTest {
    @Autowired PricesController api;
    @Autowired com.example.finance.api.ApiController api2;
    @Autowired UpdateService updates;
    @Autowired JsonMapper json;

    @Test
    void currentPricesOnly() throws Exception {
        LocalDate thu = LocalDate.of(2026, 11, 26), wed = thu.minusDays(1);
        updates.saveStocks(List.of(
                new StockPrice(wed, "COMI.CA", null, null, null, 120.0, 1000L, "t"),
                new StockPrice(thu, "COMI.CA", null, null, null, 126.0, 1000L, "t"),
                new StockPrice(thu, "EGX30", null, null, null, 41000.0, null, "t"),
                new StockPrice(wed, "ETEL.CA", null, null, null, 40.0, 1000L, "t")));   // no Thursday price
        updates.saveFx(List.of(new FxRate(wed, "USD", 53.0, 53.0), new FxRate(thu, "USD", 53.5, 53.5),
                new FxRate(thu, "EUR", 59.0, 59.0), new FxRate(thu, "SEK", 5.3, 5.3)));
        updates.saveMetals(List.of(
                MetalCalculator.calculate(wed, wed.atTime(21, 0), 3500, 40, 53.5, wed),
                MetalCalculator.calculate(thu, thu.atTime(21, 0), 3535, 41, 53.5, thu)));

        PricesController.Prices p = api.prices();

        // Stocks: one entry per ticker with its newest price; ETEL keeps Wednesday's; the index comes last.
        assertThat(p.stocks().items()).extracting(PricesController.Item::key).containsExactly("COMI.CA", "ETEL.CA", "EGX30");
        var comi = p.stocks().items().getFirst();
        assertThat(comi.name()).isEqualTo("Commercial International Bank");
        assertThat(comi.unit()).isEqualTo("share");
        assertThat(comi.price()).isEqualTo(126.0);
        assertThat(p.stocks().items().get(1).date()).isEqualTo(wed);
        assertThat(p.stocks().items().get(2).unit()).isEqualTo("points");
        assertThat(p.stocks().date()).isEqualTo(thu);

        // Currencies: USD, EUR first; one rate each (Thursday's).
        assertThat(p.currencies().date()).isEqualTo(thu);
        assertThat(p.currencies().items()).extracting(PricesController.Item::key).containsExactly("USD", "EUR", "SEK");
        var usd = p.currencies().items().getFirst();
        assertThat(usd.price()).isEqualTo(53.5);
        assertThat(usd.buy()).isEqualTo(53.5);
        assertThat(usd.sell()).isEqualTo(53.5);
        assertThat(usd.name()).isEqualTo("US Dollar");

        // Gold and silver: Thursday's prices only.
        assertThat(p.gold().items()).extracting(PricesController.Item::key).containsExactly("24", "21", "18", "pound");
        assertThat(p.gold().ounceUsd()).isEqualTo(3535.0);
        assertThat(p.gold().date()).isEqualTo(thu);
        assertThat(p.gold().items().get(1).unit()).isEqualTo("g");
        assertThat(p.gold().items().get(3).unit()).isEqualTo("coin");
        assertThat(p.silver().items()).extracting(PricesController.Item::key).containsExactly("999", "925", "800");
        assertThat(p.silver().ounceUsd()).isEqualTo(41.0);

        // Every saved day is in the charts.
        assertThat(api2.history("stocks", "COMI.CA", java.util.Optional.empty(), java.util.Optional.empty()).getBody())
                .extracting(com.example.finance.api.ApiController.Point::price).containsExactly(120.0, 126.0);
        assertThat(api2.history("currencies", "USD", java.util.Optional.empty(), java.util.Optional.empty()).getBody())
                .hasSize(2);

        String out = json.writeValueAsString(p);
        assertThat(out).contains("\"gold\":{\"date\":\"2026-11-26\"", "\"key\":\"USD\"").doesNotContain("change");
    }
}
