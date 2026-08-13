-- Admin API schema additions
-- Applied idempotently at startup

-- person_identities: typed identity mappings (replaces flat telegram_id column on people)
CREATE TABLE IF NOT EXISTS person_identities (
    id                serial PRIMARY KEY,
    person_id         int NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    identity_type     text NOT NULL,  -- telegram, email, phone, discord
    identity_value    text NOT NULL,
    normalized_value  text NOT NULL,
    is_primary        boolean NOT NULL DEFAULT false,
    created_at        timestamptz NOT NULL DEFAULT now(),
    UNIQUE (identity_type, normalized_value)
);

CREATE INDEX IF NOT EXISTS person_identities_person_id ON person_identities (person_id);
CREATE INDEX IF NOT EXISTS person_identities_lookup ON person_identities (identity_type, normalized_value);

-- Seed existing telegram_id values into person_identities
INSERT INTO person_identities (person_id, identity_type, identity_value, normalized_value, is_primary)
SELECT id, 'telegram', telegram_id, telegram_id, true
FROM people
WHERE telegram_id IS NOT NULL
ON CONFLICT (identity_type, normalized_value) DO NOTHING;

-- work_items: add fields the spec requires
ALTER TABLE work_items ADD COLUMN IF NOT EXISTS current_stage text;
ALTER TABLE work_items ADD COLUMN IF NOT EXISTS waiting_reason text;
ALTER TABLE work_items ADD COLUMN IF NOT EXISTS payload jsonb;
ALTER TABLE work_items ADD COLUMN IF NOT EXISTS completed_at timestamptz;

-- requests: add provider field for future multi-provider channels
ALTER TABLE requests ADD COLUMN IF NOT EXISTS provider text;

-- people: per-person timezone (IANA, e.g. America/New_York). NULL => inherits the
-- org default_timezone (admin_settings), which itself falls back to UTC.
ALTER TABLE people ADD COLUMN IF NOT EXISTS timezone text;

-- Soft delete (story-20): NULL = active, timestamp = deleted. No admin action ever
-- issues DELETE FROM a data entity; "delete" sets this, and rows are restorable.
ALTER TABLE people ADD COLUMN IF NOT EXISTS deleted_at timestamptz;

-- admin_sessions table for FastAPI admin login
CREATE TABLE IF NOT EXISTS admin_sessions (
    id          text PRIMARY KEY,
    person_id   int REFERENCES people(id) ON DELETE CASCADE,
    email       text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    expires_at  timestamptz NOT NULL,
    last_seen   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS admin_sessions_expires ON admin_sessions (expires_at);

-- Tool context tokens: short-lived opaque tokens passed to MCP tools.
-- Raw token is given once (in system_message to Hermes); only the hash is stored.
-- MCP servers call GET /api/tool-contexts/{token} to resolve request context.
CREATE TABLE IF NOT EXISTS tool_contexts (
    id            serial PRIMARY KEY,
    token_hash    text NOT NULL UNIQUE,
    request_id    text,
    person_id     int REFERENCES people(id),
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
