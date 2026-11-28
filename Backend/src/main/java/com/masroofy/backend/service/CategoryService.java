package com.masroofy.backend.service;

import com.masroofy.backend.dto.response.CategoryResponse;
import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.exception.FieldErrorDetail;
import com.masroofy.backend.repository.CategoryRepository;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.stereotype.Service;

@Service
public class CategoryService {

    private static final Set<String> KINDS = Set.of("expense", "income");

    private final CategoryRepository categoryRepository;

    public CategoryService(CategoryRepository categoryRepository) {
        this.categoryRepository = categoryRepository;
    }

    /** @param kind {@code expense}, {@code income} (any case), or null / blank for both */
    public List<CategoryResponse> listCategories(UUID userId, String kind) {
        String normalized = null;
        if (kind != null && !kind.isBlank()) {
            normalized = kind.trim().toLowerCase(Locale.ROOT);
            if (!KINDS.contains(normalized)) {
                throw new ApiException(ErrorCode.VALIDATION_FAILED, ErrorCode.VALIDATION_FAILED.defaultMessage(),
                        Map.of(), List.of(new FieldErrorDetail("kind", "Invalid", "Must be expense or income")), null);
            }
        }
        return categoryRepository.findVisible(userId, normalized).stream().map(CategoryResponse::from).toList();
    }
}
