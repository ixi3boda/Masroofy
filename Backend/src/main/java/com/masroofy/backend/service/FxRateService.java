package com.masroofy.backend.service;

import com.masroofy.backend.repository.FxRateRepository;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.util.Optional;
import org.springframework.stereotype.Service;

/** Converts between currencies using the PRICE_QUOTE table. */
@Service
public class FxRateService {

    /** Precision of a derived (inverted) rate; matches NUMERIC(18, 8). */
    static final int RATE_SCALE = 8;

    private final FxRateRepository repository;

    public FxRateService(FxRateRepository repository) {
        this.repository = repository;
    }

    /**
     * Units of {@code to} per 1 unit of {@code from}, from the latest quote at or before {@code asOf}.
     * Uses the pair "FROM-TO" when quoted, else inverts "TO-FROM". Empty when neither is quoted.
     */
    public Optional<BigDecimal> rate(String from, String to, Instant asOf) {
        if (from.equals(to)) {
            return Optional.of(BigDecimal.ONE);
        }
        Optional<BigDecimal> direct = repository.latestPrice(from + "-" + to, asOf);
        if (direct.isPresent()) {
            return direct;
        }
        return repository.latestPrice(to + "-" + from, asOf)
                .map(price -> BigDecimal.ONE.divide(price, RATE_SCALE, RoundingMode.HALF_EVEN));
    }
}
