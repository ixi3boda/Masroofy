package com.example.finance.model;

import jakarta.persistence.*;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * The newest gold and silver prices (a single row): world prices from gold-api.com (US$ per ounce), and the
 * Egyptian prices worked out from them with the US dollar rate (EGP per gram; gold pound per coin).
 * The API serves this as {@link com.example.finance.api.Metals}.
 */
@Entity
@Table(name = "metal_prices", uniqueConstraints = @UniqueConstraint(columnNames = "price_date"))
public class MetalPrice {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    public Long id;
    @Column(name = "price_date", nullable = false)
    public LocalDate date;
    /** When gold-api.com last updated the gold price (Cairo time). */
    public LocalDateTime pricedAt;

    public Double goldOunceUsd;
    public Double silverOunceUsd;
    /** US Dollar rate used (average of buy and sell), and its date. */
    public Double usdEgp;
    public LocalDate usdEgpDate;

    public Double gold24;
    public Double gold21;
    public Double gold18;
    public Double goldPound;
    public Double silver999;
    public Double silver925;
    public Double silver800;

    public String source;
    public Instant fetchedAt;
}
