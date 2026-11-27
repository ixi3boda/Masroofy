package com.masroofy.backend.repository;

import static com.masroofy.backend.repository.JdbcTimestamps.toDb;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.Optional;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

/** Exchange rates from the ASSET / PRICE_QUOTE tables (currency pairs such as "USD-EGP"). */
@Repository
public class FxRateRepository {

    private final JdbcTemplate jdbcTemplate;

    public FxRateRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /** The latest price of currency pair {@code symbol} quoted at or before {@code asOf}. */
    public Optional<BigDecimal> latestPrice(String symbol, Instant asOf) {
        return jdbcTemplate.query("""
                SELECT q.price
                FROM price_quotes q
                JOIN assets a ON a.id = q.asset_id
                WHERE a.symbol = ? AND a.type = 'currency' AND q.as_of <= ?
                ORDER BY q.as_of DESC
                LIMIT 1
                """,
                (rs, rowNum) -> rs.getBigDecimal("price"),
                symbol, toDb(asOf)).stream().findFirst();
    }
}
