package com.masroofy.backend.controller;

import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.masroofy.backend.dto.response.AccountResponse;
import com.masroofy.backend.dto.response.CategoryResponse;
import com.masroofy.backend.firebase.FirebaseIdentityClient;
import com.masroofy.backend.firebase.VerifiedToken;
import com.masroofy.backend.model.User;
import com.masroofy.backend.repository.UserRepository;
import com.masroofy.backend.service.AccountService;
import com.masroofy.backend.service.CategoryService;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest({AccountController.class, CategoryController.class})
@Import(WebLayerTestConfig.class)
class AccountAndCategoryControllerTest {

    private static final UUID USER_ID = UUID.fromString("22222222-2222-2222-2222-222222222222");
    private static final Instant NOW = Instant.parse("2026-11-20T10:00:00Z");

    @Autowired
    private MockMvc mvc;

    @MockitoBean
    private AccountService accountService;
    @MockitoBean
    private CategoryService categoryService;
    @MockitoBean
    private FirebaseIdentityClient firebase;
    @MockitoBean
    private UserRepository userRepository;

    private void loggedIn() {
        when(firebase.verifyIdToken("good", true)).thenReturn(new VerifiedToken("uid-1", "mariam@example.com"));
        when(userRepository.findByFirebaseUid("uid-1")).thenReturn(Optional.of(new User(USER_ID, "uid-1",
                "mariam@example.com", null, "Mariam Ali", "EGP", "en", "Africa/Cairo", null, NOW, NOW, NOW, NOW)));
    }

    @Test
    void listsAccountsWithoutEmptyCardDigits() throws Exception {
        loggedIn();
        when(accountService.listAccounts(USER_ID)).thenReturn(List.of(
                new AccountResponse(UUID.randomUUID(), "Cash", "cash", "EGP", null),
                new AccountResponse(UUID.randomUUID(), "CIB Account", "bank", "EGP", "4821")));

        mvc.perform(get("/api/v1/accounts").header("Authorization", "Bearer good"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].name").value("Cash"))
                .andExpect(jsonPath("$[0].cardLast4").doesNotExist())
                .andExpect(jsonPath("$[1].cardLast4").value("4821"));
    }

    @Test
    void listsCategoriesOfAKind() throws Exception {
        loggedIn();
        when(categoryService.listCategories(USER_ID, "expense")).thenReturn(List.of(
                new CategoryResponse(UUID.randomUUID(), "groceries", "Groceries", "expense")));

        mvc.perform(get("/api/v1/categories?kind=expense").header("Authorization", "Bearer good"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].key").value("groceries"))
                .andExpect(jsonPath("$[0].kind").value("expense"));
    }

    @Test
    void kindIsOptional() throws Exception {
        loggedIn();
        when(categoryService.listCategories(eq(USER_ID), isNull())).thenReturn(List.of());

        mvc.perform(get("/api/v1/categories").header("Authorization", "Bearer good"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$").isEmpty());
    }

    @Test
    void bothNeedAToken() throws Exception {
        mvc.perform(get("/api/v1/accounts")).andExpect(status().isUnauthorized());
        mvc.perform(get("/api/v1/categories")).andExpect(status().isUnauthorized());
    }
}
