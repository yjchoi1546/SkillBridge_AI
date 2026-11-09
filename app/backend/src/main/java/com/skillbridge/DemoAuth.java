package com.skillbridge;

import static com.skillbridge.ApiModels.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.Base64;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

/** Persistent account sessions plus an explicitly gated, separate set of development identities. */
@Service
class DemoAuth {
    private record Entry(Actor actor, Instant expires) {}
    private record Account(Actor actor, String passwordHash) {}
    private record FailedLogin(int count, Instant expires) {}
    private final Map<String, Entry> sessions = new ConcurrentHashMap<>();
    private final Map<String, FailedLogin> failedLogins = new ConcurrentHashMap<>();
    private final SecureRandom random = new SecureRandom();
    private final BCryptPasswordEncoder passwords = new BCryptPasswordEncoder(12);
    private final String dummyPasswordHash = passwords.encode("unknown-account-timing-check");
    private final JdbcTemplate jdbc;
    private final boolean enabled;
    DemoAuth(JdbcTemplate jdbc, @Value("${skillbridge.demo-enabled:false}") boolean enabled) { this.jdbc = jdbc; this.enabled = enabled; }

    @Transactional
    public Session register(String email, String password, String name, Role role) {
        validatePassword(password);
        String normalizedEmail = email.strip().toLowerCase(Locale.ROOT);
        String displayName = name.strip();
        if (displayName.length() < 2 || displayName.length() > 100 || displayName.chars().anyMatch(Character::isISOControl)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "이름 또는 기업명을 2~100자로 입력해 주세요.");
        }
        Actor actor = new Actor(UUID.randomUUID().toString(), displayName, role);
        String hash = passwords.encode(password);
        try {
            jdbc.update("INSERT INTO accounts(user_id,email,password_hash,display_name,role,created_at) VALUES(?,?,?,?,?,?)", actor.id(), normalizedEmail, hash, displayName, role.name(), Timestamp.from(Instant.now()));
        } catch (DataIntegrityViolationException e) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "이미 등록된 이메일입니다.");
        }
        return createSession(actor);
    }

    @Transactional
    public Session login(String email, String password) {
        validatePassword(password);
        String normalizedEmail = email.strip().toLowerCase(Locale.ROOT);
        Instant now = Instant.now();
        failedLogins.entrySet().removeIf(e -> !e.getValue().expires().isAfter(now));
        FailedLogin failures = failedLogins.get(normalizedEmail);
        if (failures != null && failures.count() >= 10) throw new ResponseStatusException(HttpStatus.TOO_MANY_REQUESTS, "로그인 시도가 많습니다. 잠시 후 다시 시도해 주세요.");
        List<Account> matches = jdbc.query("SELECT user_id,display_name,role,password_hash FROM accounts WHERE email=?", (rs, row) -> new Account(new Actor(rs.getString("user_id"), rs.getString("display_name"), Role.valueOf(rs.getString("role"))), rs.getString("password_hash")), normalizedEmail);
        Account account = matches.isEmpty() ? null : matches.getFirst();
        boolean valid = passwords.matches(password, account == null ? dummyPasswordHash : account.passwordHash());
        if (account == null || !valid) {
            // Bound the in-process limiter as well as per-account password attempts.
            if (failedLogins.size() >= 10000 && !failedLogins.containsKey(normalizedEmail)) throw new ResponseStatusException(HttpStatus.TOO_MANY_REQUESTS, "로그인 시도가 많습니다. 잠시 후 다시 시도해 주세요.");
            failedLogins.compute(normalizedEmail, (key, old) -> old == null || !old.expires().isAfter(now) ? new FailedLogin(1, now.plusSeconds(900)) : new FailedLogin(old.count() + 1, old.expires()));
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "이메일 또는 비밀번호를 확인해 주세요.");
        }
        failedLogins.remove(normalizedEmail);
        return createSession(account.actor());
    }

    private void validatePassword(String password) {
        if (password == null || password.isBlank() || password.length() < 10 || password.getBytes(StandardCharsets.UTF_8).length > 72) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "비밀번호는 10자 이상, UTF-8 기준 72바이트 이하여야 합니다.");
        }
    }

    private Session createSession(Actor actor) {
        Instant now = Instant.now();
        jdbc.update("DELETE FROM auth_sessions WHERE expires_at<=?", Timestamp.from(now));
        List<String> active = jdbc.query("SELECT token_hash FROM auth_sessions WHERE user_id=? ORDER BY expires_at DESC", (rs, row) -> rs.getString(1), actor.id());
        // A bounded set of sessions per account prevents unbounded token accumulation.
        for (int i = 19; i < active.size(); i++) jdbc.update("DELETE FROM auth_sessions WHERE token_hash=?", active.get(i));
        String token = newToken();
        jdbc.update("INSERT INTO auth_sessions(token_hash,user_id,expires_at) VALUES(?,?,?)", hashToken(token), actor.id(), Timestamp.from(now.plusSeconds(28800)));
        return new Session(token, actor.name(), actor.role());
    }

    private String newToken() {
        byte[] bytes = new byte[32]; random.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    private String hashToken(String token) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(token.getBytes(StandardCharsets.US_ASCII))); }
        catch (NoSuchAlgorithmException impossible) { throw new IllegalStateException("SHA-256 is unavailable", impossible); }
    }

    private String bearer(String authorization) {
        if (authorization == null || !authorization.matches("Bearer [A-Za-z0-9_-]{43}")) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다.");
        return authorization.substring(7);
    }

    public Session me(String authorization) {
        Actor actor = require(authorization, null);
        return new Session(bearer(authorization), actor.name(), actor.role());
    }

    @Transactional
    public void logout(String authorization) {
        String token = bearer(authorization);
        sessions.remove(token);
        jdbc.update("DELETE FROM auth_sessions WHERE token_hash=?", hashToken(token));
    }

    /** Legacy browser demonstration endpoint. Never creates or authenticates a real account. */
    Session login(Role role) {
        if (!enabled) throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "데모 로그인이 비활성화되어 있습니다. 실제 인증 연동이 필요합니다.");
        sessions.entrySet().removeIf(e -> e.getValue().expires().isBefore(Instant.now()));
        if (sessions.size() >= 1000) throw new ResponseStatusException(HttpStatus.TOO_MANY_REQUESTS, "데모 세션 한도를 초과했습니다.");
        String token = newToken();
        Actor actor = new Actor(role == Role.COMPANY ? "company-demo" : "person-demo", role == Role.COMPANY ? "브릿지커머스" : "김브릿지", role);
        sessions.put(token, new Entry(actor, Instant.now().plusSeconds(28800)));
        return new Session(token, actor.name(), role);
    }
    Actor require(String authorization, Role role) {
        String token = bearer(authorization);
        Entry demo = sessions.get(token);
        Actor actor;
        if (enabled && demo != null && demo.expires().isAfter(Instant.now())) actor = demo.actor();
        else {
            List<Actor> found = jdbc.query("SELECT a.user_id,a.display_name,a.role FROM auth_sessions s JOIN accounts a ON a.user_id=s.user_id WHERE s.token_hash=? AND s.expires_at>?", (rs, row) -> new Actor(rs.getString("user_id"), rs.getString("display_name"), Role.valueOf(rs.getString("role"))), hashToken(token), Timestamp.from(Instant.now()));
            if (found.isEmpty()) throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "세션이 만료되었습니다. 다시 로그인해 주세요.");
            actor = found.getFirst();
        }
        if (role != null && role != actor.role()) throw new ResponseStatusException(HttpStatus.FORBIDDEN, "이 회원 유형으로는 접근할 수 없습니다.");
        return actor;
    }
}
