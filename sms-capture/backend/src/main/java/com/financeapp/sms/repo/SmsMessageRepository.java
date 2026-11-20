package com.financeapp.sms.repo;

import com.financeapp.sms.domain.SmsMessage;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SmsMessageRepository extends JpaRepository<SmsMessage, Long> {
    boolean existsByUserIdAndBodyHash(Long userId, String bodyHash);
}
