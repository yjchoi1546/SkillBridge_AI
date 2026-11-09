package com.skillbridge;

import jakarta.servlet.*;
import jakarta.servlet.http.*;
import java.io.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

@Component
class RequestBoundary extends OncePerRequestFilter {
    private final int maxBytes;
    RequestBoundary(@Value("${skillbridge.max-request-bytes:2100000}") int maxBytes) { this.maxBytes = maxBytes; }
    @Override protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain) throws ServletException, IOException {
        response.setHeader("Cache-Control", "no-store"); response.setHeader("X-Content-Type-Options", "nosniff"); response.setHeader("Referrer-Policy", "same-origin");
        if (!request.getRequestURI().startsWith("/api/") || !java.util.List.of("POST", "PUT", "PATCH").contains(request.getMethod())) { chain.doFilter(request, response); return; }
        byte[] body = request.getInputStream().readNBytes(maxBytes + 1);
        if (body.length > maxBytes) { response.setStatus(413); response.setContentType("application/json;charset=UTF-8"); response.getWriter().write("{\"message\":\"요청 크기 제한을 초과했습니다.\"}"); return; }
        HttpServletRequestWrapper wrapped = new HttpServletRequestWrapper(request) {
            @Override public ServletInputStream getInputStream() {
                ByteArrayInputStream source = new ByteArrayInputStream(body);
                return new ServletInputStream() {
                    @Override public int read() { return source.read(); }
                    @Override public int read(byte[] bytes, int offset, int length) { return source.read(bytes, offset, length); }
                    @Override public boolean isFinished() { return source.available() == 0; }
                    @Override public boolean isReady() { return true; }
                    @Override public void setReadListener(ReadListener listener) { throw new UnsupportedOperationException("Synchronous API input only"); }
                };
            }
            @Override public BufferedReader getReader() { return new BufferedReader(new InputStreamReader(getInputStream(), java.nio.charset.StandardCharsets.UTF_8)); }
        };
        chain.doFilter(wrapped, response);
    }
}
