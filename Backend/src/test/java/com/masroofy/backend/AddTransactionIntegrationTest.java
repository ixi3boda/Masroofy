package com.masroofy.backend;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.firebase.FirebaseApp;
import com.google.firebase.auth.FirebaseAuth;
import com.masroofy.backend.firebase.FirebaseIdentityClient;
import com.masroofy.backend.firebase.VerifiedToken;
import com.masroofy.backend.service.EmailService;
import com.masroofy.backend.service.UserRegisteredEvent;
import com.masroofy.backend.support.PostgresTestSupport;
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;

/**
 * What the app does from Home's "+" button: sign-up gives a Cash account, the form lists it, Save posts the
 * transaction, Retry doesn't save it twice, the Saved screen reads it back, and Home's dashboard counts it.
 * Real PostgreSQL; only Firebase and email are mocked.
 */
@SpringBootTest
@AutoConfigureMockMvc
class AddTransactionIntegrationTest extends PostgresTestSupport {

    private static final String EMAIL = "add-transaction@example.com";
    private static final String TOKEN = "Bearer add-token";

    @Autowired
    private MockMvc mvc;
    @Autowired
    private JdbcTemplate jdbc;
    @Autowired
    private ApplicationEventPublisher events;
    @Autowired
    private ObjectMapper objectMapper;

    @MockitoBean
    private FirebaseApp firebaseApp;
    @MockitoBean
    private FirebaseAuth firebaseAuth;
    @MockitoBean
    private FirebaseIdentityClient firebase;
    @MockitoBean
    private EmailService emailService;

    private UUID userId;

    @BeforeEach
    void signUp() {
        userId = UUID.randomUUID();
        jdbc.update("""
                INSERT INTO users (id, firebase_uid, email, full_name, email_verified_at, terms_accepted_at,
                                   created_at, updated_at)
                VALUES (?, 'uid-add', ?, 'Mariam Ali', now(), now(), now(), now())""", userId, EMAIL);
        when(firebase.verifyIdToken("add-token", true)).thenReturn(new VerifiedToken("uid-add", EMAIL));
        events.publishEvent(new UserRegisteredEvent(userId, EMAIL));
    }

    @AfterEach
    void cleanUp() {
        jdbc.update("DELETE FROM users WHERE id = ?", userId);
    }

    private JsonNode json(MvcResult result) throws Exception {
        return objectMapper.readTree(result.getResponse().getContentAsString());
    }

    @Test
    void addFromHomeThenRetryThenSeeItOnTheDashboard() throws Exception {
        // The account picker: the sign-up gave a Cash account.
        JsonNode accounts = json(mvc.perform(get("/api/v1/accounts").header("Authorization", TOKEN))
                .andExpect(status().isOk()).andReturn());
        assertThat(accounts).hasSize(1);
        assertThat(accounts.get(0).get("name").asText()).isEqualTo("Cash");
        String cash = accounts.get(0).get("id").asText();

        String today = LocalDate.now(ZoneId.of("Africa/Cairo")).toString();
        String body = """
                {"clientRequestId":"%s","type":"EXPENSE","amount":"120.00","title":"Uber","categoryKey":"transport",
                 "date":"%s","accountId":"%s","note":" Ride home "}""".formatted(UUID.randomUUID(), today, cash);

        // Save.
        JsonNode created = json(mvc.perform(post("/api/v1/transactions").header("Authorization", TOKEN)
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.signedAmount").value("-120.00"))
                .andExpect(jsonPath("$.category.key").value("transport"))
                .andExpect(jsonPath("$.note").value("Ride home"))
                .andExpect(jsonPath("$.date").value(today))
                .andReturn());
        String id = created.get("id").asText();

        // Retry with the same request: same transaction, nothing new saved.
        mvc.perform(post("/api/v1/transactions").header("Authorization", TOKEN)
                        .contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(id));
        assertThat(jdbc.queryForObject("SELECT count(*) FROM transactions WHERE user_id = ?", Long.class, userId))
                .isEqualTo(1);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM audit_log WHERE entity_id = ?::uuid AND action = 'create'",
                Long.class, id)).isEqualTo(1);

        // The Saved screen reads it back.
        mvc.perform(get("/api/v1/transactions/" + id).header("Authorization", TOKEN))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Uber"));

        // Back on Home.
        mvc.perform(get("/api/v1/dashboard").header("Authorization", TOKEN))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.summary.totalExpense").value("120.00"))
                .andExpect(jsonPath("$.balance.total").value("-120.00"))
                .andExpect(jsonPath("$.recentTransactions[0].id").value(id));
    }

    @Test
    void anotherUsersTransactionIsNotFound() throws Exception {
        UUID stranger = UUID.randomUUID();
        try {
            jdbc.update("""
                    INSERT INTO users (id, firebase_uid, email, full_name, email_verified_at, terms_accepted_at,
                                       created_at, updated_at)
                    VALUES (?, 'uid-stranger', 'stranger@example.com', 'S', now(), now(), now(), now())""", stranger);
            events.publishEvent(new UserRegisteredEvent(stranger, "stranger@example.com"));
            UUID theirCash = jdbc.queryForObject("SELECT id FROM accounts WHERE user_id = ?", UUID.class, stranger);
            UUID theirs = UUID.randomUUID();
            jdbc.update("""
                    INSERT INTO transactions (id, user_id, account_id, category_id, type, amount, currency,
                                              occurred_at, created_at, updated_at)
                    VALUES (?, ?, ?, '0c0a0000-0000-4000-8000-000000000001', 'expense', 10, 'EGP', now(), now(), now())""",
                    theirs, stranger, theirCash);

            mvc.perform(get("/api/v1/transactions/" + theirs).header("Authorization", TOKEN))
                    .andExpect(status().isNotFound())
                    .andExpect(jsonPath("$.code").value("NOT_FOUND"));
        } finally {
            jdbc.update("DELETE FROM users WHERE id = ?", stranger);
        }
    }
}
