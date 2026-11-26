package com.masroofy.backend.repository;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.masroofy.backend.support.LedgerFixtures;
import com.masroofy.backend.support.PostgresTestSupport;
import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.jdbc.JdbcTest;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * The database itself refuses inconsistent ledger data. Runs without a test transaction because the transfer check
 * is deferred to COMMIT; every row is removed afterwards.
 */
@JdbcTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Transactional(propagation = Propagation.NOT_SUPPORTED)
class LedgerConstraintsTest extends PostgresTestSupport {

    private static final Instant AT = Instant.parse("2026-11-10T10:00:00Z");

    @Autowired
    private JdbcTemplate jdbc;
    @Autowired
    private PlatformTransactionManager transactionManager;

    private LedgerFixtures fx;
    private UUID user;
    private UUID cib;
    private UUID cash;

    @BeforeEach
    void setUp() {
        fx = new LedgerFixtures(jdbc);
        user = fx.user("ledger-" + UUID.randomUUID() + "@example.com");
        cib = fx.account(user, "CIB", "bank", "EGP", "0", AT);
        cash = fx.account(user, "Cash", "cash", "EGP", "0", AT);
    }

    @AfterEach
    void cleanUp() {
        jdbc.update("DELETE FROM users WHERE email LIKE 'ledger-%' OR email LIKE 'intruder-%'");
    }

    @Test
    void amountMustBePositive() {
        assertThatThrownBy(() -> fx.expense(user, cib, "-5.00", AT, "Negative"))
                .isInstanceOf(DataIntegrityViolationException.class).hasMessageContaining("ck_transactions_amount");
        assertThatThrownBy(() -> fx.expense(user, cib, "0.00", AT, "Zero"))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    void categoryKindMustMatchTheType() {
        assertThatThrownBy(() -> fx.tx(user, cib, LedgerFixtures.GROCERIES, "income", "10", "EGP", "1", AT, "x",
                "confirmed", false))
                .isInstanceOf(DataIntegrityViolationException.class)
                .hasMessageContaining("does not match category kind");
    }

    @Test
    void incomeAndExpenseNeedACategoryAndTransfersMustNotHaveOne() {
        assertThatThrownBy(() -> fx.tx(user, cib, null, "expense", "10", "EGP", "1", AT, "x", "confirmed", false))
                .isInstanceOf(DataIntegrityViolationException.class);
    }

    @Test
    void anotherUsersAccountIsRejected() {
        UUID intruder = fx.user("intruder-" + UUID.randomUUID() + "@example.com");

        assertThatThrownBy(() -> fx.expense(intruder, cib, "10.00", AT, "Not my account"))
                .isInstanceOf(DataIntegrityViolationException.class).hasMessageContaining("fk_transactions_account");
    }

    @Test
    void transactionCurrencyMustBeTheAccountCurrency() {
        assertThatThrownBy(() -> fx.tx(user, cib, LedgerFixtures.GROCERIES, "expense", "10", "USD", "48", AT, "x",
                "confirmed", false))
                .isInstanceOf(DataIntegrityViolationException.class).hasMessageContaining("fk_transactions_account");
    }

    @Test
    void aTransferNeedsBothLegsAtCommit() {
        TransactionTemplate tx = new TransactionTemplate(transactionManager);
        UUID transferId = UUID.randomUUID();

        assertThatThrownBy(() -> tx.executeWithoutResult(status -> {
            jdbc.update("INSERT INTO transfers (id, user_id, occurred_at, created_at, updated_at) "
                    + "VALUES (?, ?, ?, now(), now())", transferId, user, java.sql.Timestamp.from(AT));
            jdbc.update("""
                    INSERT INTO transactions (id, user_id, account_id, transfer_id, type, amount, currency,
                                              occurred_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?, 'transfer_out', 50, 'EGP', ?, now(), now())""",
                    UUID.randomUUID(), user, cib, transferId, java.sql.Timestamp.from(AT));
        })).hasMessageContaining("must have one transfer_out and one transfer_in");

        assertThat(jdbc.queryForObject("SELECT count(*) FROM transfers WHERE id = ?", Integer.class, transferId))
                .isZero();
    }

    @Test
    void aCompleteTransferCommits() {
        UUID transferId = new TransactionTemplate(transactionManager)
                .execute(status -> fx.transfer(user, cib, cash, "50.00", "EGP", AT));

        assertThat(jdbc.queryForObject("SELECT count(*) FROM transactions WHERE transfer_id = ?", Integer.class,
                transferId)).isEqualTo(2);
    }

    @Test
    void oneOverallBudgetPerMonthAndMonthlyBudgetsStartOnThe1st() {
        fx.overallMonthlyBudget(user, "18000", LocalDate.of(2026, 11, 1), false);

        assertThatThrownBy(() -> fx.overallMonthlyBudget(user, "9000", LocalDate.of(2026, 11, 1), false))
                .isInstanceOf(DuplicateKeyException.class);
        assertThatThrownBy(() -> fx.overallMonthlyBudget(user, "9000", LocalDate.of(2026, 12, 15), false))
                .isInstanceOf(DataIntegrityViolationException.class).hasMessageContaining("ck_budgets_monthly_start");
    }

    @Test
    void deletingAUserRemovesAllTheirLedgerData() {
        fx.expense(user, cib, "10.00", AT, "x");
        new TransactionTemplate(transactionManager).execute(status -> fx.transfer(user, cib, cash, "5", "EGP", AT));
        fx.overallMonthlyBudget(user, "100", LocalDate.of(2026, 11, 1), false);

        jdbc.update("DELETE FROM users WHERE id = ?", user);

        assertThat(jdbc.queryForObject("""
                SELECT (SELECT count(*) FROM transactions WHERE user_id = ?) + (SELECT count(*) FROM transfers
                WHERE user_id = ?) + (SELECT count(*) FROM accounts WHERE user_id = ?) + (SELECT count(*)
                FROM budgets WHERE user_id = ?)""", Integer.class, user, user, user, user)).isZero();
    }
}
