package com.example.finance.model;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface MetalPriceRepository extends JpaRepository<MetalPrice, Long> {
    Optional<MetalPrice> findByDate(LocalDate date);
    List<MetalPrice> findByDateBetweenOrderByDateAsc(LocalDate from, LocalDate to);
    Optional<MetalPrice> findTopByOrderByDateDesc();
}
