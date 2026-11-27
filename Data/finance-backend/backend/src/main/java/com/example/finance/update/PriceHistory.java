package com.example.finance.update;

import com.example.finance.model.FxRate;
import com.example.finance.model.MetalPrice;
import com.example.finance.model.PricePoint;
import com.example.finance.model.PricePointRepository;
import com.example.finance.model.StockPrice;
import java.time.Instant;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import org.springframework.stereotype.Service;

/**
 * Saves the price of everything per day for the charts (table price_history). A day has one price
 * per item: the latest one, so the 3 runs of a day update the same point.
 */
@Service
public class PriceHistory {
    private final PricePointRepository repo;

    public PriceHistory(PricePointRepository repo) {
        this.repo = repo;
    }

    public void record(FxRate r) {
        record(PricePoint.CURRENCIES, r.currency, r.date, r.buy);
    }

    public void record(StockPrice s) {
        record(PricePoint.STOCKS, s.ticker, s.date, s.close);
    }

    public void record(MetalPrice m) {
        for (PricePoint p : points(m, Instant.now())) record(p.kind, p.item, p.date, p.price);
    }

    /** The gold and silver points of one day (the keys /api/prices uses). */
    static List<PricePoint> points(MetalPrice m, Instant at) {
        List<PricePoint> out = new ArrayList<>();
        add(out, PricePoint.GOLD, "24", m.date, m.gold24, at);
        add(out, PricePoint.GOLD, "21", m.date, m.gold21, at);
        add(out, PricePoint.GOLD, "18", m.date, m.gold18, at);
        add(out, PricePoint.GOLD, "pound", m.date, m.goldPound, at);
        add(out, PricePoint.SILVER, "999", m.date, m.silver999, at);
        add(out, PricePoint.SILVER, "925", m.date, m.silver925, at);
        add(out, PricePoint.SILVER, "800", m.date, m.silver800, at);
        return out;
    }

    private static void add(List<PricePoint> out, String kind, String item, LocalDate date, Double price, Instant at) {
        if (price != null && date != null) out.add(new PricePoint(kind, item, date, price, at));
    }

    public void record(String kind, String item, LocalDate date, Double price) {
        if (price == null || date == null) return;
        PricePoint p = repo.findByKindAndItemAndDate(kind, item, date)
                .orElseGet(() -> new PricePoint(kind, item, date, 0, null));
        p.price = price;
        p.recordedAt = Instant.now();
        repo.save(p);
    }

    /** Points of one item, oldest first; from/to are optional (null = no limit). */
    public List<PricePoint> points(String kind, String item, LocalDate from, LocalDate to) {
        if (from == null && to == null) return repo.findByKindAndItemOrderByDateAsc(kind, item);
        return repo.findByKindAndItemAndDateBetweenOrderByDateAsc(kind, item,
                from != null ? from : LocalDate.of(1900, 1, 1), to != null ? to : LocalDate.of(9999, 12, 31));
    }
}
