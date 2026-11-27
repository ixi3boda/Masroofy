package com.example.finance.model;

import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;

/** One row per currency: only the newest rate is kept here (per-day prices are in price_history). */
public interface FxRateRepository extends JpaRepository<FxRate, Long> {
    Optional<FxRate> findTopByCurrencyOrderByDateDesc(String currency);
    List<FxRate> findAllByOrderByCurrencyAsc();

    /** How many rates are older than the newest one of the same currency. */
    @Query("select count(f) from FxRate f where f.date < (select max(g.date) from FxRate g where g.currency = f.currency)")
    long countOlderRates();

    /** Deletes every rate that is older than the newest one of the same currency. */
    @Modifying
    @Query("delete from FxRate f where f.date < (select max(g.date) from FxRate g where g.currency = f.currency)")
    int deleteOlderRates();

    /** Deletes rows saved under the old CBE names ("US Dollar", ...) instead of a currency code. */
    @Modifying
    @Query("delete from FxRate f where length(f.currency) <> 3")
    int deleteNonCodeCurrencies();
}
