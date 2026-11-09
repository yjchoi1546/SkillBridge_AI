package com.skillbridge;

import static com.skillbridge.ApiModels.*;
import static org.assertj.core.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest(properties={"skillbridge.demo-enabled=false", "skillbridge.demo-delay-ms=20", "skillbridge.ai.mode=demo"})
@AutoConfigureMockMvc
class AuthApiTest {
    @Autowired MockMvc mvc;
    @Autowired ObjectMapper mapper;
    @Autowired JdbcTemplate jdbc;
    private final String password = "real-password-2026";

    private String email() { return UUID.randomUUID()+"@example.test"; }
    private JsonNode postJson(String path, Object input, String token, int expected) throws Exception {
        var request = post(path).contentType(MediaType.APPLICATION_JSON).content(mapper.writeValueAsBytes(input));
        if (token != null) request.header("Authorization", "Bearer "+token);
        byte[] body = mvc.perform(request).andExpect(status().is(expected)).andReturn().getResponse().getContentAsByteArray();
        return body.length == 0 ? mapper.createObjectNode() : mapper.readTree(body);
    }
    private JsonNode register(String email, String role) throws Exception { return postJson("/api/auth/register", Map.of("email", email, "password", password, "name", role.equals("COMPANY") ? "실제 기업" : "실제 개인", "role", role), null, 201); }

    @Test void registrationHashesPasswordsAndLoginPersistsOnlyTokenHash() throws Exception {
        String email = email();
        JsonNode registered = register(email.toUpperCase(java.util.Locale.ROOT), "PERSON");
        String token = registered.path("token").asText();
        assertThat(token).hasSize(43);
        assertThat(registered.path("role").asText()).isEqualTo("PERSON");
        String storedPassword = jdbc.queryForObject("SELECT password_hash FROM accounts WHERE email=?", String.class, email);
        assertThat(storedPassword).isNotEqualTo(password).startsWith("$2");
        assertThat(new BCryptPasswordEncoder().matches(password, storedPassword)).isTrue();
        String storedToken = jdbc.queryForObject("SELECT token_hash FROM auth_sessions s JOIN accounts a ON a.user_id=s.user_id WHERE a.email=?", String.class, email);
        assertThat(storedToken).hasSize(64).doesNotContain(token);
        mvc.perform(get("/api/auth/me").header("Authorization", "Bearer "+token)).andExpect(status().isOk()).andExpect(jsonPath("name").value("실제 개인"));
        JsonNode loggedIn = postJson("/api/auth/login", Map.of("email", email, "password", password), null, 200);
        assertThat(loggedIn.path("token").asText()).isNotEqualTo(token);
        postJson("/api/auth/register", Map.of("email", email, "password", password, "name", "중복 계정", "role", "COMPANY"), null, 409);

        // Construct a new service instance over the same database to simulate losing all process memory.
        DemoAuth restarted = new DemoAuth(jdbc, false);
        Actor actor = restarted.require("Bearer "+token, Role.PERSON);
        assertThat(actor.name()).isEqualTo("실제 개인");
        postJson("/api/auth/logout", Map.of(), token, 204);
        mvc.perform(get("/api/auth/me").header("Authorization", "Bearer "+token)).andExpect(status().isUnauthorized());
        assertThatThrownBy(() -> restarted.require("Bearer "+token, null)).hasMessageContaining("401");
        mvc.perform(get("/api/auth/me").header("Authorization", "Bearer "+loggedIn.path("token").asText())).andExpect(status().isOk());
    }

    @Test void realCompaniesAndPeopleCannotReadEachOthersPrivateRecords() throws Exception {
        String companyOne = register(email(), "COMPANY").path("token").asText();
        String companyTwo = register(email(), "COMPANY").path("token").asText();
        String personOne = register(email(), "PERSON").path("token").asText();
        String personTwo = register(email(), "PERSON").path("token").asText();
        JsonNode created = postJson("/api/company/requests", Map.of("requestText", "사내 월별 매출 보고서에 포함된 고객사 비공개 정보를 정리하고 집계를 자동화하고 싶습니다.", "jobRole", "데이터 분석", "sensitiveWords", "고객사", "generalization", "high", "attachments", List.of()), companyOne, 202);
        String id = created.path("id").asText();
        mvc.perform(get("/api/company/projects/"+id).header("Authorization", "Bearer "+companyOne)).andExpect(status().isOk());
        mvc.perform(get("/api/company/projects/"+id).header("Authorization", "Bearer "+companyTwo)).andExpect(status().isNotFound());
        mvc.perform(get("/api/company/projects/"+id).header("Authorization", "Bearer "+personOne)).andExpect(status().isForbidden());
        JsonNode application = postJson("/api/applications", Map.of("projectId", "sales-report", "difficulty", "beginner"), personOne, 201);
        String applicationId = application.path("id").asText();
        mvc.perform(get("/api/applications/"+applicationId).header("Authorization", "Bearer "+personOne)).andExpect(status().isOk());
        mvc.perform(get("/api/applications/"+applicationId).header("Authorization", "Bearer "+personTwo)).andExpect(status().isNotFound());
        postJson("/api/company/projects/"+id+"/publish", Map.of(), personOne, 403);
    }

    @Test void invalidCredentialsLengthExpiryAndDemoAccessAreRejected() throws Exception {
        String email = email();
        String token = register(email, "PERSON").path("token").asText();
        JsonNode wrong = postJson("/api/auth/login", Map.of("email", email, "password", "incorrect-password"), null, 401);
        JsonNode missing = postJson("/api/auth/login", Map.of("email", email(), "password", "incorrect-password"), null, 401);
        assertThat(wrong.path("message").asText()).isEqualTo(missing.path("message").asText());
        postJson("/api/auth/register", Map.of("email", email(), "password", "short", "name", "검증 계정", "role", "PERSON"), null, 400);
        postJson("/api/auth/register", Map.of("email", email(), "password", "가".repeat(25), "name", "검증 계정", "role", "PERSON"), null, 400);
        postJson("/api/auth/demo", Map.of("role", "COMPANY"), null, 503);
        mvc.perform(get("/api/auth/me")).andExpect(status().isUnauthorized());
        jdbc.update("UPDATE auth_sessions SET expires_at=? WHERE user_id=(SELECT user_id FROM accounts WHERE email=?)", java.sql.Timestamp.from(java.time.Instant.now().minusSeconds(1)), email);
        mvc.perform(get("/api/auth/me").header("Authorization", "Bearer "+token)).andExpect(status().isUnauthorized());
        String attemptEmail = email();
        for (int i=0; i<10; i++) postJson("/api/auth/login", Map.of("email", attemptEmail, "password", "incorrect-password"), null, 401);
        postJson("/api/auth/login", Map.of("email", attemptEmail, "password", "incorrect-password"), null, 429);
    }
}
