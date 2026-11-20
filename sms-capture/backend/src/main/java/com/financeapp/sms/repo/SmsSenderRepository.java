package com.financeapp.sms.repo;

import com.financeapp.sms.domain.SmsSender;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SmsSenderRepository extends JpaRepository<SmsSender, Long> {
    List<SmsSender> findByUserId(Long userId);
    Optional<SmsSender> findByUserIdAndSenderId(Long userId, String senderId);
}
