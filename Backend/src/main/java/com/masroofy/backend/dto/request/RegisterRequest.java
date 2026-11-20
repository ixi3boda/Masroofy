package com.masroofy.backend.dto.request;

import jakarta.validation.constraints.AssertTrue;
import com.masroofy.backend.util.EmailUtils;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

/** Screen 01-02 "Create an account". */
public record RegisterRequest(
        @NotBlank(message = "Enter your name")
        @Size(max = 100, message = "Name must be at most 100 characters")
        String fullName,

        @NotBlank(message = "Enter your email")
        @Email(regexp = EmailUtils.VALID_EMAIL_REGEX, message = "Enter a valid email address")
        @Size(max = 254, message = "Email must be at most 254 characters")
        String email,

        @NotBlank(message = "Create a password")
        @Size(max = 128, message = "Password must be at most 128 characters")
        String password,

        @NotNull(message = "You must agree to the Terms & Privacy Policy")
        @AssertTrue(message = "You must agree to the Terms & Privacy Policy")
        Boolean acceptedTerms) {

    public RegisterRequest {
        email = EmailUtils.trim(email);
        fullName = EmailUtils.trim(fullName);
    }


    @Override
    public String toString() {
        return "RegisterRequest[fullName=" + fullName + ", email=" + email + ", password=***]";
    }
}
