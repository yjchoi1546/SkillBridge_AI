package com.skillbridge;

import static com.skillbridge.ApiModels.*;
import static com.skillbridge.DemoRepository.*;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import jakarta.annotation.PreDestroy;
import java.time.LocalDate;
import java.util.*;
import java.util.concurrent.*;
import java.util.function.Consumer;
import java.util.regex.Pattern;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ClassPathResource;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

@Service
class WorkspaceService {
    private final DemoRepository store;
    private final ObjectMapper mapper;
    private final PythonAiGateway ai;
    private final DisclosureScanner scanner;
    private final long delayMs;
    private final String aiMode;
    private final ObjectNode template;
    private final ThreadPoolExecutor workers = new ThreadPoolExecutor(2, 2, 0, TimeUnit.MILLISECONDS, new ArrayBlockingQueue<>(20));
    private static final Pattern FILE_NAME = Pattern.compile("[^/\\\\\\p{Cntrl}]{1,150}\\.(py|ipynb|md|txt|csv|json|js|jsx|ts|tsx|java|html|css|sql|yaml|yml)", Pattern.CASE_INSENSITIVE);
    WorkspaceService(DemoRepository store, ObjectMapper mapper, PythonAiGateway ai, DisclosureScanner scanner,
                     @Value("${skillbridge.demo-delay-ms:1800}") long delayMs,
                     @Value("${skillbridge.ai.mode:python}") String aiMode) throws java.io.IOException {
        this.store = store; this.mapper = mapper; this.ai = ai; this.scanner = scanner; this.delayMs = delayMs; this.aiMode = aiMode;
        if (!List.of("python", "demo").contains(aiMode)) throw new IllegalArgumentException("skillbridge.ai.mode must be python or demo");
        try (var stream = new ClassPathResource("demo-projects.json").getInputStream()) { template = (ObjectNode) mapper.readTree(stream).get(0); }
    }
    Map<String,Object> health() { return Map.of("status", "UP", "storage", "jdbc", "ai", aiMode, "provider", aiMode.equals("demo") ? "demo" : ai.provider()); }
    private ResponseStatusException invalid(String message) { return new ResponseStatusException(HttpStatus.CONFLICT, message); }
    private Project project(String id) { Project p = store.projects.get(id); if (p == null) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "프로젝트를 찾을 수 없습니다."); return p; }
    private Project ownedProject(Actor actor, String id) { Project p = project(id); if (!p.ownerId.equals(actor.id())) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "프로젝트를 찾을 수 없습니다."); return p; }
    private Application application(Actor actor, String id) { Application a = store.applications.get(id); if (a == null || !a.ownerId.equals(actor.id())) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "참여 기록을 찾을 수 없습니다."); return a; }
    private Application companyApplication(Actor actor, String id) { Application a = store.applications.get(id); if (a == null) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "제출물을 찾을 수 없습니다."); ownedProject(actor, a.projectId); if (!List.of("REVIEW", "FINALIZED").contains(a.status)) throw invalid("평가가 끝난 제출물만 확인할 수 있습니다."); return a; }
    synchronized List<ObjectNode> publicProjects() { return store.projects.values().stream().filter(p -> p.status.equals("PUBLISHED")).map(p -> p.view(false)).toList(); }
    synchronized ObjectNode publicProject(String id) { Project p = project(id); if (!p.status.equals("PUBLISHED")) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "공개 프로젝트를 찾을 수 없습니다."); return p.view(false); }
    synchronized List<ObjectNode> participatingProjects(Actor actor) { return store.applications.values().stream().filter(a -> a.ownerId.equals(actor.id())).map(a -> project(a.projectId)).distinct().map(p -> p.view(false)).toList(); }
    synchronized List<ObjectNode> companyProjects(Actor actor) { return store.projects.values().stream().filter(p -> p.ownerId.equals(actor.id())).map(p -> p.view(true)).toList().reversed(); }
    synchronized ObjectNode companyProject(Actor actor, String id) { return ownedProject(actor, id).view(true); }
    synchronized List<ObjectNode> versions(Actor actor, String id) { return ownedProject(actor, id).versions.entrySet().stream().map(e -> { ObjectNode out = e.getValue().deepCopy(); out.put("revision", e.getKey()); return out; }).toList(); }
    synchronized ObjectNode create(Actor actor, NewRequest request) {
        if (!Set.of("데이터 분석", "AI · 머신러닝", "백엔드 개발", "프론트엔드 개발", "업무 자동화").contains(request.jobRole())) throw invalid("지원하는 직무를 선택해 주세요.");
        if (store.projects.size() >= 200) throw new ResponseStatusException(HttpStatus.TOO_MANY_REQUESTS, "프로젝트 생성 한도에 도달했습니다.");
        int size = 0;
        for (Attachment file : request.attachments()) {
            if (!file.name().matches("(?i)[^/\\\\\\p{Cntrl}]+\\.(pdf|docx|txt|md|csv)")) throw invalid("지원하지 않는 첨부 파일명입니다.");
            try { byte[] bytes = Base64.getDecoder().decode(file.contentBase64()); if (bytes.length > 750000) throw invalid("파일 하나는 750KB 이하여야 합니다."); size += bytes.length; }
            catch (IllegalArgumentException e) { throw invalid("첨부 파일 인코딩이 올바르지 않습니다."); }
        }
        if (size > 1050000) throw invalid("첨부 파일 합계는 약 1MB 이하여야 합니다.");
        String id = UUID.randomUUID().toString(); ObjectNode data = template.deepCopy();
        data.put("id", id); data.put("title", "과제 초안을 준비하고 있습니다"); data.put("company", actor.name()); data.put("domain", request.jobRole());
        data.put("summary", "기업 검토 후 공개되는 프로젝트입니다."); data.put("applicants", 0);
        data.put("engine", aiMode); data.put("aiProvider", aiMode.equals("demo") ? "demo" : ai.provider());
        data.put("deadline", LocalDate.now(java.time.ZoneId.of("Asia/Seoul")).plusDays(30).toString());
        Project p = new Project(id, actor.id(), data); p.original = request; p.status = "GENERATING"; p.versions.clear();
        store.projects.put(id, p); generation(p, false); store.persist(); return p.view(true);
    }
    private ObjectNode aiRequest(Project p) {
        NewRequest r = p.original; ObjectNode req = mapper.createObjectNode();
        req.put("request_text", r.requestText()); req.putArray("job_roles").add(r.jobRole()); req.put("data_scope", "synthetic_public");
        req.put("generalization", r.generalization().equals("high") ? "high" : "medium");
        var terms = req.putArray("sensitive_terms"); Arrays.stream(r.sensitiveWords().split("[,;\\n]")).map(String::trim).filter(s -> !s.isEmpty()).distinct().forEach(terms::add);
        var docs = req.putArray("documents");
        for (Attachment attachment : r.attachments()) {
            String name = attachment.name().toLowerCase(Locale.ROOT);
            String type = name.endsWith(".pdf") ? "application/pdf" : name.endsWith(".docx") ? "application/vnd.openxmlformats-officedocument.wordprocessingml.document" : "text/plain";
            docs.addObject().put("filename", attachment.name()).put("media_type", type).put("content_base64", attachment.contentBase64());
        }
        req.set("clarifications", p.privateData.has("clarifications") ? p.privateData.get("clarifications").deepCopy() : mapper.createArrayNode());
        return req;
    }
    private void generation(Project p, boolean revision) {
        p.status = "GENERATING"; p.error = "";
        ObjectNode payload = mapper.createObjectNode().set("request", aiRequest(p));
        if (revision && p.privateData.has("aiDraft")) { payload.set("draft", p.privateData.get("aiDraft").deepCopy()); payload.put("feedback", p.feedback); }
        p.jobId = enqueue(p.ownerId, "GENERATE", () -> {
            if (aiMode.equals("demo")) { Thread.sleep(delayMs); return mapper.createObjectNode(); }
            if (!revision && payload.path("request").path("clarifications").isEmpty()) {
                JsonNode questions = ai.invoke("clarify", payload, p.ownerId, p.id);
                if (questions.isArray() && !questions.isEmpty()) return mapper.createObjectNode().set("questions", questions);
            }
            return ai.invoke(payload.has("draft") ? "revise" : "generate", payload, p.ownerId, p.id);
        }, result -> {
            if (result.has("questions")) { p.privateData.set("clarifyingQuestions", result.get("questions")); p.status = "NEEDS_CLARIFICATION"; return; }
            if (!aiMode.equals("demo")) {
                JsonNode draft = result.path("draft");
                if (!draft.hasNonNull("title") || !draft.path("tasks").isArray() || draft.path("tasks").size() != 3 || !draft.path("dataset").hasNonNull("csv")) throw new IllegalStateException("AI draft shape invalid");
                p.privateData.set("aiDraft", draft.deepCopy()); p.privateData.set("leakReport", result.path("leak_report").deepCopy());
                p.publicData.put("title", draft.path("title").asText()); p.publicData.put("summary", draft.path("summary").asText());
                p.publicData.set("tasks", draft.get("tasks").deepCopy()); p.publicData.put("dataset", draft.path("dataset").path("csv").asText());
                p.publicData.set("domainTags", draft.path("domain_tags").deepCopy());
                Set<String> skills = new LinkedHashSet<>(); draft.path("tasks").forEach(t -> t.path("skills").forEach(s -> skills.add(s.asText()))); p.publicData.set("skills", mapper.valueToTree(skills));
            } else { p.publicData.put("title", "데이터 실무 프로젝트"); p.publicData.put("summary", "데이터를 정제하고 결과를 재현 가능한 산출물로 만드는 예시 과제입니다."); }
            JsonNode checked = p.privateData.has("aiDraft") ? p.privateData.get("aiDraft") : p.publicData;
            p.privateData.set("disclosure", scanner.scan(checked, p.original.sensitiveWords(), p.privateData.get("leakReport")));
            p.status = "DRAFT"; p.versions.put(p.revision, p.publicData.deepCopy());
        }, message -> { p.status = "FAILED"; p.error = message; });
    }
    synchronized ObjectNode clarify(Actor actor, String id, Answers input) {
        Project p = ownedProject(actor, id); if (!p.status.equals("NEEDS_CLARIFICATION")) throw invalid("추가 질문에 답변할 수 있는 단계가 아닙니다.");
        JsonNode questions = p.privateData.path("clarifyingQuestions"); if (input.answers().size() != questions.size()) throw invalid("모든 추가 질문에 답변해 주세요.");
        ArrayNode clarifications = p.privateData.putArray("clarifications"); for (int i=0; i<questions.size(); i++) clarifications.addObject().put("question", questions.get(i).path("question").asText()).put("answer", input.answers().get(i));
        generation(p, false); store.persist(); return p.view(true);
    }
    synchronized ObjectNode revise(Actor actor, String id, String feedback) { Project p = ownedProject(actor, id); if (!p.status.equals("DRAFT")) throw invalid("초안 상태에서만 수정할 수 있습니다."); if (p.original == null) throw invalid("샘플 프로젝트는 수정할 수 없습니다."); p.feedback = feedback; p.revision++; generation(p, true); store.persist(); return p.view(true); }
    synchronized ObjectNode retry(Actor actor, String id) { Project p = ownedProject(actor, id); if (!p.status.equals("FAILED") || p.original == null) throw invalid("실패한 생성 작업만 재시도할 수 있습니다."); generation(p, p.privateData.has("aiDraft")); store.persist(); return p.view(true); }
    synchronized ObjectNode publish(Actor actor, String id) { Project p = ownedProject(actor, id); if (!p.status.equals("DRAFT")) throw invalid("검토할 수 있는 초안이 아닙니다."); if (p.privateData.path("disclosure").path("status").asText().equals("blocked")) throw invalid("민감 정보 유출 검사에 실패해 공개할 수 없습니다. 초안을 수정해 주세요."); p.status = "PUBLISHED"; store.persist(); return p.view(true); }
    synchronized ObjectNode close(Actor actor, String id) { Project p = ownedProject(actor, id); if (!p.status.equals("PUBLISHED")) throw invalid("공개된 프로젝트만 모집을 마감할 수 있습니다."); p.status = "CLOSED"; store.persist(); return p.view(true); }
    synchronized List<ObjectNode> applications(Actor actor) { return store.applications.values().stream().filter(a -> a.ownerId.equals(actor.id())).map(Application::view).toList(); }
    synchronized List<ObjectNode> companySubmissions(Actor actor) { return store.applications.values().stream().filter(a -> project(a.projectId).ownerId.equals(actor.id()) && List.of("REVIEW", "FINALIZED").contains(a.status)).map(Application::view).toList(); }
    synchronized ObjectNode getApplication(Actor actor, String id) { return application(actor, id).view(); }
    synchronized ObjectNode companySubmission(Actor actor, String id) { return companyApplication(actor, id).view(); }
    synchronized ObjectNode apply(Actor actor, Apply input) {
        Project p = project(input.projectId()); if (!p.status.equals("PUBLISHED")) throw invalid("공개된 프로젝트만 신청할 수 있습니다.");
        if (p.publicData.path("tasks").findValuesAsText("difficulty").stream().noneMatch(input.difficulty().name()::equals)) throw invalid("제공되지 않는 과제 난이도입니다.");
        for (Application a : store.applications.values()) if (a.ownerId.equals(actor.id()) && a.projectId.equals(p.id)) return a.view();
        if (store.applications.size() >= 500) throw new ResponseStatusException(HttpStatus.TOO_MANY_REQUESTS, "신청 한도에 도달했습니다.");
        Application a = new Application(UUID.randomUUID().toString(), actor.id(), p.id, input.difficulty(), mapper); store.applications.put(a.id, a);
        p.publicData.put("applicants", p.publicData.path("applicants").asInt() + 1); store.persist(); return a.view();
    }
    private void validateFiles(Work work) {
        int chars = 0;
        for (var entry : work.files().entrySet()) { if (!FILE_NAME.matcher(entry.getKey()).matches()) throw invalid("지원하지 않는 파일 형식이거나 잘못된 파일명입니다."); chars += entry.getValue().length(); }
        if (chars > 200000) throw invalid("전체 제출물은 200,000자 이하여야 합니다.");
    }
    synchronized ObjectNode save(Actor actor, String id, Work work, boolean submit) {
        Application a = application(actor, id); if (!a.status.equals("WORKING")) throw invalid("제출 후에는 수정할 수 없습니다."); validateFiles(work);
        if (submit && (work.files().isEmpty() || work.files().values().stream().anyMatch(String::isBlank) || work.process().trim().length() < 20 || work.references().isBlank() || work.aiUsage().isBlank())) throw invalid("파일, 과정 기록(20자 이상), 참고자료, AI 사용 공개가 필요합니다.");
        a.data.set("files", mapper.valueToTree(work.files())); a.data.put("process", work.process()); a.data.put("references", work.references()); a.data.put("aiUsage", work.aiUsage()); a.data.remove("error");
        if (submit) {
            if (aiMode.equals("demo")) { templateQuestions(a); a.status = "FOLLOWUP"; }
            else {
                a.status = "QUESTIONING"; ObjectNode payload = submissionPayload(a);
                enqueue(a.ownerId, "FOLLOWUP", () -> ai.invoke("followup", payload, a.ownerId, a.projectId), result -> {
                    if (result.isArray() && !result.isEmpty()) {
                        ArrayNode questions = a.data.putArray("questions"); ArrayNode ids = a.data.putArray("questionIds");
                        for (JsonNode q : result) { if (questions.size() >= 3) break; if (q.path("question").asText().isBlank()) continue; questions.add(q.path("question").asText()); ids.add(q.path("id").asText()); }
                        if (questions.isEmpty()) templateQuestions(a); else a.data.put("questionSource", "ai");
                    } else templateQuestions(a);
                    a.status = "FOLLOWUP";
                }, message -> { a.status = "WORKING"; a.data.put("error", message); });
            }
        }
        store.persist(); return a.view();
    }
    private void templateQuestions(Application a) {
        a.data.putArray("questions").add("제출 파일에서 가장 중요한 설계 선택과 그 이유를 설명해 주세요.").add("다른 입력이나 예외 상황에서 결과를 어떻게 검증했나요?").add("AI 또는 참고자료를 활용한 부분과 직접 검증한 부분을 구분해 주세요.");
        a.data.putArray("questionIds").add("app-q1").add("app-q2").add("app-q3"); a.data.put("questionSource", "template");
    }
    private ObjectNode submissionPayload(Application a) {
        Project p = project(a.projectId); ObjectNode payload = mapper.createObjectNode();
        JsonNode task = p.publicData.path("tasks").findParents("difficulty").stream().filter(t -> t.path("difficulty").asText().equals(a.difficulty.name())).findFirst().orElseThrow();
        ObjectNode normalized = ((ObjectNode) task).deepCopy(); if (!normalized.has("scope")) normalized.put("scope", "공개된 합성 데이터만 사용합니다.");
        if (!normalized.has("rubric")) normalized.putArray("rubric").addObject().put("criterion", "요구사항 충족").put("description", "과제 목표를 충족하는 근거를 제시합니다.").put("auto_checkable", false);
        if (!normalized.has("tests")) normalized.putArray("tests").addObject().put("id", "manual-review").put("description", "기업의 결과물 확인").put("kind", "manual");
        payload.set("task", normalized);
        if (p.privateData.path("aiDraft").has("dataset")) payload.set("dataset", p.privateData.path("aiDraft").get("dataset").deepCopy());
        else { ObjectNode dataset = payload.putObject("dataset"); dataset.put("filename", "sample_data.csv"); dataset.put("csv", p.publicData.path("dataset").asText()); dataset.put("seed", 0); dataset.putArray("columns"); }
        ObjectNode submission = payload.putObject("submission"); submission.set("files", a.data.path("files").deepCopy()); submission.put("ai_usage", a.data.path("aiUsage").asText());
        submission.putArray("references").addObject().put("kind", "document").put("title", "참고자료 목록").put("note", a.data.path("references").asText());
        submission.putArray("process_log").addObject().put("question", "문제 이해, 접근, 시도와 검증 과정").put("answer", a.data.path("process").asText());
        ArrayNode answers = submission.putArray("followup_answers"); JsonNode questions = a.data.path("questions");
        for (int i=0; i<questions.size(); i++) { String answer = a.data.path("answers").path(i).asText(); if (!answer.isBlank()) answers.addObject().put("question_id", a.data.path("questionIds").path(i).asText("q"+i)).put("question", questions.get(i).asText()).put("answer", answer); }
        return payload;
    }
    synchronized ObjectNode answer(Actor actor, String id, Answers input) {
        Application a = application(actor, id); if (!a.status.equals("FOLLOWUP")) throw invalid("후속 질문 단계에서만 답변할 수 있습니다.");
        if (input.answers().size() != a.data.path("questions").size() || input.answers().stream().anyMatch(s -> s.trim().length() < 10)) throw invalid("모든 질문에 10자 이상 답변해 주세요.");
        a.data.set("answers", mapper.valueToTree(input.answers())); a.data.remove("error"); a.status = "EVALUATING"; ObjectNode payload = submissionPayload(a);
        enqueue(a.ownerId, "EVALUATE", () -> {
            if (aiMode.equals("demo")) { Thread.sleep(delayMs); return mapper.createObjectNode(); }
            return ai.invoke("evaluate", payload, a.ownerId, a.projectId);
        }, result -> {
            ObjectNode evaluation = a.data.putObject("evaluation"); boolean demo = aiMode.equals("demo") || ai.provider().equals("fake");
            evaluation.put("demo", demo); evaluation.put("source", aiMode); evaluation.put("summary", result.path("ai_summary").asText("개발용 평가입니다. 실제 코드 실행과 LLM 평가는 수행하지 않았습니다."));
            ArrayNode criteria = evaluation.putArray("criteria");
            if (result.path("ai_review").isArray()) for (JsonNode c : result.get("ai_review")) criteria.addObject().put("name", c.path("criterion").asText()).put("status", demo ? "unverified" : c.path("status").asText("unverified")).put("comment", c.path("comment").asText());
            else for (String name : List.of("집계 정확성", "요구사항 충족", "재현 가능성")) criteria.addObject().put("name", name).put("status", "unverified").put("comment", "실제 평가 연동 전 · 기업 확인 필요");
            ArrayNode tests = evaluation.putArray("tests");
            for (JsonNode t : result.path("test_results")) { ObjectNode row = tests.addObject().put("testId", t.path("test_id").asText()).put("detail", t.path("detail").asText()); if (t.path("passed").isBoolean()) row.put("passed", t.get("passed").asBoolean()); else row.putNull("passed"); }
            evaluation.set("improvements", result.path("improvements").isArray() ? result.get("improvements").deepCopy() : mapper.createArrayNode()); a.status = "REVIEW";
        }, message -> { a.status = "FOLLOWUP"; a.data.put("error", message); });
        store.persist(); return a.view();
    }
    synchronized ObjectNode finalizeReport(Actor actor, String id, String feedback) { Application a = companyApplication(actor, id); if (!a.status.equals("REVIEW")) throw invalid("기업 검토 상태에서만 확정할 수 있습니다."); if (feedback.trim().length() < 10) throw invalid("피드백은 10자 이상 작성해 주세요."); a.data.put("feedback", feedback); a.status = "FINALIZED"; store.persist(); return a.view(); }
    synchronized ObjectNode portfolio(Actor actor, String id) { Application a = application(actor, id); if (!a.status.equals("FINALIZED")) throw invalid("확정된 리포트만 포트폴리오에 추가할 수 있습니다."); a.data.put("portfolio", true); store.persist(); return a.view(); }
    synchronized ObjectNode job(Actor actor, String id) { ObjectNode job = store.jobs.get(id); if (job == null || !job.path("ownerId").asText().equals(actor.id())) throw new ResponseStatusException(HttpStatus.NOT_FOUND, "작업을 찾을 수 없습니다."); ObjectNode view = job.deepCopy(); view.remove("ownerId"); return view; }
    private String enqueue(String ownerId, String kind, Callable<JsonNode> work, Consumer<JsonNode> success, Consumer<String> failure) {
        String id = UUID.randomUUID().toString(); ObjectNode job = mapper.createObjectNode().put("id", id).put("ownerId", ownerId).put("kind", kind).put("status", "QUEUED").put("demo", aiMode.equals("demo") || ai.provider().equals("fake"));
        if (store.jobs.size() >= 500) store.jobs.entrySet().removeIf(e -> List.of("SUCCEEDED", "FAILED").contains(e.getValue().path("status").asText()));
        store.jobs.put(id, job);
        try { workers.execute(() -> {
            synchronized (this) { job.put("status", "RUNNING"); store.persist(); }
            try { JsonNode result = work.call(); synchronized (this) { success.accept(result); job.put("status", "SUCCEEDED"); store.persist(); } }
            catch (Exception e) { synchronized (this) { String message = e instanceof PythonAiGateway.AiCallException ? e.getMessage() : "작업에 실패했습니다. 잠시 후 다시 시도해 주세요."; failure.accept(message); job.put("status", "FAILED").put("error", message); store.persist(); } if (e instanceof InterruptedException) Thread.currentThread().interrupt(); }
        }); }
        catch (RejectedExecutionException e) { failure.accept("작업 대기열이 가득 찼습니다. 잠시 후 다시 시도해 주세요."); job.put("status", "FAILED").put("error", "작업 대기열이 가득 찼습니다."); }
        return id;
    }
    @PreDestroy void shutdown() { workers.shutdownNow(); }
}
