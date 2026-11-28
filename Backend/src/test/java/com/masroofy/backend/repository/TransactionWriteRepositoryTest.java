package com.masroofy.backend.repository;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.masroofy.backend.model.Account;
import com.masroofy.backend.model.Category;
import com.masroofy.backend.model.NewTransaction;
import com.masroofy.backend.repository.TransactionRepository.TransactionRow;
import com.masroofy.backend.support.LedgerFixtures;
import com.masroofy.backend.support.PostgresTestSupport;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.jdbc.JdbcTest;
import org.springframework.context.annotation.Import;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.JdbcTemplate;

/** Accounts, categories, transactions and the audit log on real PostgreSQL with migrations V1-V5. */
@JdbcTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Import({AccountRepository.class, CategoryRepository.class, TransactionRepository.class, AuditLogRepository.class})
class TransactionWriteRepositoryTest extends PostgresTestSupport {

    private static final Instant NOW = Instant.parse("2026-11-20T10:00:00Z");
    private static final Instant CREATED = Instant.parse("2026-09-01T00:00:00Z");

    @Autowired
    private AccountRepository accounts;
    @Autowired
    private CategoryRepository categories;
    @Autowired
    private TransactionRepository transactions;
    @Autowired
    private AuditLogRepository auditLog;
    @Autowired
    private JdbcTemplate jdbc;

    private LedgerFixtures fx;
    private UUID user;
    private UUID cib;

    @BeforeEach
    void setUp() {
        fx = new LedgerFixtures(jdbc);
        user = fx.user("write-" + UUID.randomUUID() + "@example.com");
        cib = fx.account(user, "CIB Account", "bank", "EGP", "5000.00", CREATED);
    }

    private NewTransaction expense(UUID clientRequestId, UUID categoryId) {
        return new NewTransaction(UUID.randomUUID(), user, cib, categoryId, "expense", new BigDecimal("850.00"),
                "EGP", BigDecimal.ONE, NOW, "Carrefour", "Weekly groceries", "a".repeat(64), clientRequestId, NOW);
    }

    // ---- Accounts --------------------------------------------------------------------------------------------------

    @Test
    void defaultCashIsCreatedOnceInTheUsersBaseCurrency() {
        assertThat(accounts.insertDefaultCash(UUID.randomUUID(), user, NOW)).isTrue();
        assertThat(accounts.insertDefaultCash(UUID.randomUUID(), user, NOW)).isFalse();

        List<Account> open = accounts.findOpenByUser(user);
        assertThat(open).extracting(Account::name).containsExactly("CIB Account", "Cash");
        assertThat(open.get(1).currency()).isEqualTo("EGP");
        assertThat(open.get(1).type()).isEqualTo("cash");
    }

    @Test
    void findOpenIgnoresArchivedAndOtherUsersAccounts() {
        UUID other = fx.user("other-" + UUID.randomUUID() + "@example.com");
        UUID otherAccount = fx.account(other, "Theirs", "cash", "EGP", "0", CREATED);
        UUID archived = fx.account(user, "Old card", "card", "EGP", "0", CREATED);
        jdbc.update("UPDATE accounts SET is_archived = TRUE WHERE id = ?", archived);

        assertThat(accounts.findOpen(user, cib)).isPresent();
        assertThat(accounts.findOpen(user, otherAccount)).isEmpty();
        assertThat(accounts.findOpen(user, archived)).isEmpty();
        assertThat(accounts.findOpenByUser(user)).extracting(Account::id).containsExactly(cib);
    }

    // ---- Categories ------------------------------------------------------------------------------------------------

    @Test
    void systemCategoriesComeInTheAppsOrder() {
        assertThat(categories.findVisible(user, "expense")).extracting(Category::key)
                .containsExactly("groceries", "transport", "bills", "rent", "dining", "health", "shopping", "other");
        assertThat(categories.findVisible(user, "income")).extracting(Category::key)
                .containsExactly("salary", "freelance", "investment", "gift", "refund", "otherIncome");
        assertThat(categories.findVisible(user, null)).hasSize(14);
    }

    @Test
    void categoriesByKeyAndIdSeeOnlySystemAndOwnVisibleOnes() {
        UUID other = fx.user("cat-" + UUID.randomUUID() + "@example.com");
        UUID theirs = UUID.randomUUID();
        jdbc.update("""
                INSERT INTO categories (id, user_id, name, kind, icon, is_hidden, created_at, updated_at)
                VALUES (?, ?, 'Pets', 'expense', 'pets', FALSE, now(), now())""", theirs, other);

        assertThat(categories.findVisibleByKey(user, "groceries")).map(Category::id).contains(LedgerFixtures.GROCERIES);
        assertThat(categories.findVisibleByKey(user, "pets")).isEmpty();
        assertThat(categories.findVisibleById(user, theirs)).isEmpty();
        assertThat(categories.findVisibleById(other, theirs)).isPresent();
    }

    // ---- Transactions ----------------------------------------------------------------------------------------------

    @Test
    void insertsAndReadsBackWithAccountAndCategoryNames() {
        NewTransaction tx = expense(UUID.randomUUID(), LedgerFixtures.GROCERIES);

        transactions.insert(tx);

        TransactionRow row = transactions.findVisible(user, tx.id()).orElseThrow();
        assertThat(row.type()).isEqualTo("expense");
        assertThat(row.amount()).isEqualByComparingTo("850.00");
        assertThat(row.occurredAt()).isEqualTo(NOW);
        assertThat(row.source()).isEqualTo("manual");
        assertThat(row.status()).isEqualTo("confirmed");
        assertThat(row.categoryKey()).isEqualTo("groceries");
        assertThat(row.accountName()).isEqualTo("CIB Account");
        assertThat(transactions.findByClientRequestId(user, tx.clientRequestId())).map(TransactionRow::id)
                .contains(tx.id());
    }

    @Test
    void anotherUserOrADeletedRowIsNotVisible() {
        NewTransaction tx = expense(UUID.randomUUID(), LedgerFixtures.GROCERIES);
        transactions.insert(tx);
        UUID other = fx.user("peek-" + UUID.randomUUID() + "@example.com");

        assertThat(transactions.findVisible(other, tx.id())).isEmpty();
        jdbc.update("UPDATE transactions SET is_deleted = TRUE WHERE id = ?", tx.id());
        assertThat(transactions.findVisible(user, tx.id())).isEmpty();
    }

    @Test
    void aClientRequestIdIsUniquePerUserOnly() {
        UUID requestId = UUID.randomUUID();
        transactions.insert(expense(requestId, LedgerFixtures.GROCERIES));

        // Another user may use the same id.
        UUID other = fx.user("same-id-" + UUID.randomUUID() + "@example.com");
        UUID otherAccount = fx.account(other, "Cash", "cash", "EGP", "0", CREATED);
        transactions.insert(new NewTransaction(UUID.randomUUID(), other, otherAccount, LedgerFixtures.GROCERIES,
                "expense", BigDecimal.TEN, "EGP", BigDecimal.ONE, NOW, "Kiosk", null, "b".repeat(64), requestId, NOW));

        // The same user may not (last: a violation ends the test's database transaction).
        assertThatThrownBy(() -> transactions.insert(expense(requestId, LedgerFixtures.GROCERIES)))
                .isInstanceOf(DuplicateKeyException.class);
    }

    @Test
    void theDatabaseRefusesACategoryOfTheWrongKind() {
        assertThatThrownBy(() -> transactions.insert(expense(UUID.randomUUID(), LedgerFixtures.SALARY)))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    // ---- Audit log -------------------------------------------------------------------------------------------------

    @Test
    void auditRowsKeepTheJson() {
        UUID entityId = UUID.randomUUID();

        auditLog.insert(UUID.randomUUID(), user, "transaction", entityId, "create", null,
                "{\"amount\":\"850.00\",\"type\":\"expense\"}", NOW);

        assertThat(jdbc.queryForObject("SELECT after ->> 'amount' FROM audit_log WHERE entity_id = ?", String.class,
                entityId)).isEqualTo("850.00");
    }

    @Test
    void aCreateAuditRowHasNoBefore() {
        assertThatThrownBy(() -> auditLog.insert(UUID.randomUUID(), user, "transaction", UUID.randomUUID(), "create",
                "{}", "{}", NOW)).isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    void aCreateAuditRowNeedsAfter() {
        assertThatThrownBy(() -> auditLog.insert(UUID.randomUUID(), user, "transaction", UUID.randomUUID(), "create",
                null, null, NOW)).isInstanceOf(DataIntegrityViolationException.class);
    }
}
