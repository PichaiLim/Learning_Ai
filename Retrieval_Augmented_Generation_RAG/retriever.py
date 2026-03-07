# retriever.py
# ---------------------------------------
# Stage 6: Query Embedding -> pgvector similarity search -> top-k chunks
#
# Requirements:
#   pip install psycopg[binary] pgvector requests
#
# Env:
#   DATABASE_URL, OLLAMA_URL, EMBED_MODEL
#
# Usage (as module):
#   from retriever import retrieve_top_k
#   chunks = retrieve_top_k(question="...", top_k=5)

import os
import json
import argparse
from typing import Any, Dict, List, Optional

import requests
import psycopg
from psycopg.rows import dict_row
from pgvector.psycopg import register_vector


# -------------------------
# Ollama embedding
# -------------------------
def ollama_embed(text: str, model: str, base_url: str, timeout_sec: int = 120) -> List[float]:
    # Preferred: /api/embeddings
    url1 = base_url.rstrip("/") + "/api/embeddings"
    r1 = requests.post(url1, json={"model": model, "prompt": text}, timeout=timeout_sec)
    if r1.status_code == 200:
        data = r1.json()
        if "embedding" in data and isinstance(data["embedding"], list):
            return [float(x) for x in data["embedding"]]

    # Fallback: /api/embed
    url2 = base_url.rstrip("/") + "/api/embed"
    r2 = requests.post(url2, json={"model": model, "input": text}, timeout=timeout_sec)
    if r2.status_code == 200:
        data = r2.json()
        if "embedding" in data and isinstance(data["embedding"], list):
            return [float(x) for x in data["embedding"]]
        if "embeddings" in data and isinstance(data["embeddings"], list) and data["embeddings"]:
            return [float(x) for x in data["embeddings"][0]]

    raise RuntimeError(
        f"Ollama embed failed: /api/embeddings={r1.status_code} {r1.text[:200]} | "
        f"/api/embed={r2.status_code} {r2.text[:200]}"
    )


# -------------------------
# pgvector retrieval
# -------------------------
RETRIEVE_SQL = """
SELECT
  chunk_id, doc_id, source_file, page_start, page_end, heading_path,
  text, meta,
  embedding_model, embedding_dim,
  (vector <=> %(qvec)s) AS cosine_distance
FROM rag_chunks
WHERE (%(doc_id)s IS NULL OR doc_id = %(doc_id)s)
ORDER BY vector <=> %(qvec)s
LIMIT %(top_k)s;
"""


def retrieve_top_k(
    question: str,
    top_k: int = 5,
    db_url: Optional[str] = None,
    ollama_url: Optional[str] = None,
    embed_model: Optional[str] = None,
    doc_id: Optional[str] = None,
    timeout_sec: int = 120,
) -> Dict[str, Any]:
    """
    Returns:
      {
        "question": str,
        "top_k": int,
        "embed_model": str,
        "results": [ {chunk fields... + cosine_distance}, ... ]
      }
    """
    db_url = db_url or os.getenv("DATABASE_URL")
    ollama_url = ollama_url or os.getenv("OLLAMA_URL", "http://localhost:11434")
    embed_model = embed_model or os.getenv("EMBED_MODEL", "nomic-embed-text")

    if not db_url:
        raise ValueError("DATABASE_URL is required (env or parameter)")

    qvec = ollama_embed(question, model=embed_model, base_url=ollama_url, timeout_sec=timeout_sec)

    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(RETRIEVE_SQL, {"qvec": qvec, "top_k": top_k, "doc_id": doc_id})
            rows = cur.fetchall()

    # แปลง meta ให้เป็น dict เสมอ (psycopg อาจคืนเป็น dict อยู่แล้ว)
    results = []
    for r in rows:
        meta = r.get("meta")
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {"raw_meta": meta}
        if meta is None:
            meta = {}
        r["meta"] = meta
        results.append(r)

    return {
        "question": question,
        "top_k": top_k,
        "embed_model": embed_model,
        "results": results,
    }


# -------------------------
# CLI
# -------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", required=True)
    ap.add_argument("--top-k", type=int, default=int(os.getenv("TOP_K", "5")))
    ap.add_argument("--doc-id", default=None)
    ap.add_argument("--db-url", default=os.getenv("DATABASE_URL"))
    ap.add_argument("--ollama-url", default=os.getenv("OLLAMA_URL", "http://localhost:11434"))
    ap.add_argument("--embed-model", default=os.getenv("EMBED_MODEL", "nomic-embed-text"))
    args = ap.parse_args()

    out = retrieve_top_k(
        question=args.question,
        top_k=args.top_k,
        db_url=args.db_url,
        ollama_url=args.ollama_url,
        embed_model=args.embed_model,
        doc_id=args.doc_id,
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()