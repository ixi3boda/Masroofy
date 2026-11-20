package com.masroofy.backend.dto.request;

import com.masroofy.backend.util.EmailUtils;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record LoginRequest(
        @NotBlank(message = "Enter your email")
        @Email(regexp = EmailUtils.VALID_EMAIL_REGEX, message = "Enter a valid email address")
        @Size(max = 254, message = "Email must be at most 254 characters")
        String email,

        @NotBlank(message = "Enter your password")
        @Size(max = 128, message = "Password must be at most 128 characters")
        String password) {

    public LoginRequest {
        email = EmailUtils.trim(email);
    }


    @Override
    public String toString() {
        return "LoginRequest[email=" + email + ", password=***]";
    }
}
