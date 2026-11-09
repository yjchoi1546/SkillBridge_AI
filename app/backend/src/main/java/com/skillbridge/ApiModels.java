package com.skillbridge;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.util.List;
import java.util.Map;

final class ApiModels {
    private ApiModels() {}
    enum Role { PERSON, COMPANY }
    enum Difficulty { beginner, intermediate, advanced }
    record DemoLogin(@NotNull Role role) {}
    record Session(String token, String name, Role role) {}
    record Actor(String id, String name, Role role) {}
    record Attachment(@NotBlank @Size(max=150) String name, @NotBlank @Size(max=1000000) String contentBase64) {}
    record NewRequest(
        @NotBlank @Size(min=20, max=10000) String requestText,
        @NotBlank @Size(max=50) String jobRole,
        @NotNull @Size(max=1000) String sensitiveWords,
        @Pattern(regexp="standard|high") @NotNull String generalization,
        @NotNull @Size(max=3) List<@Valid Attachment> attachments) {}
    record Feedback(@NotBlank @Size(min=5, max=5000) String feedback) {}
    record Apply(@NotBlank String projectId, @NotNull Difficulty difficulty) {}
    record Work(
        @NotNull @Size(max=12) Map<@NotBlank @Size(max=150) String, @NotNull String> files,
        @NotNull @Size(max=15000) String process,
        @NotNull @Size(max=5000) String references,
        @NotNull @Size(max=5000) String aiUsage) {}
    record Answers(@NotNull @Size(min=1, max=10) List<@NotBlank @Size(min=10, max=3000) String> answers) {}
}
