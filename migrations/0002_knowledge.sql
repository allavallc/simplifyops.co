-- story-64 Phase A: curated knowledge store (whitelist_app; separate from Hindsight memory).
-- Forward-only, idempotent. gen_random_uuid() is core in PostgreSQL 13+ (no extension needed).

CREATE TABLE IF NOT EXISTS knowledge_documents (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    category          text NOT NULL,
    slug              text NOT NULL UNIQUE,
    title             text NOT NULL,
    content_md        text NOT NULL,
    source_type       text NOT NULL DEFAULT 'admin_created',
    read_only         boolean NOT NULL DEFAULT false,
    status            text NOT NULL DEFAULT 'active'
                          CHECK (status IN ('active', 'archived')),
    minimum_authority text NOT NULL DEFAULT 'admin'
                          CHECK (minimum_authority IN ('contact', 'member', 'admin', 'super_admin')),
    source_path       text UNIQUE,
    sync_state        text NOT NULL DEFAULT 'db_only',
    file_sha          text,
    git_commit_sha    text,
    synced_at         timestamptz,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),
    updated_by        text
);

CREATE TABLE IF NOT EXISTS knowledge_document_versions (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id    uuid NOT NULL REFERENCES knowledge_documents (id) ON DELETE CASCADE,
    version_number integer NOT NULL,
    content_sha256 text NOT NULL,
    content_md     text NOT NULL,
    actor_email    text,
    change_summary text,
    created_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (document_id, version_number)
);

CREATE INDEX IF NOT EXISTS knowledge_documents_category_idx ON knowledge_documents (category);
CREATE INDEX IF NOT EXISTS knowledge_documents_status_idx   ON knowledge_documents (status);
