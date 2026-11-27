package com.masroofy.backend.dto.request;

import com.masroofy.backend.util.EmailUtils;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

public record VerifyCodeRequest(
        @NotBlank(message = "Enter your email")
        @Email(regexp = EmailUtils.VALID_EMAIL_REGEX, message = "Enter a valid email address")
        @Size(max = 254, message = "Email must be at most 254 characters")
        String email,

        @NotBlank(message = "Enter the code")
        @Pattern(regexp = "^\\d{4,10}$", message = "Enter the code we sent to your email")
        String code) {

    public VerifyCodeRequest {
        email = EmailUtils.trim(email);
        code = EmailUtils.trim(code);
    }

}
