package com.masroofy.backend.service;

import java.time.Duration;

/** Sends the transactional auth emails. Implementations throw EMAIL_DELIVERY_FAILED on failure. */
public interface EmailService {

    void sendVerificationCode(String to, String fullName, String code, Duration validFor);

    void sendPasswordResetCode(String to, String fullName, String code, Duration validFor);
}
