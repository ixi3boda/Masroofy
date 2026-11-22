package com.example.finance.api;

import com.example.finance.model.MetalPrice;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * One day of gold and silver prices as the API serves them:
 * <pre>
 * {"date":"2026-11-22","pricedAt":"2026-11-22T04:24:09",
 *  "gold":  {"ounceUsd":3539.0,"24":6122.58,"21":5357.26,"18":4591.94,"pound":42858.07},
 *  "silver":{"ounceUsd":41.08,"999":71.0,"925":65.74,"800":56.86},
 *  "usdEgp":53.81,"usdEgpDate":"2026-11-19","source":"gold-api.com","fetchedAt":"..."}
 * </pre>
 * Gold and silver values are EGP per gram (gold pound: per coin); ounceUsd is the world price.
 */
public record Metals(LocalDate date, LocalDateTime pricedAt, Map<String, Double> gold, Map<String, Double> silver,
                     Double usdEgp, LocalDate usdEgpDate, String source, Instant fetchedAt) {

    public static Metals of(MetalPrice m) {
        Map<String, Double> gold = new LinkedHashMap<>();
        put(gold, "ounceUsd", m.goldOunceUsd);
        put(gold, "24", m.gold24);
        put(gold, "21", m.gold21);
        put(gold, "18", m.gold18);
        put(gold, "pound", m.goldPound);
        Map<String, Double> silver = new LinkedHashMap<>();
        put(silver, "ounceUsd", m.silverOunceUsd);
        put(silver, "999", m.silver999);
        put(silver, "925", m.silver925);
        put(silver, "800", m.silver800);
        return new Metals(m.date, m.pricedAt, gold, silver, m.usdEgp, m.usdEgpDate, m.source, m.fetchedAt);
    }

    private static void put(Map<String, Double> map, String key, Double value) {
        if (value != null) map.put(key, value);
    }
}
