package com.masroofy.backend.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.masroofy.backend.dto.response.DashboardResponse;
import com.masroofy.backend.dto.response.DashboardResponse.AccountRef;
import com.masroofy.backend.dto.response.DashboardResponse.AccountSummary;
import com.masroofy.backend.dto.response.DashboardResponse.Badges;
import com.masroofy.backend.dto.response.DashboardResponse.Balance;
import com.masroofy.backend.dto.response.DashboardResponse.BudgetSummary;
import com.masroofy.backend.dto.response.DashboardResponse.CategoryRef;
import com.masroofy.backend.dto.response.DashboardResponse.Period;
import com.masroofy.backend.dto.response.DashboardResponse.RecentTransaction;
import com.masroofy.backend.dto.response.DashboardResponse.Summary;
import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.exception.FieldErrorDetail;
import com.masroofy.backend.firebase.FirebaseIdentityClient;
import com.masroofy.backend.firebase.VerifiedToken;
import com.masroofy.backend.model.User;
import com.masroofy.backend.repository.UserRepository;
import com.masroofy.backend.service.DashboardService;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(DashboardController.class)
@Import(WebLayerTestConfig.class)
class DashboardControllerTest {

    private static final UUID USER_ID = UUID.fromString("22222222-2222-2222-2222-222222222222");
    private static final Instant NOW = Instant.parse("2026-11-20T10:00:00Z");

    @Autowired
    private MockMvc mvc;

    @MockitoBean
    private DashboardService dashboardService;
    @MockitoBean
    private FirebaseIdentityClient firebase;
    @MockitoBean
    private UserRepository userRepository;

    private void loggedIn() {
        when(firebase.verifyIdToken("good", true)).thenReturn(new VerifiedToken("uid-1", "mariam@example.com"));
        when(userRepository.findByFirebaseUid("uid-1")).thenReturn(Optional.of(new User(USER_ID, "uid-1",
                "mariam@example.com", null, "Mariam Ali", "EGP", "en", "Africa/Cairo", null, NOW, NOW, NOW, NOW)));
    }

    private static BigDecimal d(String value) {
        return new BigDecimal(value);
    }

    private static DashboardResponse sample() {
        UUID cib = UUID.randomUUID();
        return new DashboardResponse(
                new Period("2026-11", "Nov 2026", LocalDate.of(2026, 11, 1), LocalDate.of(2026, 11, 30),
                        "Africa/Cairo", NOW, true),
                "EGP",
                new Summary(d("30000.00"), d("12450.00"), d("17550.00")),
                new Balance(d("24550.00"), List.of(
                        new AccountSummary(cib, "CIB Account", "bank", "EGP", "4821", d("20550.00"), d("20550.00"), null),
                        new AccountSummary(UUID.randomUUID(), "Cash", "cash", "EGP", null, d("4000.00"), d("4000.00"),
                                null)), List.of()),
                new BudgetSummary(UUID.randomUUID(), d("18000.00"), d("0.00"), d("18000.00"), d("12450.00"),
                        d("5550.00"), 69, 80, "ON_TRACK", false),
                List.of(new RecentTransaction(UUID.randomUUID(), "EXPENSE", "Carrefour", "Carrefour", null,
                        new CategoryRef(UUID.randomUUID(), "groceries", "Groceries"), new AccountRef(cib, "CIB Account"),
                        null, d("850.00"), d("-850.00"), "EGP", d("850.00"), LocalDate.of(2026, 11, 19), "14:32",
                        Instant.parse("2026-11-19T12:32:00Z"))),
                new Badges(1));
    }

    @Test
    void returnsTheDashboardWithMoneyAsStrings() throws Exception {
        loggedIn();
        when(dashboardService.getDashboard(USER_ID, null, 3)).thenReturn(sample());

        mvc.perform(get("/api/v1/dashboard").header("Authorization", "Bearer good"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.period.month").value("2026-11"))
                .andExpect(jsonPath("$.period.label").value("Nov 2026"))
                .andExpect(jsonPath("$.period.startDate").value("2026-11-01"))
                .andExpect(jsonPath("$.period.asOf").value("2026-11-20T10:00:00Z"))
                .andExpect(jsonPath("$.baseCurrency").value("EGP"))
                .andExpect(jsonPath("$.summary.totalIncome").value("30000.00"))
                .andExpect(jsonPath("$.summary.totalExpense").value("12450.00"))
                .andExpect(jsonPath("$.balance.total").value("24550.00"))
                .andExpect(jsonPath("$.balance.accounts[0].name").value("CIB Account"))
                .andExpect(jsonPath("$.balance.accounts[0].balance").value("20550.00"))
                .andExpect(jsonPath("$.balance.accounts[0].fxRate").doesNotExist())
                .andExpect(jsonPath("$.balance.accounts[1].cardLast4").doesNotExist())
                .andExpect(jsonPath("$.budget.remaining").value("5550.00"))
                .andExpect(jsonPath("$.budget.usedPercent").value(69))
                .andExpect(jsonPath("$.budget.status").value("ON_TRACK"))
                .andExpect(jsonPath("$.recentTransactions[0].title").value("Carrefour"))
                .andExpect(jsonPath("$.recentTransactions[0].signedAmount").value("-850.00"))
                .andExpect(jsonPath("$.recentTransactions[0].category.key").value("groceries"))
                .andExpect(jsonPath("$.recentTransactions[0].date").value("2026-11-19"))
                .andExpect(jsonPath("$.recentTransactions[0].time").value("14:32"))
                .andExpect(jsonPath("$.recentTransactions[0].toAccount").doesNotExist())
                .andExpect(jsonPath("$.badges.pendingReview").value(1));
    }

    @Test
    void passesMonthAndRecentLimit() throws Exception {
        loggedIn();
        when(dashboardService.getDashboard(USER_ID, "2026-10", 10)).thenReturn(sample());

        mvc.perform(get("/api/v1/dashboard?month=2026-10&recentLimit=10").header("Authorization", "Bearer good"))
                .andExpect(status().isOk());
        verify(dashboardService).getDashboard(USER_ID, "2026-10", 10);
    }

    @Test
    void noBudgetMeansNoBudgetField() throws Exception {
        loggedIn();
        DashboardResponse full = sample();
        when(dashboardService.getDashboard(any(), isNull(), eq(3))).thenReturn(new DashboardResponse(full.period(),
                full.baseCurrency(), full.summary(), full.balance(), null, List.of(), full.badges()));

        mvc.perform(get("/api/v1/dashboard").header("Authorization", "Bearer good"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.budget").doesNotExist())
                .andExpect(jsonPath("$.recentTransactions").isEmpty());
    }

    @Test
    void requiresAToken() throws Exception {
        mvc.perform(get("/api/v1/dashboard"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHORIZED"));
        verifyNoInteractions(dashboardService);
    }

    @Test
    void nonNumericRecentLimitIsA400NotA500() throws Exception {
        loggedIn();

        mvc.perform(get("/api/v1/dashboard?recentLimit=abc").header("Authorization", "Bearer good"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.fieldErrors[0].field").value("recentLimit"));
        verifyNoInteractions(dashboardService);
    }

    @Test
    void invalidMonthFromTheServiceIsA400() throws Exception {
        loggedIn();
        when(dashboardService.getDashboard(any(), eq("2030-01"), anyInt())).thenThrow(new ApiException(
                ErrorCode.VALIDATION_FAILED, "Some fields are invalid.", Map.of(),
                List.of(new FieldErrorDetail("month", "Invalid", "Cannot be in the future")), null));

        mvc.perform(get("/api/v1/dashboard?month=2030-01").header("Authorization", "Bearer good"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors[0].field").value("month"))
                .andExpect(jsonPath("$.fieldErrors[0].message").value("Cannot be in the future"));
    }
}
