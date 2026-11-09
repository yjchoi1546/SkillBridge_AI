package com.skillbridge;

import static com.skillbridge.ApiModels.*;
import static org.assertj.core.api.Assertions.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.file.Path;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;

class DurableRepositoryTest {
    @TempDir Path directory;
    private final ObjectMapper mapper = new ObjectMapper();
    private DriverManagerDataSource database(String url) {
        DriverManagerDataSource source = new DriverManagerDataSource(url, "sa", "");
        source.setDriverClassName("org.h2.Driver");
        new ResourceDatabasePopulator(new ClassPathResource("schema.sql")).execute(source);
        return source;
    }
    private DemoRepository repository(DriverManagerDataSource source, boolean seed) throws IOException {
        return new DemoRepository(mapper, new JdbcTemplate(source), new DataSourceTransactionManager(source), seed);
    }

    @Test void restoresPrivateOriginalVersionsSubmissionAndJobsFromFileDatabase() throws Exception {
        String url = "jdbc:h2:file:" + directory.resolve("workspace").toString().replace('\\', '/') + ";MODE=PostgreSQL";
        var firstSource = database(url);
        DemoRepository first = repository(firstSource, true);
        var p = first.projects.get("sales-report");
        p.original = new NewRequest("고객사 PRIVATE-NAME의 주간 매출 데이터를 정제하는 업무를 자동화하고 싶습니다.",
            "데이터 분석", "PRIVATE-NAME", "high", List.of(new Attachment("original.txt", "cHJpdmF0ZQ==")));
        p.revision = 2; p.feedback = "초급 과제 범위를 수정해 주세요.";
        p.versions.put(2, p.publicData.deepCopy().put("title", "두 번째 공개본"));
        p.privateData.putObject("aiDraft").put("secret", "PRIVATE-NAME");
        p.privateData.putObject("disclosure").put("status", "needs_review");
        p.privateData.putArray("clarifyingQuestions").add("확인할 질문");
        var app = first.applications.get("app-sales");
        app.data.put("process", "정제 기준을 정하고 직접 집계 결과를 검증한 기록입니다.");
        app.data.putObject("files").put("solution.py", "print('stored, never executed')");
        app.data.put("feedback", "근거가 명확한 결과물입니다. 예외 상황의 검증을 추가해 주세요.");
        app.status = "FINALIZED";
        first.jobs.put("job-1", mapper.createObjectNode().put("id", "job-1").put("ownerId", "company-demo").put("status", "SUCCEEDED"));
        first.persist();

        DemoRepository restored = repository(database(url), true);
        assertThat(restored.projects.get("sales-report").view(true).path("requestText").asText()).contains("PRIVATE-NAME");
        assertThat(restored.projects.get("sales-report").view(false).toString()).doesNotContain("PRIVATE-NAME", "contentBase64");
        assertThat(restored.projects.get("sales-report").versions).hasSize(2);
        assertThat(restored.projects.get("sales-report").feedback).isEqualTo(p.feedback);
        assertThat(restored.projects.get("sales-report").privateData.path("aiDraft").path("secret").asText()).isEqualTo("PRIVATE-NAME");
        assertThat(restored.projects.get("sales-report").view(true).path("disclosure").path("status").asText()).isEqualTo("needs_review");
        assertThat(restored.projects.get("sales-report").view(true).has("aiDraft")).isFalse();
        assertThat(restored.applications.get("app-sales").view().path("process").asText()).isEqualTo(app.data.path("process").asText());
        assertThat(restored.applications.get("app-sales").status).isEqualTo("FINALIZED");
        assertThat(restored.jobs.get("job-1").path("status").asText()).isEqualTo("SUCCEEDED");
    }

    @Test void recoversInterruptedGenerationEvaluationAndJobStates() throws Exception {
        var source = database("jdbc:h2:mem:" + UUID.randomUUID() + ";MODE=PostgreSQL;DB_CLOSE_DELAY=-1");
        DemoRepository first = repository(source, true);
        first.projects.get("sales-report").status = "GENERATING";
        first.applications.get("app-sales").status = "EVALUATING";
        var questioning = new DemoRepository.Application("questioning", "person-other", "support-ai", Difficulty.beginner, mapper);
        questioning.status = "QUESTIONING"; first.applications.put(questioning.id, questioning);
        for (String status : List.of("QUEUED", "RUNNING")) first.jobs.put(status, mapper.createObjectNode().put("id", status).put("status", status).put("ownerId", "company-demo"));
        first.persist();

        DemoRepository recovered = repository(source, true);
        assertThat(recovered.projects.get("sales-report").status).isEqualTo("FAILED");
        assertThat(recovered.projects.get("sales-report").error).contains("재시작");
        assertThat(recovered.applications.get("app-sales").status).isEqualTo("FOLLOWUP");
        assertThat(recovered.applications.get("questioning").status).isEqualTo("WORKING");
        assertThat(recovered.jobs.values()).allSatisfy(job -> assertThat(job.path("status").asText()).isEqualTo("FAILED"));
        assertThat(repository(source, true).projects.get("sales-report").status).isEqualTo("FAILED");
    }

    @Test void anInitializedEmptyDatabaseIsNeverReseeded() throws Exception {
        var source = database("jdbc:h2:mem:" + UUID.randomUUID() + ";MODE=PostgreSQL;DB_CLOSE_DELAY=-1");
        assertThat(repository(source, false).projects).isEmpty();
        DemoRepository reopenedWithSeedingEnabled = repository(source, true);
        assertThat(reopenedWithSeedingEnabled.projects).isEmpty();
        assertThat(reopenedWithSeedingEnabled.applications).isEmpty();
    }

    @Test void partialSnapshotsFailWithoutReplacingExistingData() {
        var source = database("jdbc:h2:mem:" + UUID.randomUUID() + ";MODE=PostgreSQL;DB_CLOSE_DELAY=-1");
        var jdbc = new JdbcTemplate(source);
        jdbc.update("INSERT INTO workspace_state(state_key,payload) VALUES ('projects',?)", "[]");
        assertThatThrownBy(() -> repository(source, true)).isInstanceOf(IOException.class).hasMessageContaining("Incomplete");
        assertThat(jdbc.queryForObject("SELECT COUNT(*) FROM workspace_state", Integer.class)).isEqualTo(1);
    }
}
