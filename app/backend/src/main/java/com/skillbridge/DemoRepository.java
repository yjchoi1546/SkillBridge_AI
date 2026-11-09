package com.skillbridge;

import static com.skillbridge.ApiModels.*;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.sql.init.dependency.DependsOnDatabaseInitialization;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;
import org.springframework.web.server.ResponseStatusException;

/** Application-owned snapshot adapter backed by JDBC. Private and public views remain distinct. */
// JDBC already translates database exceptions. A repository proxy would leave the
// fields read by WorkspaceService on an uninitialized proxy instance.
@Component
@DependsOnDatabaseInitialization
class DemoRepository {
    static final class Project {
        private static final java.util.Set<String> PUBLIC_FIELDS = java.util.Set.of(
            "title", "company", "domain", "summary", "skills", "difficulty", "duration", "deadline",
            "applicants", "color", "mark", "dataset", "purpose", "terms", "engine", "aiProvider", "domainTags");
        private static final java.util.Set<String> TASK_FIELDS = java.util.Set.of(
            "difficulty", "title", "goal", "scope", "steps", "deliverables", "skills");
        final String id, ownerId;
        final ObjectNode publicData;
        final ObjectNode privateData;
        NewRequest original;
        String status = "PUBLISHED", feedback = "", error = "", jobId;
        int revision = 1;
        final Map<Integer, ObjectNode> versions = new LinkedHashMap<>();
        Project(String id, String ownerId, ObjectNode publicData) {
            this.id = id; this.ownerId = ownerId; this.publicData = publicData; this.privateData = publicData.objectNode();
            versions.put(1, publicData.deepCopy());
        }
        ObjectNode view(boolean privateView) {
            ObjectNode out = publicData.objectNode();
            for (String field : PUBLIC_FIELDS) if (publicData.has(field)) out.set(field, publicData.get(field).deepCopy());
            var tasks = out.putArray("tasks");
            for (JsonNode task : publicData.path("tasks")) {
                ObjectNode visible = tasks.addObject();
                for (String field : TASK_FIELDS) if (task.has(field)) visible.set(field, task.get(field).deepCopy());
                var rubrics = visible.putArray("rubric");
                for (JsonNode rubric : task.path("rubric")) {
                    ObjectNode item = rubrics.addObject();
                    for (String field : java.util.List.of("criterion", "description", "auto_checkable"))
                        if (rubric.has(field)) item.set(field, rubric.get(field).deepCopy());
                }
                var tests = visible.putArray("tests");
                for (JsonNode test : task.path("tests")) {
                    ObjectNode item = tests.addObject();
                    for (String field : java.util.List.of("id", "description", "kind"))
                        if (test.has(field)) item.set(field, test.get(field).deepCopy());
                }
            }
            out.put("id", id); out.put("status", status);
            if (privateView) {
                for (String key : java.util.List.of("disclosure", "clarifyingQuestions", "clarifications"))
                    if (privateData.has(key)) out.set(key, privateData.get(key).deepCopy());
                out.put("revision", revision); out.put("feedback", feedback); out.put("error", error);
                if (jobId != null) out.put("jobId", jobId);
                if (original != null) {
                    out.put("requestText", original.requestText()); out.put("sensitiveWords", original.sensitiveWords()); out.put("generalization", original.generalization());
                    var files = out.putArray("attachments");
                    original.attachments().forEach(a -> files.addObject().put("name", a.name()).put("contentBase64", a.contentBase64()));
                }
            }
            return out;
        }
    }
    static final class Application {
        final String id, ownerId, projectId;
        final Difficulty difficulty;
        String status = "WORKING";
        final ObjectNode data;
        Application(String id, String ownerId, String projectId, Difficulty difficulty, ObjectMapper mapper) {
            this.id = id; this.ownerId = ownerId; this.projectId = projectId; this.difficulty = difficulty;
            data = mapper.createObjectNode(); data.put("process", ""); data.put("references", ""); data.put("aiUsage", ""); data.put("feedback", ""); data.put("portfolio", false);
            data.putObject("files"); data.putArray("questions"); data.putArray("answers");
        }
        ObjectNode view() { ObjectNode out = data.deepCopy(); out.put("id", id); out.put("projectId", projectId); out.put("difficulty", difficulty.name()); out.put("status", status); return out; }
    }
    final Map<String, Project> projects = new LinkedHashMap<>();
    final Map<String, Application> applications = new LinkedHashMap<>();
    final Map<String, ObjectNode> jobs = new LinkedHashMap<>();
    private final ObjectMapper mapper;
    private final JdbcTemplate jdbc;
    private final TransactionTemplate transaction;
    private volatile boolean available = true;

    DemoRepository(ObjectMapper mapper, JdbcTemplate jdbc, PlatformTransactionManager transactionManager,
                   @Value("${skillbridge.seed-demo-data:true}") boolean seedDemoData) throws IOException {
        this.mapper = mapper; this.jdbc = jdbc; this.transaction = new TransactionTemplate(transactionManager);
        Map<String, String> snapshots = jdbc.query("SELECT state_key, payload FROM workspace_state", rows -> {
            Map<String, String> values = new LinkedHashMap<>();
            while (rows.next()) values.put(rows.getString("state_key"), rows.getString("payload"));
            return values;
        });
        if (snapshots.containsKey("format")) {
            if (!"1".equals(snapshots.get("format"))) throw new IOException("Unsupported workspace snapshot format");
            restore(snapshots);
            if (recoverInterruptedWork()) persist();
        } else {
            // Refuse to silently seed over a partial or foreign state snapshot.
            if (!snapshots.isEmpty()) throw new IOException("Incomplete workspace state; restore a database backup before starting");
            if (seedDemoData) seed();
            persist();
        }
    }

    private void seed() throws IOException {
        try (var stream = new ClassPathResource("demo-projects.json").getInputStream()) {
            for (JsonNode node : mapper.readTree(stream)) {
                ObjectNode data = (ObjectNode) node;
                String id = data.get("id").asText();
                projects.put(id, new Project(id, "company-demo", data));
            }
        }
        applications.put("app-sales", new Application("app-sales", "person-demo", "sales-report", Difficulty.beginner, mapper));
    }

    private ObjectNode object(JsonNode node, String field) throws IOException {
        JsonNode value = field == null ? node : node.get(field);
        if (!(value instanceof ObjectNode object)) throw new IOException("Invalid workspace snapshot object");
        return object.deepCopy();
    }

    private JsonNode array(Map<String, String> snapshots, String name) throws IOException {
        String value = snapshots.get(name);
        if (value == null) throw new IOException("Missing workspace snapshot: " + name);
        JsonNode node = mapper.readTree(value);
        if (!node.isArray()) throw new IOException("Invalid workspace snapshot array: " + name);
        return node;
    }

    private void restore(Map<String, String> snapshots) throws IOException {
        for (JsonNode node : array(snapshots, "projects")) {
            Project p = new Project(node.required("id").asText(), node.required("ownerId").asText(), object(node, "publicData"));
            p.status = node.required("status").asText();
            p.feedback = node.path("feedback").asText(""); p.error = node.path("error").asText("");
            p.jobId = node.hasNonNull("jobId") ? node.get("jobId").asText() : null;
            p.revision = node.path("revision").asInt(1);
            if (node.hasNonNull("privateData")) p.privateData.setAll(object(node, "privateData"));
            if (node.hasNonNull("original")) p.original = mapper.treeToValue(node.get("original"), NewRequest.class);
            p.versions.clear();
            var versions = object(node, "versions").fields();
            while (versions.hasNext()) {
                var version = versions.next();
                try { p.versions.put(Integer.parseInt(version.getKey()), object(version.getValue(), null)); }
                catch (NumberFormatException e) { throw new IOException("Invalid project version in workspace snapshot", e); }
            }
            projects.put(p.id, p);
        }
        for (JsonNode node : array(snapshots, "applications")) {
            String projectId = node.required("projectId").asText();
            if (!projects.containsKey(projectId)) throw new IOException("Application refers to missing project");
            Application a = new Application(node.required("id").asText(), node.required("ownerId").asText(),
                projectId, Difficulty.valueOf(node.required("difficulty").asText()), mapper);
            a.status = node.required("status").asText();
            a.data.removeAll(); a.data.setAll(object(node, "data"));
            applications.put(a.id, a);
        }
        for (JsonNode node : array(snapshots, "jobs")) {
            ObjectNode job = object(node, null); jobs.put(job.required("id").asText(), job);
        }
    }

    private boolean recoverInterruptedWork() {
        boolean changed = false;
        for (Project p : projects.values()) {
            if ("GENERATING".equals(p.status)) {
                p.status = "FAILED";
                p.error = "서버가 재시작되어 생성이 중단되었습니다. 다시 시도해 주세요.";
                changed = true;
            }
        }
        for (Application a : applications.values()) {
            if ("QUESTIONING".equals(a.status)) {
                a.status = "WORKING";
                a.data.put("error", "서버가 재시작되어 질문 생성이 중단되었습니다. 제출을 다시 시도해 주세요.");
                changed = true;
            }
            if ("EVALUATING".equals(a.status)) {
                a.status = "FOLLOWUP";
                a.data.put("error", "서버가 재시작되어 평가가 중단되었습니다. 답변을 다시 제출하면 재시도합니다.");
                changed = true;
            }
        }
        for (ObjectNode job : jobs.values()) {
            if (java.util.List.of("QUEUED", "RUNNING").contains(job.path("status").asText())) {
                job.put("status", "FAILED").put("error", "서버 재시작으로 중단된 작업입니다. 다시 시도해 주세요.");
                changed = true;
            }
        }
        return changed;
    }

    /** Call while holding the WorkspaceService mutation lock; commits all domain state atomically. */
    synchronized void persist() {
        assertAvailable();
        var projectRows = mapper.createArrayNode();
        for (Project p : projects.values()) {
            ObjectNode node = projectRows.addObject().put("id", p.id).put("ownerId", p.ownerId).put("status", p.status)
                .put("feedback", p.feedback).put("error", p.error).put("revision", p.revision);
            node.set("publicData", p.publicData.deepCopy());
            node.set("privateData", p.privateData.deepCopy());
            if (p.original != null) node.set("original", mapper.valueToTree(p.original));
            if (p.jobId != null) node.put("jobId", p.jobId);
            ObjectNode versions = node.putObject("versions");
            p.versions.forEach((number, version) -> versions.set(Integer.toString(number), version.deepCopy()));
        }
        var applicationRows = mapper.createArrayNode();
        for (Application a : applications.values()) {
            ObjectNode node = applicationRows.addObject().put("id", a.id).put("ownerId", a.ownerId).put("projectId", a.projectId)
                .put("difficulty", a.difficulty.name()).put("status", a.status);
            node.set("data", a.data.deepCopy());
        }
        var jobRows = mapper.createArrayNode(); jobs.values().forEach(job -> jobRows.add(job.deepCopy()));
        Map<String, String> snapshots = new LinkedHashMap<>();
        snapshots.put("format", "1"); snapshots.put("projects", projectRows.toString());
        snapshots.put("applications", applicationRows.toString()); snapshots.put("jobs", jobRows.toString());
        try {
            transaction.executeWithoutResult(status -> snapshots.forEach((key, value) -> {
                if (jdbc.update("UPDATE workspace_state SET payload=? WHERE state_key=?", value, key) == 0)
                    jdbc.update("INSERT INTO workspace_state(state_key,payload) VALUES (?,?)", key, value);
            }));
        } catch (RuntimeException error) {
            available = false;
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "저장소 오류로 작업을 중단했습니다. 서버를 재시작하기 전에 DB 연결과 저장 공간을 확인해 주세요.", error);
        }
    }

    boolean isAvailable() { return available; }

    void assertAvailable() {
        if (!available) throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE,
            "저장소 오류로 워크스페이스를 잠시 사용할 수 없습니다. 서버 관리자에게 문의해 주세요.");
    }
}
