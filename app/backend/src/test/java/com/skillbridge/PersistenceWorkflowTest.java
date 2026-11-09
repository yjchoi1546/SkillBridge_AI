package com.skillbridge;

import static com.skillbridge.ApiModels.*;
import static org.assertj.core.api.Assertions.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicBoolean;
import org.junit.jupiter.api.Test;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.datasource.DataSourceTransactionManager;
import org.springframework.jdbc.datasource.DriverManagerDataSource;
import org.springframework.jdbc.datasource.init.ResourceDatabasePopulator;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.web.server.ResponseStatusException;

class PersistenceWorkflowTest {
    private final ObjectMapper mapper = new ObjectMapper();
    private DriverManagerDataSource database() {
        DriverManagerDataSource source = new DriverManagerDataSource("jdbc:h2:mem:" + UUID.randomUUID() + ";MODE=PostgreSQL;DB_CLOSE_DELAY=-1", "sa", "");
        source.setDriverClassName("org.h2.Driver");
        new ResourceDatabasePopulator(new ClassPathResource("schema.sql")).execute(source);
        return source;
    }
    private DemoRepository repository(DriverManagerDataSource source) throws IOException {
        return new DemoRepository(mapper, new JdbcTemplate(source), new DataSourceTransactionManager(source), false);
    }
    private void rejectApplicationUpdates(JdbcTemplate jdbc) {
        jdbc.execute("ALTER TABLE workspace_state ADD CONSTRAINT test_application_write CHECK(state_key <> 'applications' OR payload = '[]')");
    }
    private void addUncommittedState(DemoRepository repository) {
        repository.projects.put("private-project", new DemoRepository.Project("private-project", "company", mapper.createObjectNode().put("title", "uncommitted-title")));
        repository.applications.put("app", new DemoRepository.Application("app", "person", "private-project", Difficulty.beginner, mapper));
    }

    @Test void failedSnapshotWriteRollsBackDatabaseAndClosesWorkspaceUntilRestart() throws Exception {
        var source = database(); var jdbc = new JdbcTemplate(source); var repository = repository(source);
        rejectApplicationUpdates(jdbc); addUncommittedState(repository);
        assertThatThrownBy(repository::persist).isInstanceOf(ResponseStatusException.class).hasMessageContaining("503");
        assertThat(repository.isAvailable()).isFalse();
        assertThatThrownBy(repository::assertAvailable).isInstanceOf(ResponseStatusException.class).hasMessageContaining("503");
        // The first UPDATE must be rolled back when the later application UPDATE fails.
        assertThat(jdbc.queryForObject("SELECT payload FROM workspace_state WHERE state_key='projects'", String.class)).isEqualTo("[]");
        DemoRepository restarted = repository(source);
        assertThat(restarted.isAvailable()).isTrue();
        assertThat(restarted.projects).isEmpty(); assertThat(restarted.applications).isEmpty();

        var filter = new WorkspaceAvailabilityFilter(repository); var called = new AtomicBoolean();
        var request = new MockHttpServletRequest("GET", "/api/projects"); var response = new MockHttpServletResponse();
        filter.doFilter(request, response, (incoming, outgoing) -> called.set(true));
        assertThat(called).isFalse(); assertThat(response.getStatus()).isEqualTo(503);
        assertThat(response.getContentAsString()).doesNotContain("uncommitted-title");
        var authResponse = new MockHttpServletResponse();
        filter.doFilter(new MockHttpServletRequest("POST", "/api/auth/login"), authResponse, (incoming, outgoing) -> called.set(true));
        assertThat(called).isTrue();
    }

    @Test void inFlightResponseIsDiscardedWhenStorageFailsDuringControllerExecution() throws Exception {
        var source = database(); var jdbc = new JdbcTemplate(source); var repository = repository(source);
        rejectApplicationUpdates(jdbc);
        var filter = new WorkspaceAvailabilityFilter(repository); var response = new MockHttpServletResponse();
        filter.doFilter(new MockHttpServletRequest("GET", "/api/projects"), response, (request, outgoing) -> {
            outgoing.setCharacterEncoding("UTF-8"); outgoing.getWriter().write("UNCOMMITTED-PRIVATE-DATA");
            addUncommittedState(repository);
            try { repository.persist(); } catch (ResponseStatusException expected) { /* handled as a controller exception */ }
        });
        assertThat(response.getStatus()).isEqualTo(503);
        assertThat(response.getContentAsString()).doesNotContain("UNCOMMITTED-PRIVATE-DATA");
    }

    @Test void projectResponseUsesExplicitPublicFieldsAndDefensiveNestedCopies() {
        var raw = mapper.createObjectNode().put("title", "Public title").put("requestText", "PRIVATE-REQUEST").put("ownerId", "PRIVATE-OWNER");
        var task = raw.putArray("tasks").addObject().put("title", "Public task").put("difficulty", "beginner").put("sourceDocument", "PRIVATE-DOCUMENT");
        task.putArray("rubric").addObject().put("criterion", "Correctness").put("sourceDocument", "PRIVATE-RUBRIC");
        task.putArray("tests").addObject().put("id", "T1").put("description", "Public test").put("kind", "manual").put("privateFixture", "PRIVATE-FIXTURE");
        var p = new DemoRepository.Project("p", "company", raw);
        p.original = new NewRequest("기업 PRIVATE-REQUEST가 포함된 비공개 업무 원문을 충분히 작성합니다.", "데이터 분석", "PRIVATE-REQUEST", "high", List.of());
        p.privateData.putObject("aiDraft").put("source", "PRIVATE-AI");
        p.privateData.putObject("disclosure").put("detail", "PRIVATE-DISCLOSURE");
        var publicView = p.view(false);
        assertThat(publicView.toString()).doesNotContain("PRIVATE-", "sourceDocument", "ownerId", "requestText", "privateFixture");
        assertThat(p.view(true).toString()).contains("PRIVATE-REQUEST", "PRIVATE-DISCLOSURE").doesNotContain("PRIVATE-AI");
        publicView.withArray("tasks").removeAll();
        assertThat(p.publicData.path("tasks").size()).isEqualTo(1);
    }
}
