package com.skillbridge;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import java.util.concurrent.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/** Fixed trusted argv. Executable paths and module names never come from HTTP input. */
@Component
class PythonAiGateway {
    private final ObjectMapper mapper;
    private final Path root;
    private final String command, provider;
    private final int timeoutSeconds;
    PythonAiGateway(ObjectMapper mapper,
                    @Value("${skillbridge.ai.repository-root:../..}") String root,
                    @Value("${skillbridge.ai.python-command:uv}") String command,
                    @Value("${skillbridge.ai.provider:fake}") String provider,
                    @Value("${skillbridge.ai.timeout-seconds:240}") int timeoutSeconds) {
        this.mapper = mapper; this.root = Path.of(root).toAbsolutePath().normalize();
        this.command = command; this.provider = provider; this.timeoutSeconds = timeoutSeconds;
    }
    String provider() { return provider; }
    JsonNode invoke(String operation, JsonNode payload, String ownerId, String projectId) {
        List<String> args = command.equals("uv") || command.endsWith("uv.exe")
            ? List.of(command, "run", "--frozen", "--no-sync", "python", "-m", "app.backend.ai_bridge")
            : List.of(command, "-m", "app.backend.ai_bridge");
        Process process = null;
        ExecutorService io = Executors.newVirtualThreadPerTaskExecutor();
        try {
            ProcessBuilder builder = new ProcessBuilder(args).directory(root.toFile()).redirectError(ProcessBuilder.Redirect.DISCARD);
            builder.environment().put("PYTHONIOENCODING", "utf-8");
            builder.environment().put("UV_CACHE_DIR", root.resolve("app/.cache/uv").toString());
            builder.environment().put("UV_PYTHON_INSTALL_DIR", root.resolve("app/.tools/python").toString());
            builder.environment().put("UV_PROJECT_ENVIRONMENT", root.resolve("app/.tools/ai-venv").toString());
            builder.environment().put("LLM_PROVIDER", provider);
            if (provider.equals("fake")) {
                builder.environment().put("LANGFUSE_TRACING_ENABLED", "false");
                builder.environment().put("GENERATION_LLM_PROVIDER", "fake");
                builder.environment().put("EVALUATION_LLM_PROVIDER", "fake");
            }
            byte[] input = mapper.writeValueAsBytes(Map.of("operation", operation, "payload", payload, "user_id", ownerId, "session_id", projectId));
            if (input.length > 2_100_000) throw new AiCallException("AI 입력 크기 제한을 초과했습니다.");
            process = builder.start(); Process started = process;
            Future<?> writer = io.submit(() -> { try (var stream = started.getOutputStream()) { stream.write(input); } catch (IOException e) { throw new CompletionException(e); } });
            Future<byte[]> reader = io.submit(() -> {
                byte[] output = started.getInputStream().readNBytes(3_000_001);
                if (output.length > 3_000_000) { stop(started); throw new IOException("AI output too large"); }
                return output;
            });
            if (!process.waitFor(timeoutSeconds, TimeUnit.SECONDS)) {
                stop(process); throw new AiCallException("AI 실행 제한 시간을 초과했습니다. 잠시 후 다시 시도해 주세요.");
            }
            writer.get(5, TimeUnit.SECONDS);
            JsonNode response = mapper.readTree(reader.get(5, TimeUnit.SECONDS));
            if (response == null || !response.path("ok").asBoolean()) {
                String category = response == null ? "" : response.path("error").asText();
                throw new AiCallException(switch (category) {
                    case "ConfigError" -> "AI 공급자·모델·API 키 설정이 필요합니다. 개발 중에는 LLM_PROVIDER=fake를 사용하세요.";
                    case "ModuleNotFoundError", "ImportError" -> "AI Python 의존성을 설치해 주세요. app/scripts/setup-ai.ps1을 실행하세요.";
                    case "PydanticSerializationError", "UnicodeDecodeError" -> "첨부 문서를 현재 AI 모듈이 처리하지 못했습니다. 텍스트로 변환하거나 첨부 없이 다시 요청해 주세요.";
                    default -> "AI 처리에 실패했습니다. 요청과 AI 연결 설정을 확인하고 다시 시도해 주세요.";
                });
            }
            if (process.exitValue() != 0) throw new AiCallException("AI 프로세스가 정상적으로 완료되지 않았습니다.");
            if (!response.hasNonNull("result")) throw new AiCallException("AI 응답에 결과가 없습니다.");
            return response.get("result");
        } catch (AiCallException e) { throw e; }
        catch (InterruptedException e) { Thread.currentThread().interrupt(); throw new AiCallException("서버 종료로 AI 작업이 중단되었습니다."); }
        catch (Exception e) { throw new AiCallException("Python AI 실행 환경을 확인해 주세요. app/scripts/setup-ai.ps1로 설치할 수 있습니다."); }
        finally { if (process != null && process.isAlive()) stop(process); io.shutdownNow(); }
    }
    private void stop(Process process) {
        process.descendants().forEach(ProcessHandle::destroyForcibly); process.destroyForcibly();
        try { process.getInputStream().close(); process.getOutputStream().close(); } catch (IOException ignored) { }
    }
    static class AiCallException extends RuntimeException { AiCallException(String message) { super(message); } }
}
