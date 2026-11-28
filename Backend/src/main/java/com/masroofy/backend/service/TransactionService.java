package com.masroofy.backend.service;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.masroofy.backend.dto.request.CreateTransactionRequest;
import com.masroofy.backend.dto.response.DashboardResponse.AccountRef;
import com.masroofy.backend.dto.response.DashboardResponse.CategoryRef;
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
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * Adds and reads manual income / expense transactions (Figma 03-06 → 03-14). Spec: Backend/docs/add-transaction.md.
 *
 * <p>Rules: the amount is stored positive with {@code type} giving the direction; the currency is the account's;
 * {@code fx_rate_to_base} is fixed at the moment the money moved; a date without a time becomes "now" for today and
 * midday (user's zone) for an earlier day; a repeated {@code clientRequestId} never creates a second row; every
 * create writes an AUDIT_LOG row in the same database transaction.
 */
@Service
public class TransactionService {

    /** The created or already existing transaction, and whether this request created it (201) or not (200). */
    public record CreateResult(TransactionResponse transaction, boolean created) {
    }

    static final LocalDate OLDEST_DATE = LocalDate.of(2000, 1, 1);
    static final LocalTime DEFAULT_TIME = LocalTime.NOON;

    private static final Logger log = LoggerFactory.getLogger(TransactionService.class);
    private static final DateTimeFormatter TIME = DateTimeFormatter.ofPattern("HH:mm");
    private static final String EXPENSE = "expense";

    private final UserRepository userRepository;
    private final AccountRepository accountRepository;
    private final CategoryRepository categoryRepository;
    private final TransactionRepository transactionRepository;
    private final AuditLogRepository auditLogRepository;
    private final FxRateService fxRateService;
    private final ObjectMapper objectMapper;
    private final TransactionTemplate transactionTemplate;
    private final Clock clock;

    public TransactionService(UserRepository userRepository, AccountRepository accountRepository,
                              CategoryRepository categoryRepository, TransactionRepository transactionRepository,
                              AuditLogRepository auditLogRepository, FxRateService fxRateService,
                              ObjectMapper objectMapper, PlatformTransactionManager transactionManager, Clock clock) {
        this.userRepository = userRepository;
        this.accountRepository = accountRepository;
        this.categoryRepository = categoryRepository;
        this.transactionRepository = transactionRepository;
        this.auditLogRepository = auditLogRepository;
        this.fxRateService = fxRateService;
        this.objectMapper = objectMapper;
        this.transactionTemplate = new TransactionTemplate(transactionManager);
        this.clock = clock;
    }

    // ---- Create ----------------------------------------------------------------------------------------------------

    public CreateResult create(UUID userId, CreateTransactionRequest request) {
        User user = loadUser(userId);
        ZoneId zone = DashboardService.zoneOf(user.timezone());
        Instant now = clock.instant();

        Optional<TransactionRow> earlier = transactionRepository.findByClientRequestId(userId,
                request.clientRequestId());
        if (earlier.isPresent()) {
            return replay(earlier.get(), request, zone);
        }

        String type = request.type().toLowerCase(Locale.ROOT);
        List<FieldErrorDetail> errors = new ArrayList<>();
        Account account = accountRepository.findOpen(userId, request.accountId()).orElse(null);
        if (account == null) {
            errors.add(new FieldErrorDetail("accountId", "NotFound", "Choose one of your accounts"));
        }
        Category category = resolveCategory(userId, request, type, errors);
        LocalTime time = request.time() == null ? null : LocalTime.parse(request.time(), TIME);
        checkDate(request.date(), time, zone, now, errors);
        if (!errors.isEmpty()) {
            throw new ApiException(ErrorCode.VALIDATION_FAILED, ErrorCode.VALIDATION_FAILED.defaultMessage(),
                    Map.of(), errors, null);
        }

        Instant occurredAt = occurredAt(request.date(), time, zone, now);
        BigDecimal fxRate = fxRateService.rate(account.currency(), user.baseCurrency(), occurredAt)
                .orElseThrow(() -> new ApiException(ErrorCode.FX_RATE_UNAVAILABLE));
        BigDecimal amount = request.amount().setScale(2, RoundingMode.UNNECESSARY);
        String title = request.title().trim();
        NewTransaction tx = new NewTransaction(UUID.randomUUID(), userId, account.id(), category.id(), type, amount,
                account.currency(), fxRate, occurredAt, title, trimToNull(request.note()),
                fingerprint(userId, account.id(), type, amount, request.date(), title), request.clientRequestId(),
                now);

        try {
            transactionTemplate.executeWithoutResult(status -> {
                transactionRepository.insert(tx);
                auditLogRepository.insert(UUID.randomUUID(), userId, AuditLogRepository.ENTITY_TRANSACTION, tx.id(),
                        AuditLogRepository.ACTION_CREATE, null, auditJson(tx), now);
            });
        } catch (DuplicateKeyException e) {
            // Another request with the same clientRequestId committed first.
            TransactionRow winner = transactionRepository.findByClientRequestId(userId, request.clientRequestId())
                    .orElseThrow(() -> e);
            return replay(winner, request, zone);
        } catch (DataIntegrityViolationException e) {
            // A database rule (CHECK or trigger) the checks above should have caught, e.g. a category changed meanwhile.
            log.warn("Transaction for user {} refused by the database: {}", userId, e.getMostSpecificCause().getMessage());
            throw new ApiException(ErrorCode.VALIDATION_FAILED);
        }

        TransactionRow saved = transactionRepository.findVisible(userId, tx.id())
                .orElseThrow(() -> new ApiException(ErrorCode.INTERNAL_ERROR));
        return new CreateResult(toResponse(saved, zone), true);
    }

    // ---- Read ------------------------------------------------------------------------------------------------------

    public TransactionResponse get(UUID userId, UUID transactionId) {
        User user = loadUser(userId);
        return transactionRepository.findVisible(userId, transactionId)
                .map(row -> toResponse(row, DashboardService.zoneOf(user.timezone())))
                .orElseThrow(() -> new ApiException(ErrorCode.NOT_FOUND));
    }

    // ---- Rules -----------------------------------------------------------------------------------------------------

    private Category resolveCategory(UUID userId, CreateTransactionRequest request, String type,
                                     List<FieldErrorDetail> errors) {
        boolean byKey = request.categoryKey() != null && !request.categoryKey().isBlank();
        boolean byId = request.categoryId() != null;
        if (byKey == byId) {
            errors.add(byKey
                    ? new FieldErrorDetail("categoryKey", "Invalid", "Send categoryKey or categoryId, not both")
                    : new FieldErrorDetail("categoryKey", "NotNull", "Choose a category"));
            return null;
        }
        String field = byKey ? "categoryKey" : "categoryId";
        Optional<Category> found = byKey
                ? categoryRepository.findVisibleByKey(userId, request.categoryKey().trim())
                : categoryRepository.findVisibleById(userId, request.categoryId());
        if (found.isEmpty()) {
            errors.add(new FieldErrorDetail(field, "NotFound", "Choose one of the categories"));
            return null;
        }
        if (!found.get().kind().equals(type)) {
            errors.add(new FieldErrorDetail(field, "KindMismatch",
                    "This is an " + found.get().kind() + " category; choose an " + type + " category"));
            return null;
        }
        return found.get();
    }

    private static void checkDate(LocalDate date, LocalTime time, ZoneId zone, Instant now,
                                  List<FieldErrorDetail> errors) {
        ZonedDateTime localNow = now.atZone(zone);
        if (date.isBefore(OLDEST_DATE)) {
            errors.add(new FieldErrorDetail("date", "Invalid", "Must be " + OLDEST_DATE + " or later"));
        } else if (date.isAfter(localNow.toLocalDate())) {
            errors.add(new FieldErrorDetail("date", "InFuture", "Cannot be in the future"));
        } else if (time != null && date.equals(localNow.toLocalDate())
                && LocalDateTime.of(date, time).isAfter(localNow.toLocalDateTime())) {
            errors.add(new FieldErrorDetail("time", "InFuture", "Cannot be in the future"));
        }
    }

    /** The given time; else now for today; else midday, which keeps the date in its day and month whatever the DST. */
    static Instant occurredAt(LocalDate date, LocalTime time, ZoneId zone, Instant now) {
        if (time != null) {
            return LocalDateTime.of(date, time).atZone(zone).toInstant();
        }
        if (date.equals(now.atZone(zone).toLocalDate())) {
            return now;
        }
        return LocalDateTime.of(date, DEFAULT_TIME).atZone(zone).toInstant();
    }

    /** SHA-256 of what identifies a payment, for duplicate detection later (64 hex characters). */
    static String fingerprint(UUID userId, UUID accountId, String type, BigDecimal amount, LocalDate date,
                              String title) {
        String key = String.join("|", userId.toString(), accountId.toString(), type, amount.toPlainString(),
                date.toString(), title.toLowerCase(Locale.ROOT));
        try {
            byte[] hash = MessageDigest.getInstance("SHA-256").digest(key.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 is not available", e);
        }
    }

    /** A repeated clientRequestId: the same transaction again is fine, a different one is refused. */
    private CreateResult replay(TransactionRow row, CreateTransactionRequest request, ZoneId zone) {
        if (!sameContent(row, request, zone)) {
            throw new ApiException(ErrorCode.IDEMPOTENCY_KEY_REUSED);
        }
        return new CreateResult(toResponse(row, zone), false);
    }

    static boolean sameContent(TransactionRow row, CreateTransactionRequest request, ZoneId zone) {
        ZonedDateTime local = row.occurredAt().atZone(zone);
        boolean sameCategory = request.categoryId() != null
                ? request.categoryId().equals(row.categoryId())
                : request.categoryKey() != null && request.categoryKey().trim().equals(row.categoryKey());
        return row.type().equals(request.type().toLowerCase(Locale.ROOT))
                && row.amount().compareTo(request.amount()) == 0
                && row.merchant() != null && row.merchant().equals(request.title().trim())
                && sameCategory
                && row.accountId().equals(request.accountId())
                && local.toLocalDate().equals(request.date())
                && (request.time() == null || TIME.format(local).equals(request.time()))
                && Objects.equals(row.note(), trimToNull(request.note()));
    }

    // ---- Mapping ---------------------------------------------------------------------------------------------------

    static TransactionResponse toResponse(TransactionRow row, ZoneId zone) {
        ZonedDateTime local = row.occurredAt().atZone(zone);
        BigDecimal amount = DashboardService.money(row.amount());
        boolean expense = EXPENSE.equals(row.type());
        String title = row.merchant() != null && !row.merchant().isBlank() ? row.merchant() : row.categoryName();
        CategoryRef category = row.categoryId() == null ? null
                : new CategoryRef(row.categoryId(), row.categoryKey(), row.categoryName());
        return new TransactionResponse(
                row.id(),
                row.type().toUpperCase(Locale.ROOT),
                title,
                row.merchant(),
                row.note(),
                category,
                new AccountRef(row.accountId(), row.accountName()),
                amount,
                expense ? amount.negate() : amount,
                row.currency(),
                DashboardService.money(row.amount().multiply(row.fxRateToBase())),
                local.toLocalDate(),
                TIME.format(local),
                row.occurredAt(),
                row.source(),
                row.status(),
                row.createdAt());
    }

    /** The row as written, for AUDIT_LOG.after: snake_case keys, money and times as strings. */
    private String auditJson(NewTransaction tx) {
        Map<String, Object> after = new LinkedHashMap<>();
        after.put("id", tx.id().toString());
        after.put("account_id", tx.accountId().toString());
        after.put("category_id", tx.categoryId().toString());
        after.put("type", tx.type());
        after.put("amount", tx.amount().toPlainString());
        after.put("currency", tx.currency());
        after.put("fx_rate_to_base", tx.fxRateToBase().toPlainString());
        after.put("occurred_at", tx.occurredAt().toString());
        after.put("merchant", tx.merchant());
        after.put("note", tx.note());
        after.put("source", NewTransaction.SOURCE_MANUAL);
        after.put("status", NewTransaction.STATUS_CONFIRMED);
        after.put("fingerprint", tx.fingerprint());
        after.put("client_request_id", tx.clientRequestId().toString());
        after.put("created_at", tx.createdAt().toString());
        try {
            return objectMapper.writeValueAsString(after);
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Could not write the audit record", e);
        }
    }

    private User loadUser(UUID userId) {
        return userRepository.findById(userId).orElseThrow(() -> new ApiException(ErrorCode.USER_NOT_FOUND));
    }

    private static String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }
}
