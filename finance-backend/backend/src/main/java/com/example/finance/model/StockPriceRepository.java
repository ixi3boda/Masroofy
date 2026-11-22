package com.example.finance.model;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

public interface StockPriceRepository extends JpaRepository<StockPrice, Long> {
    Optional<StockPrice> findByDateAndTicker(LocalDate date, String ticker);
    List<StockPrice> findByTickerAndDateBetweenOrderByDateAsc(String ticker, LocalDate from, LocalDate to);
    Optional<StockPrice> findTopByTickerOrderByDateDesc(String ticker);
    Optional<StockPrice> findTopByTickerAndDateBeforeOrderByDateDesc(String ticker, LocalDate before);

    @Query("select distinct s.ticker from StockPrice s order by s.ticker")
    List<String> findTickers();
}
