package com.skillbridge;

import static org.assertj.core.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfEnvironmentVariable;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

/** Opt in after setup-ai.ps1: real Java/Python transport, fake LLM, isolated test DB. */
@EnabledIfEnvironmentVariable(named = "SKILLBRIDGE_TEST_PYTHON", matches = "true")
@SpringBootTest(properties = {"skillbridge.ai.mode=python", "skillbridge.ai.provider=fake",
    "skillbridge.demo-enabled=false", "skillbridge.seed-demo-data=false"})
@AutoConfigureMockMvc
class PythonWorkflowTest {
    @Autowired MockMvc mvc;
    @Autowired ObjectMapper mapper;

    private JsonNode postJson(String path, String token, Object body, int expected) throws Exception {
        var request = post(path).contentType(MediaType.APPLICATION_JSON).content(mapper.writeValueAsBytes(body));
        if (token != null) request.header("Authorization", "Bearer " + token);
        byte[] response = mvc.perform(request).andExpect(status().is(expected)).andReturn().getResponse().getContentAsByteArray();
        return response.length == 0 ? mapper.createObjectNode() : mapper.readTree(response);
    }
    private JsonNode read(String path, String token) throws Exception {
        return mapper.readTree(mvc.perform(get(path).header("Authorization", "Bearer " + token))
            .andExpect(status().isOk()).andReturn().getResponse().getContentAsByteArray());
    }
    private JsonNode awaitState(String path, String token, String expected) throws Exception {
        long deadline = System.nanoTime() + java.util.concurrent.TimeUnit.SECONDS.toNanos(240);
        JsonNode response;
        do {
            response = read(path, token);
            String state = response.path("status").asText();
            if (state.equals(expected)) return response;
            assertThat(state).withFailMessage("Unexpected AI failure: %s", response).isNotEqualTo("FAILED");
            assertThat(response.path("error").asText()).isEmpty();
            Thread.sleep(250);
        } while (System.nanoTime() < deadline);
        throw new AssertionError("Timed out waiting for " + expected + ": " + response);
    }
    private String register(String role) throws Exception {
        return postJson("/api/auth/register", null, Map.of("email", role.toLowerCase() + "@python.example.test",
            "password", "python-workflow-2026", "name", "Python " + role, "role", role), 201).path("token").asText();
    }

    @Test void publicApiV2SupportsGenerationRevisionSubmissionAndFinalReport() throws Exception {
        String company = register("COMPANY"), person = register("PERSON");
        String privateMarker = "PRIVATE-PYTHON-CLIENT";
        String attachment = Base64.getEncoder().encodeToString(("비공개 문서: " + privateMarker).getBytes(StandardCharsets.UTF_8));
        JsonNode created = postJson("/api/company/requests", company, Map.of(
            "requestText", "고객사 " + privateMarker + "의 월별 매출 CSV를 정제하고 지점별 집계를 자동화하고 싶습니다.",
            "jobRole", "데이터 분석", "sensitiveWords", privateMarker, "generalization", "high",
            "attachments", List.of(Map.of("name", "request.txt", "contentBase64", attachment))), 202);
        String projectId = created.path("id").asText(), projectPath = "/api/company/projects/" + projectId;
        JsonNode draft = awaitState(projectPath, company, "DRAFT");
        assertThat(draft.path("tasks").size()).isEqualTo(3);
        assertThat(draft.path("dataset").asText()).contains("\n");
        assertThat(draft.path("aiProvider").asText()).isEqualTo("fake");
        assertThat(draft.path("disclosure").path("status").asText()).isEqualTo("unchecked");
        postJson(projectPath + "/revise", company, Map.of("feedback", "결과물의 재현 방법을 명확하게 설명해 주세요."), 202);
        assertThat(awaitState(projectPath, company, "DRAFT").path("revision").asInt()).isEqualTo(2);
        postJson(projectPath + "/publish", company, Map.of(), 200);
        assertThat(read("/api/projects/" + projectId, person).toString())
            .doesNotContain(privateMarker, attachment, "requestText", "clarifications", "disclosure", "aiDraft");

        String applicationId = postJson("/api/applications", person,
            Map.of("projectId", projectId, "difficulty", "beginner"), 201).path("id").asText();
        String applicationPath = "/api/applications/" + applicationId;
        Map<String, Object> work = Map.of("files", Map.of("solution.py", "raise RuntimeError('submitted code must never run')"),
            "process", "원본 CSV의 결측값과 집계 기준을 확인하고 예상 결과와 비교하여 검증했습니다.",
            "references", "Pandas 공식 문서", "aiUsage", "사용하지 않음");
        postJson(applicationPath + "/work", person, work, 200);
        postJson(applicationPath + "/submit", person, work, 200);
        JsonNode followup = awaitState(applicationPath, person, "FOLLOWUP");
        List<String> answers = java.util.stream.IntStream.range(0, followup.path("questions").size())
            .mapToObj(i -> "예외 입력과 정상 입력의 기대 결과를 직접 계산하고 비교하여 검증했습니다.").toList();
        postJson(applicationPath + "/answers", person, Map.of("answers", answers), 202);
        JsonNode reviewed = awaitState(applicationPath, person, "REVIEW");
        assertThat(reviewed.path("evaluation").path("demo").asBoolean()).isTrue();
        assertThat(reviewed.path("evaluation").path("criteria")).isNotEmpty();
        reviewed.path("evaluation").path("criteria").forEach(c -> assertThat(c.path("status").asText()).isEqualTo("unverified"));
        postJson("/api/company/submissions/" + applicationId + "/finalize", company,
            Map.of("feedback", "근거와 검증 과정이 잘 정리되어 있습니다. 다음에는 대용량 입력도 확인해 주세요."), 200);
        assertThat(postJson(applicationPath + "/portfolio", person, Map.of(), 200).path("portfolio").asBoolean()).isTrue();
    }
}
