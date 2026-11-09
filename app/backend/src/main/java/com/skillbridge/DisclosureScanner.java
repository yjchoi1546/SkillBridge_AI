package com.skillbridge;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.text.Normalizer;
import java.util.ArrayList;
import java.util.Locale;
import java.util.regex.Pattern;
import org.springframework.stereotype.Component;

/** Supplementary rule scan, not a complete deidentification guarantee. */
@Component
class DisclosureScanner {
    private final ObjectMapper mapper;
    private static final Pattern CONTACT = Pattern.compile("[\\w.+-]+@[\\w-]+\\.[\\w.-]+|\\b01[016789][- .]?\\d{3,4}[- .]?\\d{4}\\b|\\b\\d{6}-[1-4]\\d{6}\\b|\\b(?:sk|pk|rk)-[a-z0-9_-]{16,}|\\baiza[a-z0-9_-]{30,}");
    DisclosureScanner(ObjectMapper mapper) { this.mapper = mapper; }
    ObjectNode scan(JsonNode publicDraft, String sensitiveWords, JsonNode aiReport) {
        StringBuilder decoded = new StringBuilder();
        collectText(publicDraft, decoded);
        String text = normalize(decoded.toString());
        var findings = new ArrayList<String>();
        if (text.isBlank()) findings.add("검사할 공개본 내용이 없습니다.");
        for (String raw : (sensitiveWords == null ? "" : sensitiveWords).split("[,;\\n]")) {
            String word = raw.trim(); if (!word.isEmpty() && text.contains(normalize(word))) findings.add("지정 민감 단어가 공개본에 남아 있습니다: " + word);
        }
        if (CONTACT.matcher(text).find()) findings.add("연락처·개인 식별자 또는 키 형태의 표현이 발견되었습니다.");
        if (aiReport != null && aiReport.path("status").asText().equals("failed")) findings.add("AI 모듈의 유출 검사에서 실패했습니다.");
        JsonNode aiFindings = aiReport == null ? null : aiReport.get("findings");
        if (aiFindings != null && !aiFindings.isNull()) {
            if (!aiFindings.isArray()) findings.add("AI 유출 검사 결과의 형식을 확인할 수 없습니다.");
            else if (!aiFindings.isEmpty()) findings.add("AI 유출 검사에서 확인이 필요한 표현이 발견되었습니다.");
        }
        ObjectNode out = mapper.createObjectNode();
        out.put("status", !findings.isEmpty() ? "blocked" : aiReport != null && aiReport.path("status").asText().equals("passed") ? "clear" : "unchecked");
        out.set("findings", mapper.valueToTree(findings)); out.put("ruleScan", findings.isEmpty() ? "passed" : "failed");
        return out;
    }

    private String normalize(String text) {
        return Normalizer.normalize(text, Normalizer.Form.NFKC).toLowerCase(Locale.ROOT);
    }

    /** JsonNode.toString() escapes quotes, tabs and backslashes and can hide literal sensitive terms. */
    private void collectText(JsonNode node, StringBuilder text) {
        if (node == null || node.isNull()) return;
        if (node.isValueNode()) {
            text.append(node.asText()).append('\n');
        } else {
            node.elements().forEachRemaining(child -> collectText(child, text));
        }
    }
}
