package com.masroofy.backend.model;

import java.util.UUID;

/**
 * CATEGORY entity (entity doc v2, section 2). {@code key} is the {@code icon} column: the app's category key
 * (groceries, salary, ...). {@code userId} is null for a system default.
 */
public record Category(
        UUID id,
        UUID userId,
        String name,
        String kind,
        String key,
        boolean hidden) {
}
