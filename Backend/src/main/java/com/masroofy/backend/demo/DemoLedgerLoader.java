package com.masroofy.backend.demo;

import java.io.IOException;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.util.UUID;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * Loads the demo ledger (classpath:demo/demo-ledger.sql) for one user, replacing that user's accounts, transactions,
 * transfers and budgets. The script only defines session-local (pg_temp) functions, so the definitions and the call
 * run in one transaction, on one connection.
 */
@Component
public class DemoLedgerLoader {

    static final String SCRIPT = "demo/demo-ledger.sql";
    /** The default ledger: the Figma numbers, the same as the app's mock data. */
    public static final String STANDARD_PROFILE = "standard";

    private final JdbcTemplate jdbcTemplate;
    private final TransactionTemplate transaction;
    private final String script;

    public DemoLedgerLoader(JdbcTemplate jdbcTemplate, PlatformTransactionManager transactionManager) {
        this.jdbcTemplate = jdbcTemplate;
        this.transaction = new TransactionTemplate(transactionManager);
        try {
            this.script = new ClassPathResource(SCRIPT).getContentAsString(StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new UncheckedIOException("Cannot read " + SCRIPT, e);
        }
    }

    /** Loads the standard ledger. Returns the number of transactions written for the user. */
    public int load(UUID userId) {
        return load(userId, STANDARD_PROFILE);
    }

    /**
     * Loads the ledger of {@code profile} (standard, saver, freelancer, student or family; null or blank =
     * standard). Returns the
     * number of transactions written for the user.
     */
    public int load(UUID userId, String profile) {
        String chosen = profile == null || profile.isBlank() ? STANDARD_PROFILE : profile.trim();
        Integer written = transaction.execute(status -> {
            jdbcTemplate.execute(script);
            return jdbcTemplate.queryForObject("SELECT pg_temp.demo_load_ledger(?, ?)", Integer.class, userId,
                    chosen);
        });
        return written == null ? 0 : written;
    }
}
