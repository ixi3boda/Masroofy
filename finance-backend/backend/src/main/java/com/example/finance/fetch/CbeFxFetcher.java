package com.example.finance.fetch;

import com.example.finance.model.FxRate;
import java.io.IOException;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import org.jsoup.Connection;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * CBE historical exchange rates. Does what the "Show Data" button on the CBE page does:
 * open the page for its cookies and hidden form values, then post the form.
 */
@Component
public class CbeFxFetcher {
    static final String BASE = "https://www.cbe.org.eg";
    static final String PATH = "/en/economic-research/statistics/cbe-exchange-rates/historical-data";
    static final String API = BASE + "/api/statistics/GetHistoricalData";
    private static final DateTimeFormatter FORM_DATE = DateTimeFormatter.ofPattern("dd/MM/yyyy");

    private final List<String> currencies;

    public CbeFxFetcher(@Value("${app.fx.currencies}") List<String> currencies) {
        this.currencies = currencies;
    }

    public List<FxRate> fetch(LocalDate from, LocalDate to) throws IOException {
        Connection.Response page = Http.connect(BASE + PATH).execute();
        Document doc = page.parse();

        Connection post = Http.connect(API)
                .cookies(page.cookies())
                .referrer(BASE + PATH)
                .header("Origin", BASE)
                .header("X-Requested-With", "XMLHttpRequest")
                .data("__RequestVerificationToken", hidden(doc, "__RequestVerificationToken"))
                .data("uid", hidden(doc, "uid"))
                .data("DataSourceId", hidden(doc, "DataSourceId"))
                .data("FallbackUrl", PATH)
                .data("LanguageName", "en")
                .data("FromDateRaw", from.format(FORM_DATE))
                .data("ToDateRaw", to.format(FORM_DATE))
                .data("SubmitAction", "1");
        for (String c : currencies) {
            post.data("SelectedSelectOptions", c).data("multiselect_multipleSelectID", c);
        }
        return parseTable(post.post());
    }

    private static String hidden(Document doc, String name) {
        Element input = doc.selectFirst("input[name=\"" + name + "\"]");
        if (input == null || input.attr("value").isBlank()) {
            throw new IllegalStateException("Could not find " + name + " on the CBE page. "
                    + "The site may have changed, or it blocked the request.");
        }
        return input.attr("value");
    }

    /** Reads the biggest table in the answer; its columns must include date, currency, buy and sell. */
    static List<FxRate> parseTable(Document doc) {
        Element table = doc.select("table").stream()
                .max(Comparator.comparingInt(t -> t.select("tr").size()))
                .orElseThrow(() -> new IllegalStateException("No table in the CBE answer: "
                        + doc.text().substring(0, Math.min(300, doc.text().length()))));

        Elements rows = table.select("tr");
        List<String> header = rows.getFirst().select("th, td").eachText().stream()
                .map(h -> h.trim().toLowerCase(Locale.ROOT)).toList();
        int iDate = column(header, "date"), iCur = column(header, "currency");
        int iBuy = column(header, "buy"), iSell = column(header, "sell");

        List<FxRate> out = new ArrayList<>();
        for (Element row : rows.subList(1, rows.size())) {
            List<String> cells = row.select("td").eachText();
            if (cells.size() < header.size()) continue;
            Double buy = Numbers.parse(cells.get(iBuy)), sell = Numbers.parse(cells.get(iSell));
            if (buy == null || sell == null) continue;
            out.add(new FxRate(Dates.parse(cells.get(iDate), true), cells.get(iCur).trim(), buy, sell));
        }
        return out;
    }

    private static int column(List<String> header, String name) {
        for (int i = 0; i < header.size(); i++) {
            if (header.get(i).contains(name)) return i;
        }
        throw new IllegalStateException("CBE table has no '" + name + "' column: " + header);
    }
}
