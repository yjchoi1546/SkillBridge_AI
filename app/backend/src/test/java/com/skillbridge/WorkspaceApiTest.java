package com.skillbridge;

import static com.skillbridge.ApiModels.*;
import static org.assertj.core.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest(properties={"skillbridge.demo-delay-ms=30", "skillbridge.demo-enabled=true", "skillbridge.ai.mode=demo"})
@AutoConfigureMockMvc
class WorkspaceApiTest {
    @Autowired MockMvc mvc;
    @Autowired ObjectMapper mapper;
    @Autowired WorkspaceService service;
    private String login(String role) throws Exception {
        JsonNode session = mapper.readTree(mvc.perform(post("/api/auth/demo").contentType(MediaType.APPLICATION_JSON).content(mapper.writeValueAsBytes(Map.of("role", role)))).andExpect(status().isOk()).andReturn().getResponse().getContentAsByteArray());
        return "Bearer " + session.path("token").asText();
    }
    private JsonNode send(String path, String token, Object body, int expected) throws Exception {
        return mapper.readTree(mvc.perform(post(path).header("Authorization", token).contentType(MediaType.APPLICATION_JSON).content(mapper.writeValueAsBytes(body))).andExpect(status().is(expected)).andReturn().getResponse().getContentAsByteArray());
    }
    private JsonNode read(String path, String token, int expected) throws Exception {
        return mapper.readTree(mvc.perform(get(path).header("Authorization", token)).andExpect(status().is(expected)).andReturn().getResponse().getContentAsByteArray());
    }
    private void await(String path, String token, String field, String value) throws Exception {
        for (int i=0; i<100; i++) { if (read(path, token, 200).path(field).asText().equals(value)) return; Thread.sleep(15); }
        fail("작업이 기대 상태로 전환되지 않았습니다: " + value);
    }
    @Test void privateOriginalNeverAppearsInPublicProjectAndOtherOwnersAreDenied() throws Exception {
        String company = login("COMPANY"), person = login("PERSON");
        JsonNode created = send("/api/company/requests", company, Map.of("requestText", "내부 거래처 SECRET-CLIENT의 매출 데이터를 정제하는 업무를 자동화하고 싶습니다.", "jobRole", "데이터 분석", "sensitiveWords", "SECRET-CLIENT", "generalization", "high", "attachments", List.of(Map.of("name", "private.txt", "contentBase64", "U0VDUkVU"))), 202);
        String id = created.path("id").asText();
        assertThat(created.path("status").asText()).isEqualTo("GENERATING");
        read("/api/projects/"+id, person, 404);
        read("/api/company/projects/"+id, person, 403);
        read("/api/jobs/"+created.path("jobId").asText(), person, 404);
        assertThatThrownBy(() -> service.companyProject(new Actor("another-company", "다른 기업", Role.COMPANY), id)).hasMessageContaining("404");
        await("/api/company/projects/"+id, company, "status", "DRAFT");
        send("/api/company/projects/"+id+"/revise", company, Map.of("feedback", "초급 과제 범위를 검토하고 조정해 주세요."), 202);
        await("/api/company/projects/"+id, company, "status", "DRAFT");
        assertThat(read("/api/company/projects/"+id+"/versions", company, 200).size()).isEqualTo(2);
        send("/api/company/projects/"+id+"/publish", company, Map.of(), 200);
        JsonNode published = read("/api/projects/"+id, person, 200);
        assertThat(published.toString()).doesNotContain("SECRET-CLIENT", "requestText", "contentBase64", "sensitiveWords", "jobId", "feedback");
        send("/api/company/projects/"+id+"/publish", company, Map.of(), 409);
    }
    @Test void submissionLifecycleRequiresAnswersAndCompanyReview() throws Exception {
        String person = login("PERSON"), company = login("COMPANY");
        JsonNode app = send("/api/applications", person, Map.of("projectId", "support-ai", "difficulty", "intermediate"), 201);
        String id = app.path("id").asText();
        assertThat(send("/api/applications", person, Map.of("projectId", "support-ai", "difficulty", "beginner"), 201).path("id").asText()).isEqualTo(id);
        send("/api/applications/"+id+"/portfolio", person, Map.of(), 409);
        Map<String,Object> work = Map.of("files", Map.of("solution.py", "print('demo, not executed')"), "process", "분류 규칙을 정의하고 정상 입력과 예외 입력의 결과를 직접 비교하여 검증했습니다.", "references", "공식 문서", "aiUsage", "사용하지 않음");
        send("/api/applications/"+id+"/work", person, work, 200);
        send("/api/applications/"+id+"/submit", person, work, 200);
        send("/api/applications/"+id+"/work", person, work, 409);
        read("/api/company/submissions/"+id, company, 409);
        send("/api/applications/"+id+"/answers", person, Map.of("answers", List.of("짧음", "짧음", "짧음")), 400);
        send("/api/applications/"+id+"/answers", person, Map.of("answers", List.of("유형별로 규칙을 나누어 설명 가능성을 우선했습니다.", "빈 문자열과 분류되지 않는 입력을 별도로 확인했습니다.", "참고 문서는 사용했지만 코드는 직접 작성하고 검증했습니다.")), 202);
        await("/api/applications/"+id, person, "status", "REVIEW");
        JsonNode reviewed = read("/api/company/submissions/"+id, company, 200);
        assertThat(reviewed.path("evaluation").path("criteria").get(0).path("status").asText()).isEqualTo("unverified");
        send("/api/company/submissions/"+id+"/finalize", person, Map.of("feedback", "결과물이 잘 정리되어 있습니다. 예외 상황을 추가해 주세요."), 403);
        send("/api/company/submissions/"+id+"/finalize", company, Map.of("feedback", "결과물이 잘 정리되어 있습니다. 예외 상황을 추가해 주세요."), 200);
        assertThat(send("/api/applications/"+id+"/portfolio", person, Map.of(), 200).path("portfolio").asBoolean()).isTrue();
        assertThatThrownBy(() -> service.getApplication(new Actor("other-person", "다른 개인", Role.PERSON), id)).hasMessageContaining("404");
    }
    @Test void missingSessionInvalidInputAndLargeBodiesAreRejected() throws Exception {
        mvc.perform(get("/api/company/projects")).andExpect(status().isUnauthorized());
        mvc.perform(post("/api/auth/demo").contentType(MediaType.APPLICATION_JSON).content("{\"role\":\"ADMIN\"}")).andExpect(status().isBadRequest());
        String token = login("PERSON");
        send("/api/applications/app-sales/work", token, Map.of("files", Map.of("../escape.py", "pass"), "process", "", "references", "", "aiUsage", ""), 409);
        mvc.perform(post("/api/auth/demo").contentType(MediaType.APPLICATION_JSON).content(" ".repeat(2100001))).andExpect(status().isPayloadTooLarge());
    }
}
