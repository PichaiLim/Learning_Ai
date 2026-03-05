-- ============================================================
-- init.sql — รันอัตโนมัติตอน PostgreSQL container เริ่มต้น
-- ============================================================

-- เปิดใช้งาน pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ตัวอย่าง: สร้างตารางสำหรับเก็บ documents + embeddings
CREATE TABLE IF NOT EXISTS documents (
    id          SERIAL PRIMARY KEY,
    content     TEXT NOT NULL,
    metadata    JSONB DEFAULT '{}',
    embedding   vector(1536),              -- ปรับ dimension ตาม model ที่ใช้
    created_at  TIMESTAMP DEFAULT NOW()
);

-- Index สำหรับ vector similarity search (HNSW - เร็วกว่า IVFFlat)
CREATE INDEX IF NOT EXISTS documents_embedding_idx
    ON documents
    USING hnsw (embedding vector_cosine_ops);

-- ตัวอย่าง: ตารางสำหรับ chat history
CREATE TABLE IF NOT EXISTS chat_sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     TEXT,
    messages    JSONB DEFAULT '[]',
    created_at  TIMESTAMP DEFAULT NOW(),
    updated_at  TIMESTAMP DEFAULT NOW()
);
