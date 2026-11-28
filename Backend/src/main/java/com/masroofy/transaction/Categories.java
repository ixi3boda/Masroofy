package com.masroofy.transaction;

import java.util.List;
import java.util.Set;

/**
 * The category ids the app uses. Keep in sync with voice-service/voice_expense/data/categories.json
 * (the voice service only ever returns these ids).
 */
public final class Categories {

    public static final List<String> ALL = List.of(
            "food_dining", "groceries", "transport", "fuel", "shopping", "electronics", "bills_utilities",
            "mobile_internet", "health", "education", "entertainment", "subscriptions", "housing",
            "personal_care", "gifts_donations", "travel", "income", "other");

    public static final Set<String> TRANSACTION_TYPES = Set.of("expense", "income");
    public static final Set<String> PAYMENT_METHODS = Set.of("cash", "card", "wallet", "unknown");

    private static final Set<String> ALL_SET = Set.copyOf(ALL);

    private Categories() {
    }

    public static boolean isValid(String category) {
        return category != null && ALL_SET.contains(category);
    }
}
