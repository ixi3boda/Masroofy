package com.example.finance.model;

import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;

/** One row per ticker: only the newest price is kept here (per-day prices are in price_history). */
public interface StockPriceRepository extends JpaRepository<StockPrice, Long> {
    Optional<StockPrice> findTopByTickerOrderByDateDesc(String ticker);
    List<StockPrice> findAllByOrderByTickerAsc();

    /** How many prices are older than the newest one of the same ticker. */
    @Query("select count(s) from StockPrice s where s.date < (select max(t.date) from StockPrice t where t.ticker = s.ticker)")
    long countOlderPrices();

    /** Deletes every price that is older than the newest one of the same ticker. */
    @Modifying
    @Query("delete from StockPrice s where s.date < (select max(t.date) from StockPrice t where t.ticker = s.ticker)")
    int deleteOlderPrices();
}
