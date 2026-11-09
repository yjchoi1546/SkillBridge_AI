package com.skillbridge;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.util.ContentCachingResponseWrapper;

/** Never serve mutable, uncommitted workspace state after a durable write failure. */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 20)
class WorkspaceAvailabilityFilter extends OncePerRequestFilter {
    private final DemoRepository repository;
    WorkspaceAvailabilityFilter(DemoRepository repository) { this.repository = repository; }

    @Override protected boolean shouldNotFilter(HttpServletRequest request) {
        String path = request.getRequestURI().substring(request.getContextPath().length());
        return !(path.equals("/api/projects") || path.startsWith("/api/projects/")
            || path.startsWith("/api/company/") || path.equals("/api/applications")
            || path.startsWith("/api/applications/") || path.startsWith("/api/jobs/"));
    }

    private void unavailable(HttpServletResponse response) throws IOException {
        response.reset();
        response.setStatus(HttpServletResponse.SC_SERVICE_UNAVAILABLE);
        response.setHeader("Cache-Control", "no-store");
        response.setHeader("X-Content-Type-Options", "nosniff");
        response.setContentType("application/json");
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        response.getWriter().write("{\"message\":\"저장소 오류로 워크스페이스를 잠시 사용할 수 없습니다. 서버 관리자에게 문의해 주세요.\"}");
    }

    @Override protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                            FilterChain chain) throws ServletException, IOException {
        if (!repository.isAvailable()) { unavailable(response); return; }
        ContentCachingResponseWrapper buffered = new ContentCachingResponseWrapper(response);
        try {
            chain.doFilter(request, buffered);
        } finally {
            // A write may have failed while this request waited for the workspace lock.
            if (!repository.isAvailable()) unavailable(buffered);
            buffered.copyBodyToResponse();
        }
    }
}
