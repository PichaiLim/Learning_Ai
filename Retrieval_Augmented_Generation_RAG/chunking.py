# chunking.py
# ---------------------------------------
# Read cleaned markdown pages -> chunk into smaller semantic pieces -> write chunks.jsonl + chunk_manifest.json
#
# Input expected (from preprocessing.py):
#   <doc_dir>/
#     manifest.json
#     preprocess_manifest.json (optional)
#     clean_pages_md/page_001.md
#     clean_pages_md/page_002.md
#
# Output:
#   <doc_dir>/
#     chunks/
#       chunks.jsonl
#       chunk_manifest.json
#
# Notes:
# - ใช้การนับ "จำนวนคำ" เป็นตัวแทน token (เพราะไม่พึ่ง tokenizer ภายนอก)
# - ถ้าคุณใช้ tokenizer จริงในอนาคต (เช่น tiktoken) จะปรับได้ในฟังก์ชัน count_words()
#
# ``` bash
# รันแบบหัวข้อ:
# python chunking.py --doc-dir "PATH_TO/data/raw/<doc_id>" --mode headings
# 
# หรือ รันแบบ sliding (ถ้าเอกสารไม่มีหัวข้อ):
# python chunking.py --doc-dir "PATH_TO/data/raw/<doc_id>" --mode sliding --max-words 700 --overlap-words 100 --min-words 30
#
# Windows example:
# python "C:\Users\Public\Public Programs\Learning_Ai\Retrieval_Augmented_Generation_RAG\chunking.py" ^
#   --doc-dir "C:\Users\Public\Public Programs\Learning_Ai\Retrieval_Augmented_Generation_RAG\media\output\data\raw\<doc_id>" ^
#   --mode headings
# ```
#
# หรือ รันแบบ sliding (ถ้าเอกสารไม่มีหัวข้อ):
# python "C:\Users\Public\Public Programs\Learning_Ai\Retrieval_Augmented_Generation_RAG\chunking.py" ^
#   --doc-dir "C:\Users\Public\Public Programs\Learning_Ai\Retrieval_Augmented_Generation_RAG\media\output\data\raw\<doc_id>" ^
#   --mode sliding --max-words 700 --overlap-words 100 --min-words 30
# ```
#
# ``` Output Json
# {
#   "chunk_id": "...",
#   "doc_id": "...",
#   "page_start": 1,
#   "page_end": 1,
#   "heading_path": ["บทนำ"],
#   "text": "...",
#   "meta": {...}
# }
# ```
# ---------------------------------------

import os
import re
import json
import argparse
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Tuple, List, Optional, Any


BKK_TZ = timezone(timedelta(hours=7))


# -------------------------
# 1) Utilities
# -------------------------
def now_iso_bkk() -> str:
    """คืนเวลาปัจจุบันแบบ ISO ใน timezone ไทย"""
    return datetime.now(BKK_TZ).isoformat(timespec="seconds")


def ensure_dir(path: str) -> None:
    """สร้างโฟลเดอร์ถ้ายังไม่มี"""
    os.makedirs(path, exist_ok=True)


def read_text(path: str) -> str:
    """อ่านไฟล์ข้อความ"""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_json(path: str, data: Dict) -> None:
    """เขียน JSON"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def write_jsonl(path: str, rows: List[Dict]) -> None:
    """เขียน JSONL (1 บรรทัดต่อ 1 chunk)"""
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def read_json(path: str) -> Dict:
    """อ่าน JSON"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def sha1_text(s: str) -> str:
    """ทำ hash ข้อความ เพื่อสร้าง chunk_id ที่เสถียร"""
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def count_words(text: str) -> int:
    """
    นับจำนวนคำแบบง่าย (ใช้ whitespace split)
    - ภาษาไทยจริงๆไม่มีเว้นวรรคทุกคำ แต่สำหรับการคุมขนาด chunk แบบคร่าว ๆ ใช้งานได้
    - ถ้าอยากแม่นขึ้น ค่อยเปลี่ยนเป็น tokenizer จริงภายหลัง
    """
    parts = re.split(r"\s+", text.strip())
    return 0 if parts == [""] else len(parts)


def split_words(text: str) -> List[str]:
    """แยกคำแบบง่าย"""
    parts = re.split(r"\s+", text.strip())
    return [] if parts == [""] else parts


# -------------------------
# 2) Parse metadata header from Markdown (เหมือน preprocessing.py)
# -------------------------
META_BLOCK_RE = re.compile(r"^\s*<!--\s*\n(.*?)\n-->\s*\n?", re.DOTALL)

def split_md_metadata(md_text: str) -> Tuple[Dict[str, str], str]:
    """
    แยก metadata header ออกจาก markdown

    รูปแบบ:
    <!--
    key: value
    -->
    body...

    Returns:
      (metadata_dict, markdown_body)
    """
    m = META_BLOCK_RE.match(md_text)
    if not m:
        return {}, md_text

    raw_meta = m.group(1)
    body = md_text[m.end():]

    meta = {}
    for line in raw_meta.splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip()

    return meta, body


# -------------------------
# 3) Page marker + basic cleanup helpers
# -------------------------
PAGE_MARKER_RE = re.compile(r"^---\s*PAGE\s*(\d+)\s*---\s*$", re.IGNORECASE | re.MULTILINE)

def extract_page_from_body(body: str) -> Optional[int]:
    """ดึงเลขหน้าจาก marker --- PAGE N --- ถ้ามี"""
    m = PAGE_MARKER_RE.search(body)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def remove_page_marker(body: str) -> str:
    """เอา marker ออกจากข้อความก่อน chunk (เพื่อไม่ให้ซ้ำในทุก chunk)"""
    lines = body.splitlines()
    out = []
    for line in lines:
        if re.fullmatch(r"---\s*PAGE\s*\d+\s*---", line.strip(), flags=re.IGNORECASE):
            continue
        out.append(line)
    return "\n".join(out).strip()


def normalize_newlines(text: str) -> str:
    """จัดรูปแบบบรรทัดให้สะอาดเล็กน้อย"""
    # ลดบรรทัดว่างซ้ำ
    text = re.sub(r"\n{3,}", "\n\n", text.strip())
    return text.strip()


# -------------------------
# 4) Chunking Mode A: Heading-based chunking
# -------------------------
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)

def split_by_headings(md_text: str) -> List[Dict[str, Any]]:
    """
    แยกข้อความตามหัวข้อ Markdown:
      # Title
      ## Section
      ### Subsection

    คืน list ของ block:
      {
        "heading_level": int,
        "heading_text": str,
        "content": str
      }

    หมายเหตุ:
    - ถ้าไม่มีหัวข้อเลย จะคืน block เดียวเป็นทั้งเอกสาร
    """
    md_text = normalize_newlines(md_text)
    matches = list(HEADING_RE.finditer(md_text))
    if not matches:
        return [{
            "heading_level": 0,
            "heading_text": "",
            "content": md_text
        }]

    blocks = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md_text)
        level = len(m.group(1))
        title = m.group(2).strip()
        section_text = md_text[m.end():end].strip()

        # เก็บหัวข้อ + เนื้อหา
        blocks.append({
            "heading_level": level,
            "heading_text": title,
            "content": section_text
        })
    return blocks


def pack_blocks_to_chunks(
    blocks: List[Dict[str, Any]],
    max_words: int,
    overlap_words: int
) -> List[Dict[str, Any]]:
    """
    เอา blocks (ตามหัวข้อ) มาจัดกลุ่มเป็น chunks โดยคุมขนาดด้วยจำนวนคำ
    - ถ้า block ใหญ่เกิน max_words จะถูกแบ่งย่อยแบบ sliding window

    Returns list chunks:
      {
        "heading_path": ["H1", "H2", ...] (แบบคร่าว)
        "text": ...
      }
    """
    chunks = []
    heading_stack: List[Tuple[int, str]] = []

    def current_heading_path() -> List[str]:
        return [t for (_, t) in heading_stack]

    def split_big_text(text: str, heading_path: List[str]) -> None:
        words = split_words(text)
        if not words:
            return
        step = max(1, max_words - overlap_words)
        start = 0
        while start < len(words):
            end = min(start + max_words, len(words))
            piece = " ".join(words[start:end]).strip()
            if piece:
                chunks.append({
                    "heading_path": heading_path,
                    "text": piece
                })
            start += step

    buffer_text = ""
    buffer_heading_path: List[str] = []

    for b in blocks:
        lvl = b["heading_level"]
        title = b["heading_text"]
        content = b["content"].strip()

        # ปรับ stack ให้สะท้อนโครงสร้างหัวข้อ
        if lvl > 0:
            while heading_stack and heading_stack[-1][0] >= lvl:
                heading_stack.pop()
            heading_stack.append((lvl, title))

        # สร้างข้อความ section
        section_text = ""
        if lvl > 0:
            prefix = "#" * lvl + " " + title
            section_text = f"{prefix}\n{content}".strip()
        else:
            section_text = content

        section_words = count_words(section_text)

        # ถ้า section ใหญ่มาก แยกย่อยเลย
        if section_words > max_words:
            # flush buffer ก่อน
            if buffer_text.strip():
                chunks.append({
                    "heading_path": buffer_heading_path,
                    "text": buffer_text.strip()
                })
                buffer_text = ""
                buffer_heading_path = []

            split_big_text(section_text, current_heading_path())
            continue

        # ลอง pack ลง buffer
        candidate = (buffer_text + "\n\n" + section_text).strip() if buffer_text else section_text
        if count_words(candidate) <= max_words:
            buffer_text = candidate
            buffer_heading_path = current_heading_path()
        else:
            # ปล่อย buffer เดิมเป็น chunk
            if buffer_text.strip():
                chunks.append({
                    "heading_path": buffer_heading_path,
                    "text": buffer_text.strip()
                })
            buffer_text = section_text
            buffer_heading_path = current_heading_path()

    # flush สุดท้าย
    if buffer_text.strip():
        chunks.append({
            "heading_path": buffer_heading_path,
            "text": buffer_text.strip()
        })

    return chunks


# -------------------------
# 5) Chunking Mode B: Sliding window chunking (word-based)
# -------------------------
def sliding_window_chunks(text: str, max_words: int, overlap_words: int) -> List[str]:
    """
    แบ่งข้อความเป็น chunks ด้วยหน้าต่างเลื่อน
    - เหมาะกับ OCR ที่ไม่มีหัวข้อ/โครงสร้าง
    """
    text = normalize_newlines(text)
    words = split_words(text)
    if not words:
        return []

    step = max(1, max_words - overlap_words)
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        piece = " ".join(words[start:end]).strip()
        if piece:
            chunks.append(piece)
        start += step
    return chunks


# -------------------------
# 6) Build chunks for one doc_dir
# -------------------------
def resolve_doc_pages(doc_dir: str) -> List[Dict[str, Any]]:
    """
    อ่าน manifest.json เพื่อรู้ path ของหน้า
    - รองรับใช้ preprocess_manifest.json ด้วย (ถ้ามี)
    """
    manifest_path = os.path.join(doc_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"manifest.json not found in: {doc_dir}")

    manifest = read_json(manifest_path)
    doc_id = manifest.get("doc_id")
    source_file = manifest.get("source_file")

    preprocess_path = os.path.join(doc_dir, "preprocess_manifest.json")
    use_preprocessed = os.path.exists(preprocess_path)

    # ถ้ามี preprocess_manifest ให้ใช้ output_md จากมัน (clean_pages_md)
    if use_preprocessed:
        pm = read_json(preprocess_path)
        pages = pm.get("pages", [])
        page_items = []
        for p in pages:
            if p.get("status") != "ok":
                continue
            out_md = p.get("output_md")
            page_no = p.get("page")
            if not out_md:
                continue
            page_items.append({
                "page": page_no,
                "md_relpath": out_md,
                "doc_id": doc_id,
                "source_file": source_file
            })
        if page_items:
            return sorted(page_items, key=lambda x: int(x["page"]) if x["page"] else 0)

    # fallback: ใช้ pages_md จาก manifest.json
    pages = manifest.get("pages", [])
    page_items = []
    for p in pages:
        if p.get("status") != "ok":
            continue
        md_path = p.get("md_path")
        page_no = p.get("page")
        if not md_path:
            continue
        page_items.append({
            "page": page_no,
            "md_relpath": md_path,
            "doc_id": doc_id,
            "source_file": source_file
        })
    return sorted(page_items, key=lambda x: int(x["page"]) if x["page"] else 0)


def chunk_document_dir(
    doc_dir: str,
    mode: str = "headings",
    max_words: int = 700,
    overlap_words: int = 100,
    min_words: int = 30
) -> Dict[str, Any]:
    """
    ทำ chunking ทั้งเอกสาร:
    - อ่านแต่ละหน้า
    - ทำ chunk ตามโหมดที่เลือก
    - สร้าง chunks.jsonl + chunk_manifest.json

    min_words: กรอง chunk ที่สั้นเกินไป (กัน noise)
    """
    pages = resolve_doc_pages(doc_dir)
    if not pages:
        raise RuntimeError("No pages found to chunk (check preprocess/manifest)")

    doc_id = pages[0]["doc_id"]
    source_file = pages[0]["source_file"]

    out_dir = os.path.join(doc_dir, "chunks")
    ensure_dir(out_dir)

    all_chunks: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    for item in pages:
        page_no = item["page"]
        md_path = os.path.join(doc_dir, item["md_relpath"])

        try:
            raw = read_text(md_path)
            meta, body = split_md_metadata(raw)

            # ดึงเลขหน้าจาก body marker ถ้ามี (เพื่อตรงกับ preprocessing)
            page_from_body = extract_page_from_body(body)
            effective_page = page_from_body or page_no

            # เอา marker ออกก่อน chunk
            body = remove_page_marker(body)
            body = normalize_newlines(body)

            if not body.strip():
                continue

            if mode == "headings":
                # แบ่งตามหัวข้อ แล้ว pack ให้พอดี max_words
                blocks = split_by_headings(body)
                packed = pack_blocks_to_chunks(blocks, max_words=max_words, overlap_words=overlap_words)
                for idx, ch in enumerate(packed, start=1):
                    text = ch["text"].strip()
                    if count_words(text) < min_words:
                        continue

                    chunk_id = f"{doc_id}_p{int(effective_page):03d}_h_{idx:04d}_{sha1_text(text)[:8]}"
                    all_chunks.append({
                        "chunk_id": chunk_id,
                        "doc_id": doc_id,
                        "source_file": source_file,
                        "page_start": int(effective_page),
                        "page_end": int(effective_page),
                        "heading_path": ch.get("heading_path", []),
                        "text": text,
                        "meta": {
                            **meta,
                            "chunk_mode": "headings",
                            "chunk_index_on_page": idx,
                            "chunked_at": now_iso_bkk(),
                        }
                    })

            elif mode == "sliding":
                # แบ่งด้วย sliding window ตามจำนวนคำ
                pieces = sliding_window_chunks(body, max_words=max_words, overlap_words=overlap_words)
                for idx, text in enumerate(pieces, start=1):
                    if count_words(text) < min_words:
                        continue
                    chunk_id = f"{doc_id}_p{int(effective_page):03d}_s_{idx:04d}_{sha1_text(text)[:8]}"
                    all_chunks.append({
                        "chunk_id": chunk_id,
                        "doc_id": doc_id,
                        "source_file": source_file,
                        "page_start": int(effective_page),
                        "page_end": int(effective_page),
                        "heading_path": [],
                        "text": text.strip(),
                        "meta": {
                            **meta,
                            "chunk_mode": "sliding",
                            "chunk_index_on_page": idx,
                            "chunked_at": now_iso_bkk(),
                        }
                    })
            else:
                raise ValueError("mode must be 'headings' or 'sliding'")

        except Exception as e:
            errors.append({"page": page_no, "md": item["md_relpath"], "error": str(e)})

    # เขียนไฟล์ผลลัพธ์
    chunks_path = os.path.join(out_dir, "chunks.jsonl")
    write_jsonl(chunks_path, all_chunks)

    chunk_manifest = {
        "doc_id": doc_id,
        "source_file": source_file,
        "chunk_started_at": now_iso_bkk(),
        "mode": mode,
        "max_words": max_words,
        "overlap_words": overlap_words,
        "min_words": min_words,
        "chunks_total": len(all_chunks),
        "pages_total": len(pages),
        "pages_with_chunks": len(set(c["page_start"] for c in all_chunks)) if all_chunks else 0,
        "errors_total": len(errors),
        "errors": errors,
        "output": {
            "dir": "chunks",
            "chunks_jsonl": "chunks/chunks.jsonl",
        },
        "chunk_finished_at": now_iso_bkk(),
    }
    write_json(os.path.join(out_dir, "chunk_manifest.json"), chunk_manifest)

    return chunk_manifest


# -------------------------
# 7) CLI
# -------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--doc-dir", 
        required=False, 
        help="Path to doc folder (contains manifest.json)", 
        default=str(os.path.join(os.path.dirname(__file__), "data", "raw", "PDPA_thailand_ef58d853"))
        )
    ap.add_argument(
        "--mode",
        default="headings",
        choices=["headings", "sliding"],
        help="Chunking mode: headings (by markdown headers) or sliding (word window)",
    )
    ap.add_argument("--max-words", type=int, default=700, help="Max words per chunk (approx token budget)")
    ap.add_argument("--overlap-words", type=int, default=100, help="Overlap words between chunks")
    ap.add_argument("--min-words", type=int, default=30, help="Drop chunks smaller than this")
    args = ap.parse_args()

    m = chunk_document_dir(
        doc_dir=args.doc_dir,
        mode=args.mode,
        max_words=args.max_words,
        overlap_words=args.overlap_words,
        min_words=args.min_words
    )

    print(
        f"Chunking done: doc_id={m['doc_id']} chunks={m['chunks_total']} errors={m['errors_total']} mode={m['mode']}"
    )
    print(f"Output: {os.path.join(args.doc_dir, 'chunks', 'chunks.jsonl')}")
    print(f"Manifest: {os.path.join(args.doc_dir, 'chunks', 'chunk_manifest.json')}")


if __name__ == "__main__":
    main()