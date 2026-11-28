package com.masroofy.backend.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.masroofy.backend.dto.response.DashboardResponse.AccountRef;
import com.masroofy.backend.dto.response.DashboardResponse.CategoryRef;
import com.masroofy.backend.dto.response.TransactionResponse;
import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.firebase.FirebaseIdentityClient;
import com.masroofy.backend.firebase.VerifiedToken;
import com.masroofy.backend.model.User;
import com.masroofy.backend.repository.UserRepository;
import com.masroofy.backend.service.TransactionService;
import com.masroofy.backend.service.TransactionService.CreateResult;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder;

@WebMvcTest(TransactionController.class)
@Import(WebLayerTestConfig.class)
class TransactionControllerTest {

    private static final UUID USER_ID = UUID.fromString("22222222-2222-2222-2222-222222222222");
    private static final UUID TX_ID = UUID.fromString("44444444-4444-4444-4444-444444444444");
    private static final Instant NOW = Instant.parse("2026-11-20T10:00:00Z");

    private static final String VALID_BODY = """
            {"clientRequestId":"6f1c0b9e-3d1a-4a57-9d55-0d3c2c8f4a10","type":"EXPENSE","amount":"850.00",
             "title":"Carrefour","categoryKey":"groceries","date":"2026-11-20",
             "accountId":"33333333-3333-3333-3333-333333333333","note":"Weekly groceries"}""";

    @Autowired
    private MockMvc mvc;

    @MockitoBean
    private TransactionService transactionService;
    @MockitoBean
    private FirebaseIdentityClient firebase;
    @MockitoBean
    private UserRepository userRepository;

    private void loggedIn() {
        when(firebase.verifyIdToken("good", true)).thenReturn(new VerifiedToken("uid-1", "mariam@example.com"));
        when(userRepository.findByFirebaseUid("uid-1")).thenReturn(Optional.of(new User(USER_ID, "uid-1",
                "mariam@example.com", null, "Mariam Ali", "EGP", "en", "Africa/Cairo", null, NOW, NOW, NOW, NOW)));
    }

    private static TransactionResponse sample() {
        return new TransactionResponse(TX_ID, "EXPENSE", "Carrefour", "Carrefour", "Weekly groceries",
                new CategoryRef(UUID.randomUUID(), "groceries", "Groceries"),
                new AccountRef(UUID.fromString("33333333-3333-3333-3333-333333333333"), "CIB Account"),
                new BigDecimal("850.00"), new BigDecimal("-850.00"), "EGP", new BigDecimal("850.00"),
                LocalDate.of(2026, 11, 20), "12:00", NOW, "manual", "confirmed", NOW);
    }

    private static MockHttpServletRequestBuilder postJson(String body) {
        return post("/api/v1/transactions").header("Authorization", "Bearer good")
                .contentType(MediaType.APPLICATION_JSON).content(body);
    }

    @Test
    void createReturns201WithLocationAndMoneyAsStrings() throws Exception {
        loggedIn();
        when(transactionService.create(eq(USER_ID), any())).thenReturn(new CreateResult(sample(), true));

        mvc.perform(postJson(VALID_BODY))
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", "/api/v1/transactions/" + TX_ID))
                .andExpect(jsonPath("$.id").value(TX_ID.toString()))
                .andExpect(jsonPath("$.type").value("EXPENSE"))
                .andExpect(jsonPath("$.amount").value("850.00"))
                .andExpect(jsonPath("$.signedAmount").value("-850.00"))
                .andExpect(jsonPath("$.category.key").value("groceries"))
                .andExpect(jsonPath("$.account.name").value("CIB Account"))
                .andExpect(jsonPath("$.date").value("2026-11-20"))
                .andExpect(jsonPath("$.time").value("12:00"))
                .andExpect(jsonPath("$.occurredAt").value("2026-11-20T10:00:00Z"));
    }

    @Test
    void aRetryOfASavedRequestIs200() throws Exception {
        loggedIn();
        when(transactionService.create(eq(USER_ID), any())).thenReturn(new CreateResult(sample(), false));

        mvc.perform(postJson(VALID_BODY))
                .andExpect(status().isOk())
                .andExpect(header().doesNotExist("Location"))
                .andExpect(jsonPath("$.id").value(TX_ID.toString()));
    }

    @Test
    void formatErrorsComeBackTogetherWithoutCallingTheService() throws Exception {
        loggedIn();

        mvc.perform(postJson("""
                        {"type":"TRANSFER","amount":"-5.123","title":" ","date":"2026-11-20","time":"25:00"}"""))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.fieldErrors[?(@.field == 'clientRequestId')].code").value("NotNull"))
                .andExpect(jsonPath("$.fieldErrors[?(@.field == 'type')].code").value("Pattern"))
                .andExpect(jsonPath("$.fieldErrors[?(@.field == 'title')].code").value("NotBlank"))
                .andExpect(jsonPath("$.fieldErrors[?(@.field == 'time')].code").value("Pattern"))
                .andExpect(jsonPath("$.fieldErrors[?(@.field == 'accountId')].code").value("NotNull"));
        verifyNoInteractions(transactionService);
    }

    @Test
    void anAmountWithThreeDecimalsIsRefused() throws Exception {
        loggedIn();

        mvc.perform(postJson(VALID_BODY.replace("\"850.00\"", "\"850.125\"")))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors[0].field").value("amount"))
                .andExpect(jsonPath("$.fieldErrors[0].code").value("Digits"));
        verifyNoInteractions(transactionService);
    }

    @Test
    void aNonUuidIdInTheBodyIsMalformed() throws Exception {
        loggedIn();

        mvc.perform(postJson(VALID_BODY.replace("33333333-3333-3333-3333-333333333333", "cib-4821")))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("MALFORMED_REQUEST"));
        verifyNoInteractions(transactionService);
    }

    @Test
    void conflictAndMissingRateKeepTheirCodes() throws Exception {
        loggedIn();
        when(transactionService.create(eq(USER_ID), any()))
                .thenThrow(new ApiException(ErrorCode.IDEMPOTENCY_KEY_REUSED))
                .thenThrow(new ApiException(ErrorCode.FX_RATE_UNAVAILABLE));

        mvc.perform(postJson(VALID_BODY))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("IDEMPOTENCY_KEY_REUSED"));
        mvc.perform(postJson(VALID_BODY))
                .andExpect(status().isUnprocessableEntity())
                .andExpect(jsonPath("$.code").value("FX_RATE_UNAVAILABLE"));
    }

    @Test
    void createRequiresAToken() throws Exception {
        mvc.perform(post("/api/v1/transactions").contentType(MediaType.APPLICATION_JSON).content(VALID_BODY))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHORIZED"));
        verifyNoInteractions(transactionService);
    }

    @Test
    void getReturnsTheTransaction() throws Exception {
        loggedIn();
        when(transactionService.get(USER_ID, TX_ID)).thenReturn(sample());

        mvc.perform(get("/api/v1/transactions/" + TX_ID).header("Authorization", "Bearer good"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Carrefour"));
    }

    @Test
    void getUnknownIsA404() throws Exception {
        loggedIn();
        when(transactionService.get(USER_ID, TX_ID)).thenThrow(new ApiException(ErrorCode.NOT_FOUND));

        mvc.perform(get("/api/v1/transactions/" + TX_ID).header("Authorization", "Bearer good"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.code").value("NOT_FOUND"));
    }

    @Test
    void getWithABadIdIsA400NotA500() throws Exception {
        loggedIn();

        mvc.perform(get("/api/v1/transactions/txn-1").header("Authorization", "Bearer good"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors[0].code").value("TypeMismatch"));
        verifyNoInteractions(transactionService);
    }
}
