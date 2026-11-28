package com.masroofy.backend.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.masroofy.backend.dto.request.CreateTransactionRequest;
import com.masroofy.backend.dto.response.TransactionResponse;
import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.exception.FieldErrorDetail;
import com.masroofy.backend.model.Account;
import com.masroofy.backend.model.Category;
import com.masroofy.backend.model.NewTransaction;
import com.masroofy.backend.model.User;
import com.masroofy.backend.repository.AccountRepository;
import com.masroofy.backend.repository.AuditLogRepository;
import com.masroofy.backend.repository.CategoryRepository;
import com.masroofy.backend.repository.TransactionRepository;
import com.masroofy.backend.repository.TransactionRepository.TransactionRow;
import com.masroofy.backend.repository.UserRepository;
import com.masroofy.backend.service.TransactionService.CreateResult;
import java.math.BigDecimal;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.transaction.PlatformTransactionManager;

@ExtendWith(MockitoExtension.class)
class TransactionServiceTest {

    private static final UUID USER_ID = UUID.fromString("22222222-2222-2222-2222-222222222222");
    private static final UUID CIB = UUID.fromString("33333333-3333-3333-3333-333333333333");
    private static final UUID GROCERIES = UUID.fromString("0c0a0000-0000-4000-8000-000000000001");
    private static final UUID SALARY = UUID.fromString("0c0a0000-0000-4000-8000-000000000101");
    private static final ZoneId CAIRO = ZoneId.of("Africa/Cairo");
    /** 20 Nov 2026, 12:00 in Cairo (UTC+2). */
    private static final Instant NOW = Instant.parse("2026-11-20T10:00:00Z");
    private static final LocalDate TODAY = LocalDate.of(2026, 11, 20);

    @Mock
    private UserRepository userRepository;
    @Mock
    private AccountRepository accountRepository;
    @Mock
    private CategoryRepository categoryRepository;
    @Mock
    private TransactionRepository transactionRepository;
    @Mock
    private AuditLogRepository auditLogRepository;
    @Mock
    private FxRateService fxRateService;

    private TransactionService service;

    private static Account account(String currency) {
        return new Account(CIB, USER_ID, "CIB Account", "bank", currency, "4821", false, NOW);
    }

    private static CreateTransactionRequest request(String type, String amount, String key, LocalDate date,
                                                    String time, UUID clientRequestId) {
        return new CreateTransactionRequest(clientRequestId, type, new BigDecimal(amount), "  Carrefour ", key, null,
                date, time, CIB, "  Weekly groceries  ");
    }

    private static CreateTransactionRequest expense(LocalDate date, String time) {
        return request("EXPENSE", "850.00", "groceries", date, time, UUID.randomUUID());
    }

    /** What the repository gives back for the row the service just inserted. */
    private static TransactionRow rowOf(NewTransaction tx) {
        return new TransactionRow(tx.id(), tx.type(), tx.amount(), tx.currency(), tx.fxRateToBase(), tx.occurredAt(),
                tx.merchant(), tx.note(), "manual", "confirmed", tx.categoryId(), "groceries", "Groceries", CIB,
                "CIB Account", tx.clientRequestId(), tx.createdAt());
    }

    @BeforeEach
    void setUp() {
        service = new TransactionService(userRepository, accountRepository, categoryRepository, transactionRepository,
                auditLogRepository, fxRateService, new ObjectMapper(), mock(PlatformTransactionManager.class),
                Clock.fixed(NOW, ZoneOffset.UTC));
        lenient().when(userRepository.findById(USER_ID)).thenReturn(Optional.of(new User(USER_ID, "uid-1",
                "mariam@example.com", null, "Mariam Ali", "EGP", "en", "Africa/Cairo", null, NOW, NOW, NOW, NOW)));
        lenient().when(transactionRepository.findByClientRequestId(eq(USER_ID), any())).thenReturn(Optional.empty());
        lenient().when(accountRepository.findOpen(USER_ID, CIB)).thenReturn(Optional.of(account("EGP")));
        lenient().when(categoryRepository.findVisibleByKey(USER_ID, "groceries"))
                .thenReturn(Optional.of(new Category(GROCERIES, null, "Groceries", "expense", "groceries", false)));
        lenient().when(categoryRepository.findVisibleByKey(USER_ID, "salary"))
                .thenReturn(Optional.of(new Category(SALARY, null, "Salary", "income", "salary", false)));
        lenient().when(fxRateService.rate(eq("EGP"), eq("EGP"), any())).thenReturn(Optional.of(BigDecimal.ONE));
        // Read back exactly what was inserted.
        lenient().doAnswer(invocation -> {
            NewTransaction tx = invocation.getArgument(0);
            lenient().when(transactionRepository.findVisible(USER_ID, tx.id())).thenReturn(Optional.of(rowOf(tx)));
            return null;
        }).when(transactionRepository).insert(any());
    }

    private NewTransaction inserted() {
        ArgumentCaptor<NewTransaction> captor = ArgumentCaptor.forClass(NewTransaction.class);
        verify(transactionRepository).insert(captor.capture());
        return captor.getValue();
    }

    private static ApiException validationError(Runnable call) {
        try {
            call.run();
        } catch (ApiException e) {
            assertThat(e.getErrorCode()).isEqualTo(ErrorCode.VALIDATION_FAILED);
            return e;
        }
        throw new AssertionError("Expected VALIDATION_FAILED");
    }

    // ---- Saving ----------------------------------------------------------------------------------------------------

    @Test
    void savesAnExpenseWithAPositiveAmountTrimmedTextAndTheAccountCurrency() {
        CreateResult result = service.create(USER_ID, expense(TODAY, null));

        NewTransaction tx = inserted();
        assertThat(tx.type()).isEqualTo("expense");
        assertThat(tx.amount()).isEqualByComparingTo("850.00");
        assertThat(tx.amount().scale()).isEqualTo(2);
        assertThat(tx.currency()).isEqualTo("EGP");
        assertThat(tx.fxRateToBase()).isEqualByComparingTo("1");
        assertThat(tx.categoryId()).isEqualTo(GROCERIES);
        assertThat(tx.merchant()).isEqualTo("Carrefour");
        assertThat(tx.note()).isEqualTo("Weekly groceries");
        assertThat(tx.fingerprint()).hasSize(64);
        assertThat(tx.createdAt()).isEqualTo(NOW);

        assertThat(result.created()).isTrue();
        TransactionResponse body = result.transaction();
        assertThat(body.type()).isEqualTo("EXPENSE");
        assertThat(body.title()).isEqualTo("Carrefour");
        assertThat(body.signedAmount()).isEqualByComparingTo("-850.00");
        assertThat(body.amountInBase()).isEqualByComparingTo("850.00");
        assertThat(body.category().key()).isEqualTo("groceries");
        assertThat(body.account().id()).isEqualTo(CIB);
        assertThat(body.date()).isEqualTo(TODAY);
        assertThat(body.time()).isEqualTo("12:00");
    }

    @Test
    void writesTheAuditRowForTheSameTransaction() {
        service.create(USER_ID, expense(TODAY, null));

        NewTransaction tx = inserted();
        ArgumentCaptor<String> after = ArgumentCaptor.forClass(String.class);
        verify(auditLogRepository).insert(any(), eq(USER_ID), eq("transaction"), eq(tx.id()), eq("create"), isNull(),
                after.capture(), eq(NOW));
        assertThat(after.getValue()).contains("\"amount\":\"850.00\"", "\"type\":\"expense\"", "\"merchant\":\"Carrefour\"");
    }

    @Test
    void savesAnIncomeWithAPositiveSignedAmount() {
        CreateResult result = service.create(USER_ID,
                request("INCOME", "30000", "salary", TODAY, null, UUID.randomUUID()));

        assertThat(inserted().type()).isEqualTo("income");
        assertThat(result.transaction().signedAmount()).isEqualByComparingTo("30000.00");
    }

    @Test
    void todayWithoutATimeIsNow() {
        service.create(USER_ID, expense(TODAY, null));

        assertThat(inserted().occurredAt()).isEqualTo(NOW);
    }

    @Test
    void anEarlierDayWithoutATimeIsMiddayInTheUsersZone() {
        service.create(USER_ID, expense(LocalDate.of(2026, 11, 1), null));

        assertThat(inserted().occurredAt()).isEqualTo(Instant.parse("2026-11-01T10:00:00Z"));
    }

    @Test
    void aGivenTimeIsLocalToTheUsersZone() {
        service.create(USER_ID, expense(LocalDate.of(2026, 11, 19), "23:30"));

        assertThat(inserted().occurredAt()).isEqualTo(Instant.parse("2026-11-19T21:30:00Z"));
    }

    @Test
    void foreignCurrencyAccountsStoreTheRateAtThatMoment() {
        when(accountRepository.findOpen(USER_ID, CIB)).thenReturn(Optional.of(account("USD")));
        when(fxRateService.rate("USD", "EGP", NOW)).thenReturn(Optional.of(new BigDecimal("48.50000000")));

        CreateResult result = service.create(USER_ID, request("EXPENSE", "10.00", "groceries", TODAY, null,
                UUID.randomUUID()));

        assertThat(inserted().fxRateToBase()).isEqualByComparingTo("48.5");
        assertThat(result.transaction().amountInBase()).isEqualByComparingTo("485.00");
    }

    @Test
    void noExchangeRateIsFxRateUnavailable() {
        when(accountRepository.findOpen(USER_ID, CIB)).thenReturn(Optional.of(account("CHF")));
        when(fxRateService.rate(eq("CHF"), eq("EGP"), any())).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.create(USER_ID, expense(TODAY, null)))
                .isInstanceOf(ApiException.class)
                .extracting("errorCode").isEqualTo(ErrorCode.FX_RATE_UNAVAILABLE);
        verify(transactionRepository, never()).insert(any());
    }

    @Test
    void fingerprintIgnoresTitleCaseButNotTheAmount() {
        LocalDate date = LocalDate.of(2026, 11, 1);
        String a = TransactionService.fingerprint(USER_ID, CIB, "expense", new BigDecimal("850.00"), date, "Carrefour");
        String b = TransactionService.fingerprint(USER_ID, CIB, "expense", new BigDecimal("850.00"), date, "CARREFOUR");
        String c = TransactionService.fingerprint(USER_ID, CIB, "expense", new BigDecimal("851.00"), date, "Carrefour");

        assertThat(a).isEqualTo(b).isNotEqualTo(c).matches("[0-9a-f]{64}");
    }

    // ---- Validation ------------------------------------------------------------------------------------------------

    @Test
    void aFutureDateIsRefused() {
        ApiException e = validationError(() -> service.create(USER_ID, expense(TODAY.plusDays(1), null)));

        assertThat(e.getFieldErrors()).containsExactly(new FieldErrorDetail("date", "InFuture", "Cannot be in the future"));
        verify(transactionRepository, never()).insert(any());
    }

    @Test
    void laterTodayIsRefused() {
        ApiException e = validationError(() -> service.create(USER_ID, expense(TODAY, "12:01")));

        assertThat(e.getFieldErrors()).extracting(FieldErrorDetail::field, FieldErrorDetail::code)
                .containsExactly(org.assertj.core.groups.Tuple.tuple("time", "InFuture"));
    }

    @Test
    void aDateBefore2000IsRefused() {
        ApiException e = validationError(() -> service.create(USER_ID, expense(LocalDate.of(1999, 12, 31), null)));

        assertThat(e.getFieldErrors()).extracting(FieldErrorDetail::code).containsExactly("Invalid");
    }

    @Test
    void anotherUsersOrArchivedAccountIsNotFound() {
        when(accountRepository.findOpen(USER_ID, CIB)).thenReturn(Optional.empty());

        ApiException e = validationError(() -> service.create(USER_ID, expense(TODAY, null)));

        assertThat(e.getFieldErrors()).extracting(FieldErrorDetail::field, FieldErrorDetail::code)
                .containsExactly(org.assertj.core.groups.Tuple.tuple("accountId", "NotFound"));
    }

    @Test
    void anIncomeCategoryOnAnExpenseIsAKindMismatch() {
        ApiException e = validationError(() -> service.create(USER_ID,
                request("EXPENSE", "10", "salary", TODAY, null, UUID.randomUUID())));

        assertThat(e.getFieldErrors()).extracting(FieldErrorDetail::field, FieldErrorDetail::code)
                .containsExactly(org.assertj.core.groups.Tuple.tuple("categoryKey", "KindMismatch"));
    }

    @Test
    void anUnknownCategoryKeyIsNotFound() {
        when(categoryRepository.findVisibleByKey(USER_ID, "pets")).thenReturn(Optional.empty());

        ApiException e = validationError(() -> service.create(USER_ID,
                request("EXPENSE", "10", "pets", TODAY, null, UUID.randomUUID())));

        assertThat(e.getFieldErrors()).extracting(FieldErrorDetail::code).containsExactly("NotFound");
    }

    @Test
    void exactlyOneOfCategoryKeyAndCategoryIdIsNeeded() {
        CreateTransactionRequest neither = new CreateTransactionRequest(UUID.randomUUID(), "EXPENSE",
                new BigDecimal("10"), "Uber", null, null, TODAY, null, CIB, null);
        CreateTransactionRequest both = new CreateTransactionRequest(UUID.randomUUID(), "EXPENSE",
                new BigDecimal("10"), "Uber", "groceries", GROCERIES, TODAY, null, CIB, null);

        assertThat(validationError(() -> service.create(USER_ID, neither)).getFieldErrors())
                .extracting(FieldErrorDetail::code).containsExactly("NotNull");
        assertThat(validationError(() -> service.create(USER_ID, both)).getFieldErrors())
                .extracting(FieldErrorDetail::code).containsExactly("Invalid");
    }

    @Test
    void reportsEveryProblemAtOnce() {
        when(accountRepository.findOpen(USER_ID, CIB)).thenReturn(Optional.empty());

        ApiException e = validationError(() -> service.create(USER_ID,
                request("EXPENSE", "10", "salary", TODAY.plusDays(2), null, UUID.randomUUID())));

        assertThat(e.getFieldErrors()).extracting(FieldErrorDetail::field)
                .containsExactly("accountId", "categoryKey", "date");
    }

    @Test
    void aDatabaseRuleViolationIsA400NotA500() {
        doThrow(new DataIntegrityViolationException("check_violation")).when(transactionRepository).insert(any());

        validationError(() -> service.create(USER_ID, expense(TODAY, null)));
    }

    // ---- Idempotency -----------------------------------------------------------------------------------------------

    @Test
    void theSameRequestAgainReturnsTheFirstTransactionWithoutSaving() {
        CreateTransactionRequest first = expense(TODAY, null);
        service.create(USER_ID, first);
        TransactionRow saved = rowOf(inserted());
        when(transactionRepository.findByClientRequestId(USER_ID, first.clientRequestId()))
                .thenReturn(Optional.of(saved));

        CreateResult again = service.create(USER_ID, first);

        assertThat(again.created()).isFalse();
        assertThat(again.transaction().id()).isEqualTo(saved.id());
        verify(transactionRepository).insert(any());   // still only the first one
    }

    @Test
    void theSameRequestIdWithADifferentAmountIsAConflict() {
        CreateTransactionRequest first = expense(TODAY, null);
        service.create(USER_ID, first);
        TransactionRow saved = rowOf(inserted());
        when(transactionRepository.findByClientRequestId(USER_ID, first.clientRequestId()))
                .thenReturn(Optional.of(saved));

        CreateTransactionRequest edited = request("EXPENSE", "900.00", "groceries", TODAY, null,
                first.clientRequestId());

        assertThatThrownBy(() -> service.create(USER_ID, edited))
                .isInstanceOf(ApiException.class)
                .extracting("errorCode").isEqualTo(ErrorCode.IDEMPOTENCY_KEY_REUSED);
    }

    @Test
    void losingARaceOnTheRequestIdReturnsTheWinner() {
        CreateTransactionRequest req = expense(LocalDate.of(2026, 11, 1), null);
        TransactionRow winner = new TransactionRow(UUID.randomUUID(), "expense", new BigDecimal("850.00"), "EGP",
                BigDecimal.ONE, Instant.parse("2026-11-01T10:00:00Z"), "Carrefour", "Weekly groceries", "manual",
                "confirmed", GROCERIES, "groceries", "Groceries", CIB, "CIB Account", req.clientRequestId(), NOW);
        doThrow(new DuplicateKeyException("uk_transactions_client_request")).when(transactionRepository).insert(any());
        when(transactionRepository.findByClientRequestId(USER_ID, req.clientRequestId()))
                .thenReturn(Optional.empty(), Optional.of(winner));

        CreateResult result = service.create(USER_ID, req);

        assertThat(result.created()).isFalse();
        assertThat(result.transaction().id()).isEqualTo(winner.id());
    }

    // ---- Read ------------------------------------------------------------------------------------------------------

    @Test
    void getUnknownOrOtherUsersTransactionIsNotFound() {
        UUID id = UUID.randomUUID();
        when(transactionRepository.findVisible(USER_ID, id)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.get(USER_ID, id))
                .isInstanceOf(ApiException.class)
                .extracting("errorCode").isEqualTo(ErrorCode.NOT_FOUND);
    }

    @Test
    void occurredAtRuleIsStableAcrossTimeZones() {
        Instant at = TransactionService.occurredAt(LocalDate.of(2026, 3, 29), null, ZoneId.of("Europe/London"), NOW);
        assertThat(at.atZone(ZoneId.of("Europe/London")).toLocalDate()).isEqualTo(LocalDate.of(2026, 3, 29));
        assertThat(TransactionService.occurredAt(TODAY, null, CAIRO, NOW)).isEqualTo(NOW);
        verify(fxRateService, never()).rate(anyString(), anyString(), any());
    }
}
