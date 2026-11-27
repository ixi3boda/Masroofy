package com.masroofy.backend;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.firebase.FirebaseApp;
import com.google.firebase.auth.FirebaseAuth;
import com.masroofy.backend.demo.DemoUserSeeder;
import com.masroofy.backend.firebase.FirebaseIdentityClient;
import com.masroofy.backend.service.EmailService;
import com.masroofy.backend.support.FakeFirebase;
import com.masroofy.backend.support.PostgresTestSupport;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.TestInstance;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

/**
 * Demo data as a developer gets it: demo users created at startup in "Firebase" and PostgreSQL, able to log in through
 * the API and see a full dashboard; and a brand-new sign-up that gets the same data. Firebase is an in-memory fake.
 */
@SpringBootTest(properties = {
        "app.demo.enabled=true",
        "app.demo.for-new-users=true",
        "app.demo.users[0].email=Mariam.Demo@Masroofy.app",
        "app.demo.users[0].password=Test-Lagoon-31",
        "app.demo.users[0].full-name=Mariam Ali",
        "app.demo.users[1].email=omar.demo@masroofy.app",
        "app.demo.users[1].password=Test-Cedar-58",
        "app.demo.users[1].full-name=Omar Hassan"})
@AutoConfigureMockMvc
@TestInstance(TestInstance.Lifecycle.PER_CLASS)
class DemoSeedingIntegrationTest extends PostgresTestSupport {

    private static final String MARIAM = "mariam.demo@masroofy.app";
    private static final String OMAR = "omar.demo@masroofy.app";

    @TestConfiguration
    static class FakeFirebaseConfig {
        @Bean
        @Primary
        FakeFirebase fakeFirebase() {
            return new FakeFirebase();
        }
    }

    @Autowired
    private MockMvc mvc;
    @Autowired
    private ObjectMapper json;
    @Autowired
    private JdbcTemplate jdbc;
    @Autowired
    private FakeFirebase firebase;
    @Autowired
    private DemoUserSeeder seeder;
    @Autowired
    private FirebaseIdentityClient injectedClient;

    @MockitoBean
    private FirebaseApp firebaseApp;
    @MockitoBean
    private FirebaseAuth firebaseAuth;
    @MockitoBean
    private EmailService emailService;

    @BeforeEach
    void demoUsersReady() throws Exception {
        // Other test classes wipe the users table; re-run the startup step (it is idempotent anyway).
        seeder.run(null);
    }

    @AfterAll
    void cleanUp() {
        jdbc.update("DELETE FROM users WHERE email IN (?, ?) OR email LIKE 'signup-%'", MARIAM, OMAR);
        jdbc.update("DELETE FROM price_quotes WHERE source_api = 'demo'");
    }

    private String login(String email, String password) throws Exception {
        String body = mvc.perform(post("/api/v1/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content(json.writeValueAsString(Map.of("email", email, "password", password))))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString();
        return json.readTree(body).path("accessToken").asText();
    }

    private JsonNode dashboard(String token) throws Exception {
        return json.readTree(mvc.perform(get("/api/v1/dashboard").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andReturn().getResponse().getContentAsString());
    }

    @Test
    void demoUsersExistInFirebaseAndPostgresLinkedAndVerified() {
        assertThat(injectedClient).isSameAs(firebase);
        for (String email : List.of(MARIAM, OMAR)) {
            FakeFirebase.Account account = firebase.account(email).orElseThrow();
            assertThat(account.emailVerified()).isTrue();
            Map<String, Object> row = jdbc.queryForMap(
                    "SELECT firebase_uid, email_verified_at, base_currency, timezone FROM users WHERE email = ?", email);
            assertThat(row.get("firebase_uid")).isEqualTo(account.uid());
            assertThat(row.get("email_verified_at")).isNotNull();
            assertThat(row.get("base_currency")).isEqualTo("EGP");
            assertThat(row.get("timezone")).isEqualTo("Africa/Cairo");
        }
        assertThat(firebase.account(MARIAM).orElseThrow().displayName()).isEqualTo("Mariam Ali");
    }

    @Test
    void aDemoUserLogsInAndSeesTheFullDashboard() throws Exception {
        String token = login(MARIAM, "Test-Lagoon-31");

        mvc.perform(get("/api/v1/dashboard").header("Authorization", "Bearer " + token))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.summary.totalIncome").value("30000.00"))
                .andExpect(jsonPath("$.summary.totalExpense").value("12450.00"))
                .andExpect(jsonPath("$.balance.total").value("39100.00"))
                .andExpect(jsonPath("$.balance.accounts.length()").value(3))
                .andExpect(jsonPath("$.budget.usedPercent").value(69))
                .andExpect(jsonPath("$.recentTransactions[0].title").value("Carrefour"))
                .andExpect(jsonPath("$.recentTransactions[1].title").value("Uber"))
                .andExpect(jsonPath("$.recentTransactions[2].title").value("Vodafone"))
                .andExpect(jsonPath("$.badges.pendingReview").value(1));
        mvc.perform(get("/api/v1/users/me").header("Authorization", "Bearer " + token))
                .andExpect(jsonPath("$.email").value(MARIAM))
                .andExpect(jsonPath("$.fullName").value("Mariam Ali"));
    }

    @Test
    void eachDemoUserSeesOnlyTheirOwnAccounts() throws Exception {
        JsonNode mariam = dashboard(login(MARIAM, "Test-Lagoon-31"));
        JsonNode omar = dashboard(login(OMAR, "Test-Cedar-58"));

        assertThat(omar.at("/summary/totalExpense").asText()).isEqualTo("12450.00");
        for (int i = 0; i < 3; i++) {
            String omarAccount = omar.at("/balance/accounts/" + i + "/id").asText();
            for (int j = 0; j < 3; j++) {
                assertThat(mariam.at("/balance/accounts/" + j + "/id").asText()).isNotEqualTo(omarAccount);
            }
        }
    }

    @Test
    void restartingKeepsOneProfilePerDemoUserAndFreshData() throws Exception {
        seeder.run(null);
        seeder.run(null);

        assertThat(jdbc.queryForObject("SELECT count(*) FROM users WHERE email = ?", Integer.class, MARIAM))
                .isEqualTo(1);
        assertThat(jdbc.queryForObject("""
                SELECT count(*) FROM transactions t JOIN users u ON u.id = t.user_id WHERE u.email = ?""",
                Integer.class, MARIAM)).isEqualTo(52);
        assertThat(dashboard(login(MARIAM, "Test-Lagoon-31")).at("/summary/totalIncome").asText())
                .isEqualTo("30000.00");
    }

    @Test
    void aNewSignUpGetsTheDemoDataOnItsOwnAccount() throws Exception {
        String email = "signup-" + UUID.randomUUID() + "@example.com";
        mvc.perform(post("/api/v1/auth/register").contentType(MediaType.APPLICATION_JSON)
                        .content(json.writeValueAsString(Map.of("fullName", "Sara Nabil", "email", email,
                                "password", "Golden-Lotus-42", "acceptedTerms", true))))
                .andExpect(status().isCreated());
        ArgumentCaptor<String> code = ArgumentCaptor.forClass(String.class);
        verify(emailService).sendVerificationCode(eq(email), anyString(), code.capture(), any());
        mvc.perform(post("/api/v1/auth/email-verification/verify").contentType(MediaType.APPLICATION_JSON)
                        .content(json.writeValueAsString(Map.of("email", email, "code", code.getValue()))))
                .andExpect(status().isOk());

        JsonNode dashboard = dashboard(login(email, "Golden-Lotus-42"));

        assertThat(dashboard.at("/summary/totalIncome").asText()).isEqualTo("30000.00");
        assertThat(dashboard.at("/summary/totalExpense").asText()).isEqualTo("12450.00");
        assertThat(dashboard.at("/recentTransactions/0/title").asText()).isEqualTo("Carrefour");
        UUID userId = jdbc.queryForObject("SELECT id FROM users WHERE email = ?", UUID.class, email);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM accounts WHERE user_id = ?", Integer.class, userId))
                .isEqualTo(3);
    }

    @Test
    void wrongPasswordStillFailsForDemoUsers() throws Exception {
        mvc.perform(post("/api/v1/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content(json.writeValueAsString(Map.of("email", MARIAM, "password", "Wrong-Pass-99"))))
                .andExpect(status().isUnauthorized());
    }
}
