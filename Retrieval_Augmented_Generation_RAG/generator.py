# generator.py
# ---------------------------------------
# Stage 7: Compose prompt from retrieved chunks -> call Ollama LLM -> answer with citations
#
# Requirements:
#   pip install requests
#
# Env:
#   OLLAMA_URL, LLM_MODEL
#
# Usage:
#   from generator import generate_answer
#   answer = generate_answer(question, retrieved_results)

import os
import argparse
from typing import Any, Dict, List

import requests


def format_context_chunks(results: List[Dict[str, Any]], max_chars: int = 12000) -> str:
    """
    เอา chunks มาต่อเป็น context พร้อม label/citation id
    จำกัดความยาวรวมเพื่อกัน prompt บวม
    """
    parts = []
    total = 0
    for i, r in enumerate(results, start=1):
        src = r.get("source_file") or "unknown"
        ps = r.get("page_start")
        pe = r.get("page_end")
        hp = r.get("heading_path") or []
        heading = " / ".join(hp) if isinstance(hp, list) else str(hp)

        label = f"[S{i}] {src} p.{ps}-{pe}" if ps is not None else f"[S{i}] {src}"
        if heading:
            label += f" | {heading}"

        text = (r.get("text") or "").strip()
        block = f"{label}\n{text}\n"

        if total + len(block) > max_chars:
            break

        parts.append(block)
        total += len(block)

    return "\n".join(parts).strip()


def build_prompt(question: str, results: List[Dict[str, Any]]) -> str:
    context = format_context_chunks(results)

    # แนว prompt: บังคับอ้างอิงจาก context + ถ้าไม่มีให้บอกว่าไม่พบ
    return f"""คุณคือผู้ช่วย RAG ที่ตอบโดยอ้างอิงจาก CONTEXT เท่านั้น

กติกา:
1) ถ้าคำตอบไม่มีใน CONTEXT ให้ตอบว่า "ไม่พบข้อมูลในเอกสารที่ให้มา" และอธิบายสั้น ๆ ว่าขาดอะไร
2) ตอบเป็นภาษาไทย กระชับ ชัดเจน
3) ใส่อ้างอิงท้ายประโยคด้วยรูปแบบ [S1], [S2] ตามแหล่งข้อมูลที่ใช้

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
"""


def ollama_generate(prompt: str, model: str, base_url: str, timeout_sec: int = 180) -> str:
    """
    เรียก Ollama LLM แบบ /api/generate (ง่ายสุด)
    """
    url = base_url.rstrip("/") + "/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    r = requests.post(url, json=payload, timeout=timeout_sec)
    if r.status_code != 200:
        raise RuntimeError(f"Ollama generate failed: {r.status_code} {r.text[:300]}")
    data = r.json()
    return (data.get("response") or "").strip()


def generate_answer(
    question: str,
    retrieved: Dict[str, Any],
    ollama_url: str | None = None,
    llm_model: str | None = None,
) -> Dict[str, Any]:
    ollama_url = ollama_url or os.getenv("OLLAMA_URL", "http://localhost:11434")
    llm_model = llm_model or os.getenv("LLM_MODEL", "typhoon")

    results = retrieved.get("results") or []
    prompt = build_prompt(question, results)
    answer = ollama_generate(prompt, model=llm_model, base_url=ollama_url)

    return {
        "question": question,
        "llm_model": llm_model,
        "answer": answer,
        "sources": [
            {
                "sid": f"S{i}",
                "chunk_id": r.get("chunk_id"),
                "source_file": r.get("source_file"),
                "page_start": r.get("page_start"),
                "page_end": r.get("page_end"),
                "heading_path": r.get("heading_path"),
                "cosine_distance": r.get("cosine_distance"),
            }
            for i, r in enumerate(results, start=1)
        ],
    }


# CLI
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", required=True)
    ap.add_argument("--retrieved-json", required=True, help="Path to JSON produced by retriever.py")
    ap.add_argument("--ollama-url", default=os.getenv("OLLAMA_URL", "http://localhost:11434"))
    ap.add_argument("--llm-model", default=os.getenv("LLM_MODEL", "typhoon"))
    args = ap.parse_args()

    import json
    with open(args.retrieved_json, "r", encoding="utf-8") as f:
        retrieved = json.load(f)

    out = generate_answer(args.question, retrieved, ollama_url=args.ollama_url, llm_model=args.llm_model)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()