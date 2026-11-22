package com.example.finance.model;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import java.time.Instant;
import java.time.LocalDate;

/** Daily price of a stock or index. Indices only have a close value. */
@Entity
@Table(name = "stock_prices", uniqueConstraints = @UniqueConstraint(columnNames = {"price_date", "ticker"}))
public class StockPrice {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @JsonIgnore
    public Long id;
    @Column(name = "price_date", nullable = false)
    public LocalDate date;
    @Column(nullable = false)
    public String ticker;
    public Double open;
    public Double high;
    public Double low;
    @Column(nullable = false)
    public double close;
    public Long volume;
    public String source;
    public Instant fetchedAt;

    public StockPrice() {}

    public StockPrice(LocalDate date, String ticker, Double open, Double high, Double low,
                      double close, Long volume, String source) {
        this.date = date;
        this.ticker = ticker;
        this.open = open;
        this.high = high;
        this.low = low;
        this.close = close;
        this.volume = volume;
        this.source = source;
    }
}
