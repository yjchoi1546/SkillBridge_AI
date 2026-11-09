package com.skillbridge;

import static org.assertj.core.api.Assertions.*;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.Test;

/** Disclosure checks must never imply successful AI review merely because a local pattern did not match. */
class DisclosureScannerTest {
    private final ObjectMapper mapper = new ObjectMapper();
    private final DisclosureScanner scanner = new DisclosureScanner(mapper);

    private ObjectNode draft(String text) { return mapper.createObjectNode().put("summary", text); }
    private ObjectNode ai(String status) { return mapper.createObjectNode().put("status", status); }
    private void assertBlocked(JsonNode result) {
        assertThat(result.path("status").asText()).isEqualTo("blocked");
        assertThat(result.path("findings").size()).isPositive();
    }

    @Test void cleanRuleScanRemainsUncheckedWithoutExplicitSuccessfulAiReview() {
        ObjectNode publicDraft = draft("합성 데이터로 수행하는 공개 실습 과제입니다.");
        for (JsonNode report : new JsonNode[] {null, ai("not_checked"), ai("unknown"), mapper.createObjectNode()}) {
            ObjectNode result = scanner.scan(publicDraft, "", report);
            assertThat(result.path("status").asText()).isEqualTo("unchecked");
            assertThat(result.path("ruleScan").asText()).isEqualTo("passed");
        }
        assertThat(scanner.scan(publicDraft, "", ai("passed")).path("status").asText()).isEqualTo("clear");
    }

    @Test void sensitiveTermsAreCaseInsensitiveAndCheckedInsideNestedPublicContent() {
        ObjectNode publicDraft = draft("일반 업무 과제");
        publicDraft.putArray("tasks").addObject().put("goal", "검증 시 ClientCode-X를 사용합니다.");
        publicDraft.putObject("dataset").put("csv", "id,value\n1,SECRET_BRANCH\n");
        assertBlocked(scanner.scan(publicDraft, "  clientcode-x ;\n secret_branch  ,", ai("passed")));
        assertThat(scanner.scan(publicDraft, "CLIENTCODE-X", null).path("ruleScan").asText()).isEqualTo("failed");
    }

    @Test void knownContactAndIdentifierFormatsOverridePassedAiReview() {
        for (String text : new String[] {
            "문의: developer@example.test", "휴대폰 010-1234-5678", "휴대폰 011 123 4567",
            "식별자 900101-1234567", "token sk-ABCDEFGHIJKLMNOP1234567890",
            "token PK-ABCDEFGHIJKLMNOP1234567890", "token rk-ABCDEFGHIJKLMNOP1234567890"
        }) {
            assertBlocked(scanner.scan(draft(text), "", ai("passed")));
        }
    }

    @Test void benignSyntheticDataDoesNotBecomeBlockedByOrdinaryDatesAndIds() {
        ObjectNode publicDraft = draft("date,branch,sales\n2026-11-08,branch_A,1240000\n2026-11-09,branch_B,980000\n");
        ObjectNode result = scanner.scan(publicDraft, " , ; \n", ai("passed"));
        assertThat(result.path("status").asText()).isEqualTo("clear");
        assertThat(result.path("findings").isEmpty()).isTrue();
    }

    @Test void failedAiReviewBlocksAnOtherwiseCleanPublicDraft() {
        ObjectNode result = scanner.scan(draft("합성 데이터만 포함합니다."), "", ai("failed"));
        assertBlocked(result);
        assertThat(result.path("findings").toString()).contains("AI");
    }

    @Test void sensitiveTermsContainingJsonEscapesCannotReceiveFalseClear() {
        for (String term : new String[] {"ACME \"LAB\"", "client\\private", "tab\tclient"}) {
            assertBlocked(scanner.scan(draft("비공개 식별자 " + term + " 를 포함합니다."), term, ai("passed")));
        }
    }

    @Test void contradictoryAiReportWithFindingsCannotReceiveFalseClear() {
        ObjectNode report = ai("passed");
        report.putArray("findings").addObject().put("text", "비공개 고유명사").put("location", "summary").put("source", "proper_noun");
        ObjectNode result = scanner.scan(draft("일반화된 업무 과제"), "", report);
        assertThat(result.path("status").asText()).isNotEqualTo("clear");
        assertThat(result.path("status").asText()).isIn("blocked", "unchecked");
    }
}
