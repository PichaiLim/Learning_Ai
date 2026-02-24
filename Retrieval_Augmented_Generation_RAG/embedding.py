# embedding.py
# ---------------------------------------
# Read chunks.jsonl -> create embeddings via Ollama -> write embeddings.jsonl + embedding_manifest.json
#
# Input (from chunking.py):
#   <doc_dir>/chunks/chunks.jsonl
#
# Output:
#   <doc_dir>/embeddings/embeddings.jsonl
#   <doc_dir>/embeddings/embedding_manifest.json
#
# Requirements:
#   pip install requests
#
# Usage:
#   python embedding.py --doc-dir "PATH_TO/data/raw/<doc_id>" --model "nomic-embed-text"
#   python embedding.py --doc-dir "..." --model "bge-m3" --ollama-url "http://localhost:11434"
#
# Notes:
# - ใช้ Ollama embeddings endpoint เป็นหลัก: POST {base}/api/embeddings
# - เก็บผลแบบ JSONL เพื่อไปทำ vector_store ต่อได้ง่าย
#
# Example:
#   python embedding.py --doc-dir "Retrieval_Augmented_Generation_RAG/data/raw/PDPA_thailand_ef58d853" --model "nomic-embed-text"
#   python embedding.py --doc-dir "Retrieval_Augmented_Generation_RAG/data/raw/PDPA_thailand_ef58d853" --model "bge-m3" --ollama-url "http://localhost:11434"
#   python embedding.py --doc-dir "Retrieval_Augmented_Generation_RAG/data/raw/PDPA_thailand_ef58d853" --model "bge-m3" --ollama-url "http://localhost:11434" --timeout 180 --sleep 0.5 --limit 10
#   python embedding.py --doc-dir "Retrieval_Augmented_Generation_RAG/data/raw/PDPA_thailand_ef58d853" --model "bge-m3" --ollama-url "http://localhost:11434" --timeout 180 --sleep 0.5 --limit 20  
#   python embedding.py --doc-dir "Retrieval_Augmented_Generation_RAG/data/raw/PDPA_thailand_ef58d853" --model "bge-m3" --ollama-url "http://localhost:11434" --timeout 180 --sleep 0.5 --limit 30

import os
import json
import time
import argparse
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

import requests


BKK_TZ = timezone(timedelta(hours=7))


# -------------------------
# 1) Utilities
# -------------------------
def now_iso_bkk() -> str:
    return datetime.now(BKK_TZ).isoformat(timespec="seconds")


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_json(path: str, data: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_jsonl(path: str, rows: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def safe_float_list(vec: Any) -> List[float]:
    """
    บังคับให้ vector เป็น list[float] แบบปลอดภัย
    """
    if not isinstance(vec, list):
        raise ValueError("Embedding is not a list")
    return [float(x) for x in vec]


# -------------------------
# 2) Ollama Embedding Client
# -------------------------
def ollama_embed(
    text: str,
    model: str,
    base_url: str = "http://localhost:11434",
    timeout_sec: int = 120,
) -> List[float]:
    """
    เรียก Ollama เพื่อทำ embedding
    พยายามใช้ /api/embeddings ก่อน แล้ว fallback ไป /api/embed

    Returns:
      embedding vector (list of floats)
    """
    # 2.1 Preferred endpoint: /api/embeddings
    url1 = base_url.rstrip("/") + "/api/embeddings"
    payload1 = {"model": model, "prompt": text}

    r1 = requests.post(url1, json=payload1, timeout=timeout_sec)
    if r1.status_code == 200:
        data = r1.json()
        if "embedding" in data:
            return safe_float_list(data["embedding"])

    # 2.2 Fallback endpoint: /api/embed (บางเวอร์ชัน/บาง build ใช้ชื่อนี้)
    url2 = base_url.rstrip("/") + "/api/embed"
    payload2 = {"model": model, "input": text}

    r2 = requests.post(url2, json=payload2, timeout=timeout_sec)
    if r2.status_code == 200:
        data = r2.json()
        # บาง schema คืน {"embeddings":[[...]]} หรือ {"embedding":[...]}
        if "embedding" in data:
            return safe_float_list(data["embedding"])
        if "embeddings" in data and isinstance(data["embeddings"], list) and data["embeddings"]:
            return safe_float_list(data["embeddings"][0])

    # ถ้าล้มเหลวทั้งคู่ โยน error พร้อมรายละเอียด
    raise RuntimeError(
        f"Ollama embedding failed. "
        f"/api/embeddings status={r1.status_code} body={r1.text[:300]} | "
        f"/api/embed status={r2.status_code} body={r2.text[:300]}"
    )


# -------------------------
# 3) Main embedding pipeline for one doc_dir
# -------------------------
def embed_doc_dir(
    doc_dir: str,
    model: str,
    base_url: str = "http://localhost:11434",
    timeout_sec: int = 120,
    sleep_sec: float = 0.0,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    อ่าน chunks.jsonl → ทำ embedding → เขียน embeddings.jsonl

    Output embeddings.jsonl per row:
    {
      ...original chunk fields...,
      "embedding_model": "...",
      "embedding_dim": 768,
      "vector": [...],
      "embedded_at": "..."
    }
    """
    chunks_path = os.path.join(doc_dir, "chunks", "chunks.jsonl")
    if not os.path.exists(chunks_path):
        raise FileNotFoundError(f"chunks.jsonl not found: {chunks_path}")

    chunks = read_jsonl(chunks_path)
    if limit is not None:
        chunks = chunks[:limit]

    out_dir = os.path.join(doc_dir, "embeddings")
    ensure_dir(out_dir)

    out_rows: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    started = now_iso_bkk()
    ok = 0

    for i, ch in enumerate(chunks, start=1):
        chunk_id = ch.get("chunk_id")
        text = (ch.get("text") or "").strip()

        if not text:
            errors.append({"chunk_id": chunk_id, "error": "empty_text"})
            continue

        try:
            vec = ollama_embed(
                text=text,
                model=model,
                base_url=base_url,
                timeout_sec=timeout_sec,
            )
            row = {
                **ch,
                "embedding_model": model,
                "embedding_dim": len(vec),
                "vector": vec,
                "embedded_at": now_iso_bkk(),
            }
            out_rows.append(row)
            ok += 1
        except Exception as e:
            errors.append({"chunk_id": chunk_id, "error": str(e)})

        if sleep_sec > 0:
            time.sleep(sleep_sec)

        if i % 25 == 0:
            print(f"[progress] {i}/{len(chunks)} embedded_ok={ok} errors={len(errors)}")

    embeddings_path = os.path.join(out_dir, "embeddings.jsonl")
    write_jsonl(embeddings_path, out_rows)

    finished = now_iso_bkk()

    manifest = {
        "doc_dir": os.path.abspath(doc_dir),
        "doc_id": out_rows[0].get("doc_id") if out_rows else None,
        "source_file": out_rows[0].get("source_file") if out_rows else None,
        "started_at": started,
        "finished_at": finished,
        "ollama_base_url": base_url,
        "embedding_model": model,
        "chunks_total_input": len(chunks),
        "embeddings_ok": ok,
        "embeddings_error": len(errors),
        "output": {
            "dir": "embeddings",
            "embeddings_jsonl": "embeddings/embeddings.jsonl",
        },
        "errors": errors,
    }
    write_json(os.path.join(out_dir, "embedding_manifest.json"), manifest)
    return manifest


# -------------------------
# 4) CLI
# -------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc-dir", required=False, help="Path to doc folder (contains chunks/chunks.jsonl)", default="Retrieval_Augmented_Generation_RAG/data/raw/PDPA_thailand_ef58d853")
    ap.add_argument("--model", required=False, help="Ollama embedding model name (e.g., nomic-embed-text, bge-m3)", default=os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text"))
    ap.add_argument("--ollama-url", help="Ollama base URL", default=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    ap.add_argument("--timeout", type=int, default=os.getenv("OLLAMA_TIMEOUT", 120), help="Request timeout seconds")
    ap.add_argument("--sleep", type=float, default=os.getenv("OLLAMA_SLEEP", 0.0), help="Sleep between requests (sec)")
    ap.add_argument("--limit", type=int, default=os.getenv("OLLAMA_LIMIT", None), help="Limit number of chunks for test run")
    args = ap.parse_args()

    m = embed_doc_dir(
        doc_dir=args.doc_dir,
        model=args.model,
        base_url=args.ollama_url,
        timeout_sec=args.timeout,
        sleep_sec=args.sleep,
        limit=args.limit,
    )

    print(
        f"Embedding done: ok={m['embeddings_ok']}/{m['chunks_total_input']} errors={m['embeddings_error']} "
        f"model={m['embedding_model']}"
    )
    print(f"Output: {os.path.join(args.doc_dir, 'embeddings', 'embeddings.jsonl')}")
    print(f"Manifest: {os.path.join(args.doc_dir, 'embeddings', 'embedding_manifest.json')}")


if __name__ == "__main__":
    main()