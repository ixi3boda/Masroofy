package com.example.finance.update;

import com.example.finance.model.MetalPrice;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * Turns world prices (US$ per troy ounce) into Egyptian prices (EGP per gram) with the CBE dollar rate:
 * gram of pure metal = ounce price x dollar rate / 31.1035. Gold 24K is pure, 21K = 21/24, 18K = 18/24,
 * and the gold pound is 8 g of 21K. Silver 999, 925 and 800 are 99.9%, 92.5% and 80% pure.
 * These are world-market values: shop prices in Egypt add a margin, and workmanship for jewellery.
 */
public final class MetalCalculator {
    public static final double GRAMS_PER_OUNCE = 31.1034768;

    private MetalCalculator() {}

    public static MetalPrice calculate(LocalDate day, LocalDateTime pricedAt, double goldOunceUsd,
                                       double silverOunceUsd, double usdEgp, LocalDate usdEgpDate) {
        double goldGram = goldOunceUsd * usdEgp / GRAMS_PER_OUNCE;
        double silverGram = silverOunceUsd * usdEgp / GRAMS_PER_OUNCE;
        MetalPrice m = new MetalPrice();
        m.date = day;
        m.pricedAt = pricedAt;
        m.goldOunceUsd = round(goldOunceUsd);
        m.silverOunceUsd = round(silverOunceUsd);
        m.usdEgp = usdEgp;
        m.usdEgpDate = usdEgpDate;
        m.gold24 = round(goldGram);
        m.gold21 = round(goldGram * 21 / 24);
        m.gold18 = round(goldGram * 18 / 24);
        m.goldPound = round(goldGram * 21 / 24 * 8);
        m.silver999 = round(silverGram * 0.999);
        m.silver925 = round(silverGram * 0.925);
        m.silver800 = round(silverGram * 0.800);
        m.source = "gold-api.com";
        return m;
    }

    private static double round(double v) {
        return Math.round(v * 100) / 100.0;
    }
}
