package com.masroofy.backend.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.masroofy.backend.repository.FxRateRepository;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class FxRateServiceTest {

    private static final Instant AS_OF = Instant.parse("2026-11-20T10:00:00Z");

    private final FxRateRepository repository = mock(FxRateRepository.class);
    private final FxRateService service = new FxRateService(repository);

    @Test
    void sameCurrencyIsOneWithoutLookup() {
        assertThat(service.rate("EGP", "EGP", AS_OF)).contains(BigDecimal.ONE);
        verifyNoInteractions(repository);
    }

    @Test
    void usesTheDirectPairWhenQuoted() {
        when(repository.latestPrice("USD-EGP", AS_OF)).thenReturn(Optional.of(new BigDecimal("48.50000000")));

        assertThat(service.rate("USD", "EGP", AS_OF)).contains(new BigDecimal("48.50000000"));
    }

    @Test
    void invertsTheReversePair() {
        when(repository.latestPrice("EGP-USD", AS_OF)).thenReturn(Optional.empty());
        when(repository.latestPrice("USD-EGP", AS_OF)).thenReturn(Optional.of(new BigDecimal("50")));

        assertThat(service.rate("EGP", "USD", AS_OF)).contains(new BigDecimal("0.02000000"));
    }

    @Test
    void emptyWhenNeitherDirectionIsQuoted() {
        when(repository.latestPrice("JPY-EGP", AS_OF)).thenReturn(Optional.empty());
        when(repository.latestPrice("EGP-JPY", AS_OF)).thenReturn(Optional.empty());

        assertThat(service.rate("JPY", "EGP", AS_OF)).isEmpty();
    }
}
