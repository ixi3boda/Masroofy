package com.masroofy.backend.dto.response;

import com.masroofy.backend.model.Category;
import io.swagger.v3.oas.annotations.media.Schema;
import java.util.UUID;

/** A category the user can pick. */
public record CategoryResponse(
        UUID id,
        @Schema(example = "groceries", description = "The app's category key; the app maps it to an icon") String key,
        @Schema(example = "Groceries") String name,
        @Schema(example = "expense", allowableValues = {"expense", "income"}) String kind) {

    public static CategoryResponse from(Category category) {
        return new CategoryResponse(category.id(), category.key(), category.name(), category.kind());
    }
}
