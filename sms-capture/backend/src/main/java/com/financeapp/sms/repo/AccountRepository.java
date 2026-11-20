package com.financeapp.sms.repo;

import com.financeapp.sms.domain.Account;
import jakarta.persistence.LockModeType;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface AccountRepository extends JpaRepository<Account, Long> {

    @Query("select new com.financeapp.sms.repo.AccountKey(a.id, a.institution, a.last4, a.currency) from Account a where a.userId = :userId")
    List<AccountKey> findKeysByUserId(@Param("userId") Long userId);

    /** SELECT ... FOR UPDATE: serialises balance changes on one account. */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("select a from Account a where a.id = :id and a.userId = :userId")
    Optional<Account> lockByIdAndUserId(@Param("id") Long id, @Param("userId") Long userId);
}
