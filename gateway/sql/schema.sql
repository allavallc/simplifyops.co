-- Durable workflow schema for SimplifyOps gateway
-- Applied idempotently at gateway startup via apply_schema()

CREATE TABLE IF NOT EXISTS requests (
    id          text PRIMARY KEY,
    channel     text NOT NULL,
    from_id     text NOT NULL,
    from_name   text,
    chat_id     text NOT NULL,
    message_text text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- Provider-level idempotency: one row per (channel, provider_event_id)
CREATE TABLE IF NOT EXISTS channel_events (
    id                serial PRIMARY KEY,
    channel           text NOT NULL,
    provider_event_id text NOT NULL,
    request_id        text REFERENCES requests(id),
    created_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (channel, provider_event_id)
);

-- Dead-letter sink: inbound updates that intake terminally rejected (HTTP 422 /
-- unprocessable) or that we chose not to retry. Nothing is silently dropped —
-- these are inspectable and can surface in admin Inbox/Activity later.
CREATE TABLE IF NOT EXISTS channel_dead_letter (
    id                serial PRIMARY KEY,
    channel           text NOT NULL,
    provider_event_id text,
    reason            text NOT NULL,
    raw_update        jsonb NOT NULL,
    created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS work_items (
    id            serial PRIMARY KEY,
    request_id    text NOT NULL REFERENCES requests(id),
    status        text NOT NULL DEFAULT 'ready',
    attempt_count int  NOT NULL DEFAULT 0,
    reply_text    text,
    error_summary text,
    locked_until  timestamptz,
    retry_after   timestamptz,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS work_items_claimable
    ON work_items (status, retry_after)
    WHERE status IN ('ready', 'failed_retryable', 'reply_ready');

-- Per-user conversation history (audit log — context now owned by Hermes sessions)
CREATE TABLE IF NOT EXISTS session_history (
    id            serial PRIMARY KEY,
    user_id       text NOT NULL,
    user_msg      text NOT NULL,
    assistant_msg text NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS session_history_user_created
    ON session_history (user_id, created_at);

-- Maps each logical conversation to the current physical Hermes session.
-- logical_session_id is stable for the conversation (e.g. telegram:{from_id}).
-- hermes_session_id is the current physical session, which rotates when caps are hit.
CREATE TABLE IF NOT EXISTS hermes_session_mappings (
    user_id                   text PRIMARY KEY,
    channel                   text NOT NULL,
    logical_session_id        text NOT NULL DEFAULT '',
    hermes_session_id         text NOT NULL,
    physical_rotations        int  NOT NULL DEFAULT 0,
    rotation_reason           text,
    message_count_at_rotation int,
    created_at                timestamptz NOT NULL DEFAULT now(),
    updated_at                timestamptz NOT NULL DEFAULT now()
);

-- Add new columns to existing tables idempotently
ALTER TABLE hermes_session_mappings ADD COLUMN IF NOT EXISTS logical_session_id text NOT NULL DEFAULT '';
ALTER TABLE hermes_session_mappings ADD COLUMN IF NOT EXISTS physical_rotations int NOT NULL DEFAULT 0;
ALTER TABLE hermes_session_mappings ADD COLUMN IF NOT EXISTS rotation_reason text;
ALTER TABLE hermes_session_mappings ADD COLUMN IF NOT EXISTS message_count_at_rotation int;

-- Migrate existing rows: populate logical_session_id from channel + user_id
UPDATE hermes_session_mappings
SET logical_session_id = channel || ':' || user_id
WHERE logical_session_id = '';

-- Tool context tokens (same as admin_api/schema.sql — both services share the DB)
CREATE TABLE IF NOT EXISTS tool_contexts (
    id            serial PRIMARY KEY,
    token_hash    text NOT NULL UNIQUE,
    request_id    text,
    person_id     int,
    authority     text NOT NULL DEFAULT 'member',
    channel       text NOT NULL,
    from_id       text NOT NULL,
    primary_email text,
    timezone      text NOT NULL DEFAULT 'UTC',
    can_influence boolean NOT NULL DEFAULT true,
    expires_at    timestamptz NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS tool_contexts_expires ON tool_contexts (expires_at);

-- Global admin settings (singleton rows keyed by setting name)
CREATE TABLE IF NOT EXISTS admin_settings (
    key        text PRIMARY KEY,
    value      text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    updated_by text
);

-- Seed default session cap if not set
INSERT INTO admin_settings (key, value, updated_by)
VALUES ('session_message_cap', '100', 'system')
ON CONFLICT (key) DO NOTHING;

-- Org-wide default timezone (EST). A person with no timezone inherits this.
INSERT INTO admin_settings (key, value, updated_by)
VALUES ('default_timezone', 'America/New_York', 'system')
ON CONFLICT (key) DO NOTHING;
