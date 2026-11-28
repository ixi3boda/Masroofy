package com.masroofy.backend.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;

import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.repository.CategoryRepository;
import java.util.UUID;
import org.junit.jupiter.api.Test;

class CategoryServiceTest {

    private final CategoryRepository repository = mock(CategoryRepository.class);
    private final CategoryService service = new CategoryService(repository);
    private final UUID userId = UUID.randomUUID();

    @Test
    void kindIsCaseInsensitive() {
        service.listCategories(userId, " Income ");

        verify(repository).findVisible(userId, "income");
    }

    @Test
    void blankKindMeansBoth() {
        service.listCategories(userId, "");

        verify(repository).findVisible(userId, null);
    }

    @Test
    void unknownKindIsRefused() {
        assertThatThrownBy(() -> service.listCategories(userId, "transfer"))
                .isInstanceOfSatisfying(ApiException.class, e -> {
                    assertThat(e.getErrorCode()).isEqualTo(ErrorCode.VALIDATION_FAILED);
                    assertThat(e.getFieldErrors().get(0).field()).isEqualTo("kind");
                });
        verifyNoInteractions(repository);
    }
}
