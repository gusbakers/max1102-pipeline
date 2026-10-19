CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS week5_knowledge;
CREATE TABLE IF NOT EXISTS week5_knowledge.chunks (
    collection text NOT NULL,
    chunk_id text NOT NULL,
    source text NOT NULL,
    title text NOT NULL,
    content text NOT NULL CHECK (length(content) BETWEEN 1 AND 1200),
    content_hash text NOT NULL,
    embedding_model text NOT NULL,
    embedding vector(768) NOT NULL,
    indexed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (collection, chunk_id)
);
-- Exact cosine search is deliberate for the small pilot corpus; no ANN tuning claims.
CREATE INDEX IF NOT EXISTS knowledge_collection_model ON week5_knowledge.chunks (collection, embedding_model);

CREATE SCHEMA IF NOT EXISTS week5_stream;
CREATE TABLE IF NOT EXISTS week5_stream.events (
    event_id uuid PRIMARY KEY,
    claim_id text NOT NULL,
    occurred_at timestamptz NOT NULL,
    payload jsonb NOT NULL,
    payload_hash text NOT NULL,
    received_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS week5_stream.rejections (
    topic text NOT NULL,
    partition_id integer NOT NULL,
    offset_id bigint NOT NULL,
    reason text NOT NULL,
    payload_hash text NOT NULL,
    rejected_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (topic, partition_id, offset_id)
);
