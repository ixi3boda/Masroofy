package com.masroofy.backend.dto.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record ResetPasswordRequest(
        @NotBlank(message = "The reset session is missing")
        @Size(max = 256, message = "The reset session is invalid")
        String resetToken,

        @NotBlank(message = "Enter a new password")
        @Size(max = 128, message = "Password must be at most 128 characters")
        String newPassword,

        @NotBlank(message = "Re-enter your new password")
        @Size(max = 128, message = "Password must be at most 128 characters")
        String confirmPassword) {

    @Override
    public String toString() {
        return "ResetPasswordRequest[resetToken=***, newPassword=***, confirmPassword=***]";
    }
}
