package com.example.finance.model;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface FxRateRepository extends JpaRepository<FxRate, Long> {
    Optional<FxRate> findByDateAndCurrency(LocalDate date, String currency);
    List<FxRate> findByDateBetweenOrderByDateAscCurrencyAsc(LocalDate from, LocalDate to);
    List<FxRate> findByCurrencyAndDateBetweenOrderByDateAsc(String currency, LocalDate from, LocalDate to);
    Optional<FxRate> findTopByOrderByDateDesc();
    Optional<FxRate> findTopByCurrencyOrderByDateDesc(String currency);
    List<FxRate> findByDateOrderByCurrencyAsc(LocalDate date);
}
