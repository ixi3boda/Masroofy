package com.masroofy.backend.controller;

import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.masroofy.backend.dto.response.UserResponse;
import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.firebase.FirebaseIdentityClient;
import com.masroofy.backend.firebase.VerifiedToken;
import com.masroofy.backend.model.User;
import com.masroofy.backend.repository.UserRepository;
import com.masroofy.backend.service.UserService;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

/** Exercises the Firebase token filter and access rules through a protected endpoint. */
@WebMvcTest(UserController.class)
@Import(WebLayerTestConfig.class)
class UserControllerTest {

    private static final Instant NOW = Instant.parse("2026-11-19T10:00:00Z");
    private static final UUID USER_ID = UUID.fromString("22222222-2222-2222-2222-222222222222");

    @Autowired
    private MockMvc mvc;

    @MockitoBean
    private UserService userService;
    @MockitoBean
    private FirebaseIdentityClient firebase;
    @MockitoBean
    private UserRepository userRepository;

    private static User user(boolean verified) {
        return new User(USER_ID, "uid-1", "mariam@example.com", null, "Mariam Ali", "EGP", "en", "Africa/Cairo",
                null, verified ? NOW : null, NOW, NOW, NOW);
    }

    @Test
    void returnsProfileForVerifiedUser() throws Exception {
        when(firebase.verifyIdToken("good", true)).thenReturn(new VerifiedToken("uid-1", "mariam@example.com"));
        when(userRepository.findByFirebaseUid("uid-1")).thenReturn(Optional.of(user(true)));
        when(userService.getUser(USER_ID)).thenReturn(UserResponse.from(user(true)));

        mvc.perform(get("/api/v1/users/me").header("Authorization", "Bearer good"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.id").value(USER_ID.toString()))
                .andExpect(jsonPath("$.fullName").value("Mariam Ali"))
                .andExpect(jsonPath("$.timezone").value("Africa/Cairo"));
    }

    @Test
    void bearerSchemeIsCaseInsensitive() throws Exception {
        when(firebase.verifyIdToken("good", true)).thenReturn(new VerifiedToken("uid-1", "mariam@example.com"));
        when(userRepository.findByFirebaseUid("uid-1")).thenReturn(Optional.of(user(true)));
        when(userService.getUser(USER_ID)).thenReturn(UserResponse.from(user(true)));

        mvc.perform(get("/api/v1/users/me").header("Authorization", "bearer good"))
                .andExpect(status().isOk());
    }

    @Test
    void missingTokenIs401() throws Exception {
        mvc.perform(get("/api/v1/users/me"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHORIZED"))
                .andExpect(jsonPath("$.path").value("/api/v1/users/me"));
        verifyNoInteractions(userService);
    }

    @Test
    void nonBearerHeaderIs401() throws Exception {
        mvc.perform(get("/api/v1/users/me").header("Authorization", "Basic abc"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHORIZED"));
        verifyNoInteractions(firebase);
    }

    @Test
    void invalidTokenIs401() throws Exception {
        when(firebase.verifyIdToken("bad", true)).thenThrow(new ApiException(ErrorCode.UNAUTHORIZED, "expired"));

        mvc.perform(get("/api/v1/users/me").header("Authorization", "Bearer bad"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHORIZED"))
                .andExpect(jsonPath("$.message").value("expired"));
    }

    @Test
    void disabledAccountIs403() throws Exception {
        when(firebase.verifyIdToken("t", true)).thenThrow(new ApiException(ErrorCode.ACCOUNT_DISABLED));

        mvc.perform(get("/api/v1/users/me").header("Authorization", "Bearer t"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value("ACCOUNT_DISABLED"));
    }

    @Test
    void tokenWithoutDatabaseProfileIs401() throws Exception {
        when(firebase.verifyIdToken("good", true)).thenReturn(new VerifiedToken("uid-9", "x@example.com"));
        when(userRepository.findByFirebaseUid("uid-9")).thenReturn(Optional.empty());

        mvc.perform(get("/api/v1/users/me").header("Authorization", "Bearer good"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void unverifiedUserIsBlockedWithEmailNotVerified() throws Exception {
        when(firebase.verifyIdToken("good", true)).thenReturn(new VerifiedToken("uid-1", "mariam@example.com"));
        when(userRepository.findByFirebaseUid("uid-1")).thenReturn(Optional.of(user(false)));

        mvc.perform(get("/api/v1/users/me").header("Authorization", "Bearer good"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value("EMAIL_NOT_VERIFIED"));
        verifyNoInteractions(userService);
    }
}
