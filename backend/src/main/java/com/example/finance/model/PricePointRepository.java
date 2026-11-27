package com.example.finance.model;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface PricePointRepository extends JpaRepository<PricePoint, Long> {
    Optional<PricePoint> findByKindAndItemAndDate(String kind, String item, LocalDate date);
    List<PricePoint> findByKindAndItemOrderByDateAsc(String kind, String item);
    List<PricePoint> findByKindAndItemAndDateBetweenOrderByDateAsc(String kind, String item, LocalDate from, LocalDate to);

    /** kind, item and date of every saved point (to see what an import would add). */
    @Query("select p.kind, p.item, p.date from PricePoint p")
    List<Object[]> findAllKeys();
}
