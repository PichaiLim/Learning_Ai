# vector_store.py
# ---------------------------------------
# Read embeddings.jsonl -> upsert into PostgreSQL (pgvector)
#
# Input (from embedding.py):
#   <doc_dir>/embeddings/embeddings.jsonl
#
# Output:
#   Data stored in PostgreSQL table: rag_chunks
#
# Requirements:
#   pip install psycopg[binary] pgvector
#
# Usage:
#   python vector_store.py --doc-dir "PATH_TO/data/raw/<doc_id>" --db-url "postgresql://user:pass@localhost:5432/dbname"
#
# Notes:
# - ต้องติดตั้ง extension pgvector ในฐานข้อมูล: CREATE EXTENSION IF NOT EXISTS vector;
# - ใช้ chunk_id เป็น primary key และทำ upsert กันข้อมูลซ้ำ
#
# ``` bash
# รันแบบหัวข้อ:
# python vector_store.py --doc-dir "PATH_TO/data/raw/<doc_id>" --db-url "postgresql://user:pass@localhost:5432/dbname"
# python vector_store.py --doc-dir "C:\Users\Public\Public Programs\Learning_Ai\Retrieval_Augmented_Generation_RAG\media\output\data\raw\1756149124111" --db-url "postgresql://postgres:YOURPASS@localhost:5432/yourdb"
# 
# หรือ รันแบบ sliding (ถ้าเอกสารไม่มีหัวข้อ):
# python vector_store.py --doc-dir "PATH_TO/data/raw/<doc_id>" --db-url "postgresql://user:pass@localhost:5432/dbname"
# python vector_store.py --doc-dir "C:\Users\Public\Public Programs\Learning_Ai\Retrieval_Augmented_Generation_RAG\media\output\data\raw\1756149124111" --db-url "postgresql://postgres:YOURPASS@localhost:5432/yourdb"
#
# Windows example:
# python "C:\Users\Public\Public Programs\Learning_Ai\Retrieval_Augmented_Generation_RAG\vector_store.py" ^
#   --doc-dir "C:\Users\Public\Public Programs\Learning_Ai\Retrieval_Augmented_Generation_RAG\media\output\data\raw\<doc_id>" ^
#   --db-url "postgresql://user:pass@localhost:5432/dbname"
# ```

import os
import json
import argparse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector


BKK_TZ = timezone(timedelta(hours=7))


# -------------------------
# 1) Utilities
# -------------------------
def now_iso_bkk() -> str:
    return datetime.now(BKK_TZ).isoformat(timespec="seconds")


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            rows.append(json.loads(s))
    return rows


def chunked(lst: List[Any], size: int) -> List[List[Any]]:
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


# -------------------------
# 2) SQL: Schema / Index
# -------------------------
def ensure_pgvector_enabled(conn: psycopg.Connection) -> None:
    """เปิดใช้งาน extension pgvector"""
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    conn.commit()


def ensure_table(conn: psycopg.Connection, embedding_dim: int) -> None:
    """
    สร้างตารางหลักสำหรับเก็บ chunks + vectors
    - embedding_dim ต้องตรงกับ model ที่คุณใช้ (เช่น 768)
    """
    ddl = f"""
    CREATE TABLE IF NOT EXISTS rag_chunks (
        chunk_id        TEXT PRIMARY KEY,
        doc_id          TEXT,
        source_file     TEXT,
        page_start      INT,
        page_end        INT,
        heading_path    TEXT[],
        text            TEXT,
        meta            JSONB,

        embedding_model TEXT,
        embedding_dim   INT,
        vector          VECTOR({embedding_dim}),

        embedded_at     TIMESTAMPTZ,
        inserted_at     TIMESTAMPTZ DEFAULT NOW()
    );
    """
    with conn.cursor() as cur:
        cur.execute(ddl)
    conn.commit()


def ensure_indexes(conn: psycopg.Connection) -> None:
    """
    สร้าง index ที่ช่วยค้นหา/กรองข้อมูล
    - vector index: ใช้ HNSW (แนะนำ) หรือ IVFFLAT (ต้อง ANALYZE/ตั้ง lists)
    """
    with conn.cursor() as cur:
        # index สำหรับ filter doc_id
        cur.execute("CREATE INDEX IF NOT EXISTS idx_rag_chunks_doc_id ON rag_chunks(doc_id);")

        # index สำหรับ filter source_file
        cur.execute("CREATE INDEX IF NOT EXISTS idx_rag_chunks_source_file ON rag_chunks(source_file);")

        # vector index (HNSW) — ต้อง pgvector รุ่นที่รองรับ
        # ใช้ cosine distance: vector_cosine_ops
        cur.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = 'idx_rag_chunks_vector_hnsw'
                ) THEN
                    CREATE INDEX idx_rag_chunks_vector_hnsw
                    ON rag_chunks
                    USING hnsw (vector vector_cosine_ops);
                END IF;
            END $$;
        """)
    conn.commit()


# -------------------------
# 3) Upsert logic
# -------------------------
UPSERT_SQL = """
INSERT INTO rag_chunks (
    chunk_id, doc_id, source_file, page_start, page_end, heading_path,
    text, meta,
    embedding_model, embedding_dim, vector,
    embedded_at
)
VALUES (
    %(chunk_id)s, %(doc_id)s, %(source_file)s, %(page_start)s, %(page_end)s, %(heading_path)s,
    %(text)s, %(meta)s::jsonb,
    %(embedding_model)s, %(embedding_dim)s, %(vector)s,
    %(embedded_at)s
)
ON CONFLICT (chunk_id)
DO UPDATE SET
    doc_id = EXCLUDED.doc_id,
    source_file = EXCLUDED.source_file,
    page_start = EXCLUDED.page_start,
    page_end = EXCLUDED.page_end,
    heading_path = EXCLUDED.heading_path,
    text = EXCLUDED.text,
    meta = EXCLUDED.meta,
    embedding_model = EXCLUDED.embedding_model,
    embedding_dim = EXCLUDED.embedding_dim,
    vector = EXCLUDED.vector,
    embedded_at = EXCLUDED.embedded_at,
    inserted_at = NOW()
;
"""


def row_from_embedding_record(r: Dict[str, Any]) -> Dict[str, Any]:
    """
    แปลง record จาก embeddings.jsonl ให้เป็น row สำหรับ insert
    """
    # heading_path บางครั้งอาจเป็น list, หรือไม่มี -> ให้เป็น list เสมอ
    hp = r.get("heading_path") or []
    if not isinstance(hp, list):
        hp = []

    meta = r.get("meta") or {}
    # meta ต้องเป็น dict เพื่อ jsonb
    if not isinstance(meta, dict):
        meta = {"raw_meta": meta}

    vec = r.get("vector")
    if not isinstance(vec, list) or not vec:
        raise ValueError("Missing/invalid vector in record")

    return {
        "chunk_id": r.get("chunk_id"),
        "doc_id": r.get("doc_id"),
        "source_file": r.get("source_file"),
        "page_start": int(r.get("page_start")) if r.get("page_start") is not None else None,
        "page_end": int(r.get("page_end")) if r.get("page_end") is not None else None,
        "heading_path": hp,
        "text": r.get("text") or "",
        "meta": json.dumps(meta, ensure_ascii=False),
        "embedding_model": r.get("embedding_model"),
        "embedding_dim": int(r.get("embedding_dim")) if r.get("embedding_dim") else None,
        "vector": vec,  # pgvector adapter จะจัดการให้
        "embedded_at": r.get("embedded_at"),
    }


def upsert_embeddings(
    conn: psycopg.Connection,
    records: List[Dict[str, Any]],
    batch_size: int = 200
) -> Dict[str, int]:
    """
    upsert แบบ batch
    """
    ok = 0
    err = 0

    with conn.cursor() as cur:
        for batch in chunked(records, batch_size):
            params = []
            for r in batch:
                try:
                    params.append(row_from_embedding_record(r))
                except Exception:
                    err += 1

            if not params:
                continue

            cur.executemany(UPSERT_SQL, params)
            ok += len(params)

    conn.commit()
    return {"ok": ok, "error": err}


# -------------------------
# 4) Main pipeline
# -------------------------
def store_doc_dir(
    doc_dir: str,
    db_url: str,
    table_setup: bool = True,
    create_indexes: bool = True,
    batch_size: int = 200
) -> Dict[str, Any]:
    """
    โหลด embeddings.jsonl แล้ว insert/upsert ลง PostgreSQL
    """
    embeddings_path = os.path.join(doc_dir, "embeddings", "embeddings.jsonl")
    if not os.path.exists(embeddings_path):
        raise FileNotFoundError(f"embeddings.jsonl not found: {embeddings_path}")

    rows = read_jsonl(embeddings_path)
    if not rows:
        raise RuntimeError("No embedding rows found in embeddings.jsonl")

    # ตรวจ dim จากแถวแรก
    dim = rows[0].get("embedding_dim")
    if not dim:
        # fallback จาก vector length
        vec0 = rows[0].get("vector") or []
        dim = len(vec0)
    dim = int(dim)

    started = now_iso_bkk()

    # เชื่อมต่อ DB
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        # register pgvector adapter สำหรับ psycopg3
        register_vector(conn)

        if table_setup:
            ensure_pgvector_enabled(conn)
            ensure_table(conn, embedding_dim=dim)

        if create_indexes:
            ensure_indexes(conn)

        result = upsert_embeddings(conn, rows, batch_size=batch_size)

    finished = now_iso_bkk()

    manifest = {
        "doc_dir": os.path.abspath(doc_dir),
        "started_at": started,
        "finished_at": finished,
        "db_url_redacted": redact_db_url(db_url),
        "embedding_dim": dim,
        "input_rows": len(rows),
        "upsert_ok": result["ok"],
        "upsert_error": result["error"],
        "table": "rag_chunks",
    }
    return manifest


def redact_db_url(db_url: str) -> str:
    """
    ซ่อนรหัสผ่านใน db url เวลา log/manifest
    """
    # รูปแบบง่าย ๆ: postgresql://user:pass@host:port/db
    # แปลง user:pass@ -> user:***@
    import re
    return re.sub(r"//([^:/]+):([^@]+)@", r"//\\1:***@", db_url)


# -------------------------
# 5) CLI
# -------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc-dir", required=True, help="Path to doc folder (contains embeddings/embeddings.jsonl)")
    ap.add_argument("--db-url", required=True, help="PostgreSQL URL e.g. postgresql://user:pass@localhost:5432/dbname")
    ap.add_argument("--batch-size", type=int, default=200)
    ap.add_argument("--no-index", action="store_true", help="Do not create indexes")
    ap.add_argument("--no-setup", action="store_true", help="Do not create extension/table")
    args = ap.parse_args()

    m = store_doc_dir(
        doc_dir=args.doc_dir,
        db_url=args.db_url,
        table_setup=not args.no_setup,
        create_indexes=not args.no_index,
        batch_size=args.batch_size,
    )

    print(
        f"Vector store done: rows={m['input_rows']} ok={m['upsert_ok']} err={m['upsert_error']} "
        f"dim={m['embedding_dim']} table={m['table']}"
    )
    print(f"DB: {m['db_url_redacted']}")


if __name__ == "__main__":
    main()