package com.masroofy.backend;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.google.firebase.FirebaseApp;
import com.google.firebase.auth.FirebaseAuth;
import com.masroofy.backend.dto.request.RegisterRequest;
import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.firebase.FirebaseIdentityClient;
import com.masroofy.backend.model.AuthCodePurpose;
import com.masroofy.backend.model.User;
import com.masroofy.backend.repository.UserRepository;
import com.masroofy.backend.service.AuthCodeService;
import com.masroofy.backend.service.AuthService;
import com.masroofy.backend.service.EmailService;
import com.masroofy.backend.support.PostgresTestSupport;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.Callable;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Function;
import java.util.stream.Collectors;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

/**
 * Fires the same call from many threads at once against real PostgreSQL (the races the hard test found:
 * attempt limit, resend cooldown and duplicate sign-ups). Firebase and email are mocked.
 */
@SpringBootTest
class ConcurrencyIntegrationTest extends PostgresTestSupport {

    private static final int THREADS = 20;

    @Autowired
    private AuthCodeService authCodeService;
    @Autowired
    private AuthService authService;
    @Autowired
    private UserRepository userRepository;
    @Autowired
    private JdbcTemplate jdbcTemplate;

    @MockitoBean
    private FirebaseApp firebaseApp;
    @MockitoBean
    private FirebaseAuth firebaseAuth;
    @MockitoBean
    private FirebaseIdentityClient firebase;
    @MockitoBean
    private EmailService emailService;

    @BeforeEach
    @AfterEach
    void cleanDatabase() {
        jdbcTemplate.update("DELETE FROM auth_codes");
        jdbcTemplate.update("DELETE FROM code_dispatches");
        jdbcTemplate.update("DELETE FROM users");
    }

    private User newUser() {
        Instant now = Instant.now();
        User user = new User(UUID.randomUUID(), "uid-" + UUID.randomUUID(), UUID.randomUUID() + "@example.com", null,
                "Race Tester", "EGP", "en", "Africa/Cairo", null, null, now, now, now);
        userRepository.insert(user);
        return user;
    }

    /** Runs {@code task} on {@code THREADS} threads released together; returns each outcome's name and count. */
    private Map<String, Long> race(Callable<Object> task) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(THREADS);
        CountDownLatch start = new CountDownLatch(1);
        List<Future<String>> futures = new ArrayList<>();
        for (int i = 0; i < THREADS; i++) {
            futures.add(pool.submit(() -> {
                start.await();
                try {
                    task.call();
                    return "OK";
                } catch (ApiException e) {
                    return e.getErrorCode().name();
                }
            }));
        }
        start.countDown();
        List<String> outcomes = new ArrayList<>();
        for (Future<String> f : futures) {
            outcomes.add(f.get(60, TimeUnit.SECONDS));
        }
        pool.shutdown();
        return outcomes.stream().collect(Collectors.groupingBy(Function.identity(), Collectors.counting()));
    }

    @Test
    void parallelWrongCodesCountAtMostTheAllowedAttempts() throws Exception {
        User user = newUser();
        String right = authCodeService.issueCode(user.id(), AuthCodePurpose.EMAIL_VERIFICATION).code();
        String wrong = right.equals("000000") ? "111111" : "000000";

        Map<String, Long> outcomes = race(() -> {
            authCodeService.verifyCode(user.id(), AuthCodePurpose.EMAIL_VERIFICATION, wrong);
            return null;
        });

        assertThat(outcomes.get("INVALID_CODE")).isEqualTo(4L);
        assertThat(outcomes.get("TOO_MANY_ATTEMPTS")).isEqualTo(1L);
        assertThat(jdbcTemplate.queryForObject("SELECT max(attempts) FROM auth_codes WHERE user_id = ?",
                Integer.class, user.id())).isEqualTo(5);
    }

    @Test
    void rightCodeHiddenInABurstOfWrongOnesIsNotAcceptedAfterTheLimit() throws Exception {
        User user = newUser();
        String right = authCodeService.issueCode(user.id(), AuthCodePurpose.EMAIL_VERIFICATION).code();
        String wrong = right.equals("000000") ? "111111" : "000000";
        AtomicInteger calls = new AtomicInteger();

        Map<String, Long> outcomes = race(() -> {
            String guess = calls.incrementAndGet() == THREADS ? right : wrong;
            authCodeService.verifyCode(user.id(), AuthCodePurpose.EMAIL_VERIFICATION, guess);
            return null;
        });

        Integer attempts = jdbcTemplate.queryForObject("SELECT max(attempts) FROM auth_codes WHERE user_id = ?",
                Integer.class, user.id());
        assertThat(attempts).isLessThanOrEqualTo(5);
        if (outcomes.containsKey("OK")) {
            assertThat(attempts).as("accepted only while fewer than 5 wrong guesses were counted").isLessThan(5);
        }
    }

    @Test
    void parallelCodeRequestsIssueExactlyOneCode() throws Exception {
        User user = newUser();

        Map<String, Long> outcomes = race(() -> authCodeService.issueCode(user.id(), AuthCodePurpose.PASSWORD_RESET));

        assertThat(outcomes.get("OK")).isEqualTo(1L);
        assertThat(outcomes.get("RESEND_COOLDOWN")).isEqualTo(THREADS - 1L);
        assertThat(jdbcTemplate.queryForObject(
                "SELECT count(*) FROM auth_codes WHERE user_id = ? AND consumed_at IS NULL", Integer.class, user.id()))
                .isEqualTo(1);
    }

    @Test
    void parallelResendsForOneEmailGetOneSlot() throws Exception {
        Map<String, Long> outcomes = race(() -> {
            authCodeService.reserveDispatch("someone@example.com", AuthCodePurpose.EMAIL_VERIFICATION);
            return null;
        });

        assertThat(outcomes.get("OK")).isEqualTo(1L);
        assertThat(outcomes.get("RESEND_COOLDOWN")).isEqualTo(THREADS - 1L);
    }

    @Test
    void parallelSignUpsWithOneEmailCreateOneFirebaseAccount() throws Exception {
        AtomicInteger uids = new AtomicInteger();
        when(firebase.createUser(anyString(), anyString(), anyString())).thenAnswer(invocation -> {
            Thread.sleep(50); // a real Firebase call takes a while; widens the race window
            return "uid-" + uids.incrementAndGet();
        });
        RegisterRequest request = new RegisterRequest("Race Tester", "race@example.com", "Sunny-Nile9", true);

        Map<String, Long> outcomes = race(() -> authService.register(request));

        assertThat(outcomes.get("OK")).isEqualTo(1L);
        assertThat(outcomes.get("EMAIL_ALREADY_IN_USE")).isEqualTo(THREADS - 1L);
        verify(firebase, times(1)).createUser(anyString(), anyString(), anyString());
        assertThat(jdbcTemplate.queryForObject("SELECT count(*) FROM users WHERE email = 'race@example.com'",
                Integer.class)).isEqualTo(1);
    }
}
