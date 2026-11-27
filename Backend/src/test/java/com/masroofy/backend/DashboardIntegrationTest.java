package com.masroofy.backend;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.google.firebase.FirebaseApp;
import com.google.firebase.auth.FirebaseAuth;
import com.masroofy.backend.firebase.FirebaseIdentityClient;
import com.masroofy.backend.firebase.VerifiedToken;
import com.masroofy.backend.service.EmailService;
import com.masroofy.backend.support.PostgresTestSupport;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.YearMonth;
import java.time.ZoneId;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.testcontainers.containers.Container.ExecResult;
import org.testcontainers.images.builder.Transferable;

/**
 * The whole backend on real PostgreSQL with the real demo ledger (src/main/resources/demo/demo-ledger.sql) loaded
 * through psql, exactly as scripts/load-demo-data.sh does. Only Firebase and email are mocked.
 */
@SpringBootTest
@AutoConfigureMockMvc
class DashboardIntegrationTest extends PostgresTestSupport {

    private static final String EMAIL = "demo-dashboard@example.com";
    private static final ZoneId CAIRO = ZoneId.of("Africa/Cairo");

    @Autowired
    private MockMvc mvc;
    @Autowired
    private JdbcTemplate jdbc;

    @MockitoBean
    private FirebaseApp firebaseApp;
    @MockitoBean
    private FirebaseAuth firebaseAuth;
    @MockitoBean
    private FirebaseIdentityClient firebase;
    @MockitoBean
    private EmailService emailService;

    @BeforeEach
    void loadDemoData() throws Exception {
        jdbc.update("""
                INSERT INTO users (id, firebase_uid, email, full_name, email_verified_at, terms_accepted_at,
                                   created_at, updated_at)
                VALUES (gen_random_uuid(), 'uid-demo', ?, 'Mariam Ali', now(), now(), now(), now())""", EMAIL);
        when(firebase.verifyIdToken("demo-token", true)).thenReturn(new VerifiedToken("uid-demo", EMAIL));
        assertThat(runScriptLikeLoadDemoDataSh(EMAIL).getExitCode()).isZero();
    }

    /** Sends psql exactly what scripts/load-demo-data.sh sends: the demo ledger file and one call, in a transaction. */
    private static ExecResult runScriptLikeLoadDemoDataSh(String email) throws Exception {
        String script = "\\set ON_ERROR_STOP on\nBEGIN;\n"
                + Files.readString(Path.of("src/main/resources/demo/demo-ledger.sql"))
                + "\nSELECT pg_temp.demo_load_ledger_for_email(:'email');\nCOMMIT;\n";
        POSTGRES.copyFileToContainer(Transferable.of(script), "/tmp/load-demo-data.sql");
        return POSTGRES.execInContainer("psql", "-q", "-v", "email=" + email, "-U", POSTGRES.getUsername(),
                "-d", POSTGRES.getDatabaseName(), "-f", "/tmp/load-demo-data.sql");
    }

    @AfterEach
    void cleanUp() {
        jdbc.update("DELETE FROM users WHERE email = ?", EMAIL);
        jdbc.update("DELETE FROM price_quotes WHERE source_api = 'demo'");
    }

    @Test
    void currentMonthMatchesTheDesign() throws Exception {
        YearMonth thisMonth = YearMonth.now(CAIRO);

        mvc.perform(get("/api/v1/dashboard").header("Authorization", "Bearer demo-token"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.period.month").value(thisMonth.toString()))
                .andExpect(jsonPath("$.period.currentMonth").value(true))
                .andExpect(jsonPath("$.baseCurrency").value("EGP"))
                // Total Salary (= total income), Total Expense, Income vs Expenses
                .andExpect(jsonPath("$.summary.totalIncome").value("30000.00"))
                .andExpect(jsonPath("$.summary.totalExpense").value("12450.00"))
                .andExpect(jsonPath("$.summary.net").value("17550.00"))
                // Current Balance: CIB 20,550 + Cash 4,000 + 300 USD x 48.50
                .andExpect(jsonPath("$.balance.total").value("39100.00"))
                .andExpect(jsonPath("$.balance.accounts.length()").value(3))
                .andExpect(jsonPath("$.balance.accounts[0].name").value("CIB Account"))
                .andExpect(jsonPath("$.balance.accounts[0].balance").value("20550.00"))
                .andExpect(jsonPath("$.balance.accounts[0].cardLast4").value("4821"))
                .andExpect(jsonPath("$.balance.accounts[1].name").value("Payoneer USD"))
                .andExpect(jsonPath("$.balance.accounts[1].currency").value("USD"))
                .andExpect(jsonPath("$.balance.accounts[1].balance").value("300.00"))
                .andExpect(jsonPath("$.balance.accounts[1].balanceInBase").value("14550.00"))
                .andExpect(jsonPath("$.balance.accounts[1].fxRate").value("48.500000"))
                .andExpect(jsonPath("$.balance.accounts[2].name").value("Cash"))
                .andExpect(jsonPath("$.balance.accounts[2].balance").value("4000.00"))
                .andExpect(jsonPath("$.balance.unconvertedCurrencies").isEmpty())
                // Budget Progress: 69% used, 5,550 remaining of 18,000
                .andExpect(jsonPath("$.budget.amount").value("18000.00"))
                .andExpect(jsonPath("$.budget.spent").value("12450.00"))
                .andExpect(jsonPath("$.budget.remaining").value("5550.00"))
                .andExpect(jsonPath("$.budget.usedPercent").value(69))
                .andExpect(jsonPath("$.budget.status").value("ON_TRACK"))
                // Recent Transactions: Carrefour, Uber, Vodafone
                .andExpect(jsonPath("$.recentTransactions.length()").value(3))
                .andExpect(jsonPath("$.recentTransactions[0].title").value("Carrefour"))
                .andExpect(jsonPath("$.recentTransactions[0].category.key").value("groceries"))
                .andExpect(jsonPath("$.recentTransactions[0].category.name").value("Groceries"))
                .andExpect(jsonPath("$.recentTransactions[0].signedAmount").value("-850.00"))
                .andExpect(jsonPath("$.recentTransactions[0].account.name").value("CIB Account"))
                .andExpect(jsonPath("$.recentTransactions[1].title").value("Uber"))
                .andExpect(jsonPath("$.recentTransactions[1].category.key").value("transport"))
                .andExpect(jsonPath("$.recentTransactions[1].signedAmount").value("-120.00"))
                .andExpect(jsonPath("$.recentTransactions[1].account.name").value("Cash"))
                .andExpect(jsonPath("$.recentTransactions[2].title").value("Vodafone"))
                .andExpect(jsonPath("$.recentTransactions[2].category.key").value("bills"))
                .andExpect(jsonPath("$.recentTransactions[2].signedAmount").value("-250.00"))
                // The SMS-detected Starbucks payment waiting for review
                .andExpect(jsonPath("$.badges.pendingReview").value(1));
    }

    @Test
    void lastMonthUsesLastMonthsNumbersAndRate() throws Exception {
        YearMonth lastMonth = YearMonth.now(CAIRO).minusMonths(1);

        mvc.perform(get("/api/v1/dashboard?month=" + lastMonth + "&recentLimit=5")
                        .header("Authorization", "Bearer demo-token"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.period.currentMonth").value(false))
                // 30,000 salary + 350 USD x 48.20; 29,000 EGP + 50 USD x 48.20
                .andExpect(jsonPath("$.summary.totalIncome").value("46870.00"))
                .andExpect(jsonPath("$.summary.totalExpense").value("31410.00"))
                .andExpect(jsonPath("$.summary.net").value("15460.00"))
                // Balances at the end of last month, USD at last month's 48.20
                .andExpect(jsonPath("$.balance.total").value("21460.00"))
                .andExpect(jsonPath("$.balance.accounts[0].name").value("Payoneer USD"))
                .andExpect(jsonPath("$.balance.accounts[0].balanceInBase").value("14460.00"))
                .andExpect(jsonPath("$.balance.accounts[1].balance").value("5500.00"))
                .andExpect(jsonPath("$.balance.accounts[2].balance").value("1500.00"))
                .andExpect(jsonPath("$.budget.status").value("OVER"))
                .andExpect(jsonPath("$.budget.usedPercent").value(174))
                .andExpect(jsonPath("$.budget.remaining").value("-13410.00"))
                .andExpect(jsonPath("$.recentTransactions.length()").value(5))
                .andExpect(jsonPath("$.recentTransactions[0].title").value("Parking"))
                .andExpect(jsonPath("$.recentTransactions[1].title").value("Metro Market"))
                .andExpect(jsonPath("$.recentTransactions[2].title").value("Carrefour"))
                .andExpect(jsonPath("$.recentTransactions[2].amount").value("1630.00"));
    }

    @Test
    void transfersShowOnceWithBothAccounts() throws Exception {
        mvc.perform(get("/api/v1/dashboard?recentLimit=20").header("Authorization", "Bearer demo-token"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.recentTransactions[?(@.type == 'TRANSFER')].title").value("Transfer to Cash"))
                .andExpect(jsonPath("$.recentTransactions[?(@.type == 'TRANSFER')].account.name").value("CIB Account"))
                .andExpect(jsonPath("$.recentTransactions[?(@.type == 'TRANSFER')].amount").value("4000.00"))
                .andExpect(jsonPath("$.recentTransactions[?(@.title == 'Starbucks')]").isEmpty());
    }

    @Test
    void reloadingTheDemoDataReplacesItInsteadOfDoublingIt() throws Exception {
        ExecResult again = runScriptLikeLoadDemoDataSh(EMAIL);
        assertThat(again.getExitCode()).as(again.getStderr()).isZero();

        mvc.perform(get("/api/v1/dashboard").header("Authorization", "Bearer demo-token"))
                .andExpect(jsonPath("$.summary.totalExpense").value("12450.00"))
                .andExpect(jsonPath("$.balance.accounts.length()").value(3));
    }

    @Test
    void unknownEmailIsRejectedByTheDemoScript() throws Exception {
        ExecResult result = runScriptLikeLoadDemoDataSh("nobody@example.com");

        assertThat(result.getExitCode()).isNotZero();
        assertThat(result.getStderr()).contains("No Masroofy user with that email");
    }
}
