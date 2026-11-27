package com.example.finance.model;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import java.time.Instant;
import java.time.LocalDate;

/**
 * One price of one thing on one day, for the charts: the day's latest price (each update run
 * replaces the day's value). {@code kind} is gold, silver, currencies or stocks, as in /api/prices;
 * {@code item} is the item's key there (21, 999, USD, COMI.CA, ...). Price in EGP (per gram for gold
 * and silver, per coin for the gold pound, per 1 unit of a currency, per share; points for an index).
 */
@Entity
@Table(name = "price_history",
        uniqueConstraints = @UniqueConstraint(columnNames = {"kind", "item_key", "price_date"}),
        indexes = @Index(name = "price_history_item", columnList = "kind, item_key, price_date"))
public class PricePoint {
    public static final String GOLD = "gold", SILVER = "silver", CURRENCIES = "currencies", STOCKS = "stocks";

    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) @JsonIgnore
    public Long id;
    @Column(nullable = false)
    public String kind;
    @Column(name = "item_key", nullable = false)
    public String item;
    @Column(name = "price_date", nullable = false)
    public LocalDate date;
    public double price;
    public Instant recordedAt;

    public PricePoint() {}

    public PricePoint(String kind, String item, LocalDate date, double price, Instant recordedAt) {
        this.kind = kind;
        this.item = item;
        this.date = date;
        this.price = price;
        this.recordedAt = recordedAt;
    }
}
