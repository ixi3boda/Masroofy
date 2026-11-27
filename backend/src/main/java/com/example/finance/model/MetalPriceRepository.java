package com.example.finance.model;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;

/** A single row: only the newest gold and silver prices are kept here (per-day prices are in price_history). */
public interface MetalPriceRepository extends JpaRepository<MetalPrice, Long> {
    Optional<MetalPrice> findTopByOrderByDateDesc();

    /** How many days are older than the newest. */
    @Query("select count(m) from MetalPrice m where m.date < (select max(n.date) from MetalPrice n)")
    long countOlderPrices();

    /** Deletes every day except the newest. */
    @Modifying
    @Query("delete from MetalPrice m where m.date < (select max(n.date) from MetalPrice n)")
    int deleteOlderPrices();
}
