package com.example.finance.model;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import java.time.Instant;
import java.time.LocalDate;

/** One CBE exchange rate: buy and sell price in EGP for one currency on one day. */
@Entity
@Table(name = "fx_rates", uniqueConstraints = @UniqueConstraint(columnNames = {"rate_date", "currency"}))
public class FxRate {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @JsonIgnore
    public Long id;
    @Column(name = "rate_date", nullable = false)
    public LocalDate date;
    @Column(nullable = false)
    public String currency;
    public double buy;
    public double sell;
    public String source;
    public Instant fetchedAt;

    public FxRate() {}

    public FxRate(LocalDate date, String currency, double buy, double sell) {
        this.date = date;
        this.currency = currency;
        this.buy = buy;
        this.sell = sell;
        this.source = "CBE";
    }
}
