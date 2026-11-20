package com.financeapp.sms.repo;

import com.financeapp.sms.domain.Transaction;
import com.financeapp.sms.domain.TxStatus;
import jakarta.persistence.LockModeType;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface TransactionRepository extends JpaRepository<Transaction, Long> {

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select t from Transaction t where t.id = :id and t.userId = :userId")
    Optional<Transaction> lockByIdAndUserId(@Param("id") Long id, @Param("userId") Long userId);

    List<Transaction> findByUserIdAndStatusOrderByOccurredAtDesc(Long userId, TxStatus status);

    /** Same user and amount, not rejected, inside a time window: candidates for duplicates and own-account transfers. */
    @Query("select t from Transaction t where t.userId = :userId and t.amount = :amount and t.status <> :rejected "
            + "and t.occurredAt between :from and :to order by t.occurredAt")
    List<Transaction> findNear(@Param("userId") Long userId, @Param("amount") BigDecimal amount,
                               @Param("rejected") TxStatus rejected, @Param("from") Instant from, @Param("to") Instant to);
}
