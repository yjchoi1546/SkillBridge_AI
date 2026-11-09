CREATE TABLE IF NOT EXISTS accounts (
    user_id VARCHAR(60) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(100) NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('PERSON', 'COMPANY')),
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    token_hash VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(60) NOT NULL REFERENCES accounts(user_id),
    expires_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_expiry ON auth_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id);

-- Initial durable adapter: application-owned snapshots, atomically updated together.
-- Private originals are never read directly by the public DTO endpoints.
CREATE TABLE IF NOT EXISTS workspace_state (
    state_key VARCHAR(50) PRIMARY KEY,
    payload TEXT NOT NULL
);
