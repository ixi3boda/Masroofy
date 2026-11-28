package com.masroofy.transaction;

import com.masroofy.common.ApiException;
import com.masroofy.common.CurrentUser;
import jakarta.persistence.criteria.Predicate;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import tools.jackson.databind.JsonNode;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.YearMonth;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.TreeMap;

@Service
@Transactional
public class TransactionService {

    public static final int MAX_LIMIT = 500;

    private final TransactionRepository repository;
    private final CurrentUser currentUser;
    private final ZoneId zone;

    public TransactionService(TransactionRepository repository, CurrentUser currentUser,
                              @Value("${app.timezone:Africa/Cairo}") String timezone) {
        this.repository = repository;
        this.currentUser = currentUser;
        this.zone = ZoneId.of(timezone);
    }

    /**
     * Save what the voice service returned from /v1/expenses/confirm: the draft with the user's
     * corrections applied and already validated by Python.
     */
    public Transaction saveConfirmedVoice(JsonNode confirmed) {
        Transaction t = new Transaction();
        t.setUserId(currentUser.id());
        t.setTransactionType(orDefault(text(confirmed, "transaction_type"), "expense"));
        JsonNode amount = confirmed.path("amount");
        if (!amount.isNumber()) {
            throw new ApiException(org.springframework.http.HttpStatus.UNPROCESSABLE_CONTENT, "amount_required",
                    "An amount is required before saving. Please enter the amount.");
        }
        t.setAmount(money(amount.decimalValue()));
        t.setCurrency(orDefault(text(confirmed, "currency"), "EGP").toUpperCase());
        t.setMerchant(text(confirmed, "merchant"));
        t.setCategory(Categories.isValid(text(confirmed, "category")) ? text(confirmed, "category") : "other");
        String date = text(confirmed, "date");
        t.setDate(date == null ? today() : LocalDate.parse(date));
        String time = text(confirmed, "time");
        t.setTime(time == null ? null : LocalTime.parse(time));
        t.setPaymentMethod(orDefault(text(confirmed, "payment_method"), "unknown"));
        t.setNote(truncate(text(confirmed, "note"), 500));
        t.setTranscript(truncate(text(confirmed, "transcript"), 2000));
        t.setLanguage(text(confirmed, "language"));
        t.setExtractionMethod(text(confirmed, "extraction_method"));
        // Audio drafts spent time in speech-to-text; typed sentences did not.
        t.setSource(confirmed.path("timings_ms").path("asr").asDouble(0) > 0 ? "voice" : "text");
        List<String> edited = new ArrayList<>();
        confirmed.path("user_edited_fields").forEach(f -> edited.add(f.asString()));
        t.setEditedFields(edited);
        JsonNode pythonId = confirmed.path("id");
        t.setVoiceRecordId(pythonId.isNumber() ? pythonId.longValue() : null);
        return repository.save(t);
    }

    /** Add a transaction without voice (the form only). */
    public Transaction create(TransactionRequest request) {
        Transaction t = new Transaction();
        t.setUserId(currentUser.id());
        t.setSource("manual");
        apply(t, request, today());
        return repository.save(t);
    }

    /** Replace the editable fields of a saved transaction. */
    public Transaction update(Long id, TransactionRequest request) {
        Transaction t = get(id);
        apply(t, request, t.getDate());   // no date sent = keep the saved date
        return repository.saveAndFlush(t);
    }

    public void delete(Long id) {
        repository.delete(get(id));
    }

    @Transactional(readOnly = true)
    public Transaction get(Long id) {
        return repository.findById(id)
                .filter(t -> Objects.equals(currentUser.id(), null) || Objects.equals(currentUser.id(), t.getUserId()))
                .orElseThrow(() -> ApiException.notFound("Transaction " + id + " not found"));
    }

    /** Newest first. Every filter is optional. */
    @Transactional(readOnly = true)
    public List<Transaction> list(LocalDate from, LocalDate to, String category, String type, int limit) {
        if (limit < 1 || limit > MAX_LIMIT) {
            throw new ApiException(org.springframework.http.HttpStatus.UNPROCESSABLE_CONTENT, "invalid_limit",
                    "limit must be between 1 and " + MAX_LIMIT);
        }
        Sort newestFirst = Sort.by(Sort.Order.desc("date"), Sort.Order.desc("time"), Sort.Order.desc("id"));
        return repository.findAll(filter(from, to, category, type), PageRequest.of(0, limit, newestFirst)).getContent();
    }

    @Transactional(readOnly = true)
    public MonthlySummary summary(YearMonth month) {
        if (month == null) {
            month = YearMonth.now(zone);
        }
        List<Transaction> all = repository.findAll(filter(month.atDay(1), month.atEndOfMonth(), null, null));
        Map<String, List<Transaction>> byCurrency = new TreeMap<>();
        for (Transaction t : all) {
            byCurrency.computeIfAbsent(t.getCurrency(), c -> new ArrayList<>()).add(t);
        }
        List<MonthlySummary.CurrencyTotals> currencies = new ArrayList<>();
        byCurrency.forEach((currency, items) -> {
            BigDecimal expense = BigDecimal.ZERO.setScale(2);
            BigDecimal income = BigDecimal.ZERO.setScale(2);
            Map<String, BigDecimal> catTotal = new TreeMap<>();
            Map<String, Long> catCount = new TreeMap<>();
            for (Transaction t : items) {
                if ("income".equals(t.getTransactionType())) {
                    income = income.add(t.getAmount());
                } else {
                    expense = expense.add(t.getAmount());
                    catTotal.merge(t.getCategory(), t.getAmount(), BigDecimal::add);
                    catCount.merge(t.getCategory(), 1L, Long::sum);
                }
            }
            List<MonthlySummary.CategoryTotal> categories = new ArrayList<>();
            catTotal.forEach((cat, total) -> categories.add(new MonthlySummary.CategoryTotal(cat, total, catCount.get(cat))));
            categories.sort(Comparator.comparing(MonthlySummary.CategoryTotal::total).reversed());
            currencies.add(new MonthlySummary.CurrencyTotals(currency, expense, income, income.subtract(expense),
                    items.size(), categories));
        });
        return new MonthlySummary(month.toString(), currencies);
    }

    // ------------------------------------------------------------------

    private void apply(Transaction t, TransactionRequest r, LocalDate dateIfMissing) {
        String type = orDefault(r.transactionType(), "expense");
        String category = r.category() == null || r.category().isBlank()
                ? ("income".equals(type) ? "income" : "other")
                : r.category();
        if (!Categories.isValid(category)) {
            throw ApiException.invalidField("category: '" + category + "' is not one of " + Categories.ALL);
        }
        t.setTransactionType(type);
        t.setAmount(money(r.amount()));
        t.setCurrency(orDefault(r.currency(), "EGP").toUpperCase());
        t.setMerchant(blankToNull(r.merchant()));
        t.setCategory(category);
        t.setDate(r.date() == null ? dateIfMissing : r.date());
        t.setTime(r.time());
        t.setPaymentMethod(orDefault(r.paymentMethod(), "unknown"));
        t.setNote(blankToNull(r.note()));
    }

    private Specification<Transaction> filter(LocalDate from, LocalDate to, String category, String type) {
        String userId = currentUser.id();
        return (root, query, cb) -> {
            List<Predicate> where = new ArrayList<>();
            if (userId != null) where.add(cb.equal(root.get("userId"), userId));
            if (from != null) where.add(cb.greaterThanOrEqualTo(root.get("date"), from));
            if (to != null) where.add(cb.lessThanOrEqualTo(root.get("date"), to));
            if (category != null && !category.isBlank()) where.add(cb.equal(root.get("category"), category));
            if (type != null && !type.isBlank()) where.add(cb.equal(root.get("transactionType"), type));
            return cb.and(where.toArray(new Predicate[0]));
        };
    }

    private LocalDate today() {
        return LocalDate.now(zone);
    }

    private static BigDecimal money(BigDecimal value) {
        return value.abs().setScale(2, RoundingMode.HALF_UP);
    }

    private static String text(JsonNode node, String field) {
        JsonNode v = node.path(field);
        if (v.isMissingNode() || v.isNull()) return null;
        String s = v.asString();
        return s.isBlank() ? null : s;
    }

    private static String orDefault(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    private static String blankToNull(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }

    private static String truncate(String value, int max) {
        return value == null || value.length() <= max ? value : value.substring(0, max);
    }
}
