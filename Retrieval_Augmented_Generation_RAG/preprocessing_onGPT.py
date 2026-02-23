# preprocessing.py
# ---------------------------------------
# Read raw OCR markdown (per page) -> clean/normalize -> write cleaned markdown
#
# Expected input structure (from ingestion.py):
#   <doc_dir>/
#     manifest.json
#     pages_md/page_001.md
#     pages_md/page_002.md
#
# Output:
#   <doc_dir>/
#     clean_pages_md/page_001.md
#     clean_pages_md/page_002.md
#     preprocess_manifest.json
#
# Requirements: (standard library only)

import os
import re
import json
import argparse
from datetime import datetime, timezone, timedelta
from typing import Dict, Tuple, List, Optional


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


def write_text(path: str, text: str) -> None:
    """เขียนไฟล์ข้อความ"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read_json(path: str) -> Dict:
    """อ่าน JSON"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, data: Dict) -> None:
    """เขียน JSON"""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# -------------------------
# 2) Parse metadata header from Markdown
# -------------------------
META_BLOCK_RE = re.compile(r"^\s*<!--\s*\n(.*?)\n-->\s*\n?", re.DOTALL)

def split_md_metadata(md_text: str) -> Tuple[Dict[str, str], str]:
    """
    แยก metadata header ออกจาก markdown

    รูปแบบ header ที่ ingestion.py เขียน:
    <!--
    key: value
    key2: value2
    -->
    ...content...

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


def build_md_with_metadata(meta: Dict[str, str], body: str) -> str:
    """ประกอบ markdown กลับ พร้อม metadata header"""
    header = "<!--\n" + "\n".join(f"{k}: {v}" for k, v in meta.items()) + "\n-->\n\n"
    return header + body.strip() + "\n"


# -------------------------
# 3) Cleaning functions (Preprocessing rules)
# -------------------------
def strip_empty_edges(lines: List[str]) -> List[str]:
    """ตัดบรรทัดว่างหัว/ท้ายออก"""
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def normalize_whitespace(text: str) -> str:
    """
    ทำความสะอาด whitespace แบบปลอดภัย:
    - ลดช่องว่างซ้ำ
    - ลดช่องว่างท้ายบรรทัด
    - ไม่ไปทำลายรูปแบบตารางหนัก ๆ
    """
    lines = text.splitlines()
    out = []
    for line in lines:
        # ตัดช่องว่างท้ายบรรทัด
        line = line.rstrip()

        # ลดช่องว่างซ้ำแบบกลางบรรทัด (แต่ไม่ไปทำกับเส้นตาราง/โค้ด)
        if not line.strip().startswith("|"):
            line = re.sub(r"[ \t]{2,}", " ", line)

        out.append(line)
    return "\n".join(out)


def remove_page_number_lines(text: str) -> str:
    """
    ลบบรรทัดที่เป็นเลขหน้าอย่างเดียว (เช่น 'หน้า 12', 'Page 12')
    """
    lines = text.splitlines()
    kept = []
    for line in lines:
        s = line.strip()
        if re.fullmatch(r"(หน้า|page)\s*\d+\s*", s, flags=re.IGNORECASE):
            continue
        kept.append(line)
    return "\n".join(kept)


def remove_separator_lines(text: str) -> str:
    """
    ลบบรรทัดเส้นคั่นยาว ๆ เช่น -----, =====, _____
    """
    lines = text.splitlines()
    kept = []
    for line in lines:
        s = line.strip()
        if re.fullmatch(r"[-=_]{3,}", s):
            continue
        kept.append(line)
    return "\n".join(kept)


def remove_repeated_header_footer_simple(text: str, top_n: int = 2, bottom_n: int = 2) -> str:
    """
    เวอร์ชัน baseline: ตัดบรรทัดหัว/ท้ายแบบง่าย ๆ
    - ใช้เมื่อ OCR ชอบยัดชื่อบริษัท/ชื่อเอกสารซ้ำทุกหน้า
    - วิธีนี้ยังไม่ฉลาดมาก แต่ช่วยลด noise ได้ในหลายเคส

    แนวคิด:
    - ถ้าบรรทัดบนสุด/ล่างสุดสั้นมาก ๆ และซ้ำในหลายหน้า ให้ตัดทิ้ง
    (ในไฟล์นี้เรายังไม่ได้ทำ global compare ข้ามหน้า เพื่อให้ง่าย)
    """
    lines = text.splitlines()
    lines = strip_empty_edges(lines)

    # ตัดหัว top_n ถ้าสั้นและดูเป็น header
    for _ in range(min(top_n, len(lines))):
        s = lines[0].strip()
        if len(s) <= 40 and (("บริษัท" in s) or ("Company" in s) or ("รายงาน" in s) or ("Report" in s)):
            lines.pop(0)
        else:
            break

    # ตัดท้าย bottom_n ถ้าสั้นและดูเป็น footer
    for _ in range(min(bottom_n, len(lines))):
        if not lines:
            break
        s = lines[-1].strip()
        if len(s) <= 40 and (("สงวนลิขสิทธิ์" in s) or ("confidential" in s.lower()) or ("copyright" in s.lower())):
            lines.pop()
        else:
            break

    return "\n".join(lines)


def normalize_thai_composition_basic(text: str) -> str:
    """
    Normalize แบบเบา ๆ:
    - รวม unicode ให้คงที่ (NFC)
    """
    try:
        import unicodedata
        return unicodedata.normalize("NFC", text)
    except Exception:
        return text


def add_page_marker(body: str, page: Optional[int]) -> str:
    """
    ใส่ marker แยกหน้าเพื่อช่วย debug/citation
    """
    if page is None:
        return body.strip()
    return f"--- PAGE {page} ---\n\n{body.strip()}"


def preprocess_body(body: str, page: Optional[int]) -> str:
    """
    รวมกฎการ clean ทั้งหมดเป็น pipeline
    """
    body = normalize_thai_composition_basic(body)
    body = remove_page_number_lines(body)
    body = remove_separator_lines(body)
    body = remove_repeated_header_footer_simple(body)
    body = normalize_whitespace(body)
    body = add_page_marker(body, page)
    return body.strip() + "\n"


# -------------------------
# 4) Preprocess one document directory
# -------------------------
def preprocess_document_dir(doc_dir: str) -> Dict:
    """
    doc_dir คือโฟลเดอร์ที่มี manifest.json + pages_md/

    Returns preprocess manifest dict
    """
    manifest_path = os.path.join(doc_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"manifest.json not found in: {doc_dir}")

    manifest = read_json(manifest_path)
    pages = manifest.get("pages", [])

    pages_md_dir = os.path.join(doc_dir, "pages_md")
    out_dir = os.path.join(doc_dir, "clean_pages_md")
    ensure_dir(out_dir)

    results = []
    errors = []

    for p in pages:
        page_no = p.get("page")
        rel_md = p.get("md_path")  # e.g. pages_md/page_001.md
        if not rel_md:
            results.append({"page": page_no, "status": "skip_no_md"})
            continue

        in_md_path = os.path.join(doc_dir, rel_md)
        if not os.path.exists(in_md_path):
            errors.append({"page": page_no, "error": f"missing input md: {rel_md}"})
            results.append({"page": page_no, "status": "error"})
            continue

        try:
            raw_md = read_text(in_md_path)
            meta, body = split_md_metadata(raw_md)

            # ใช้ page จาก meta ถ้ามี
            page_from_meta = None
            if "page" in meta:
                try:
                    page_from_meta = int(meta["page"])
                except Exception:
                    page_from_meta = page_no

            cleaned_body = preprocess_body(body, page_from_meta or page_no)

            # เพิ่ม field บอกว่า clean แล้ว + เวลา
            meta["preprocessed_at"] = now_iso_bkk()
            meta["preprocess_version"] = "1.0"

            out_md_name = f"page_{int(page_no):03d}.md" if page_no else os.path.basename(in_md_path)
            out_md_path = os.path.join(out_dir, out_md_name)

            write_text(out_md_path, build_md_with_metadata(meta, cleaned_body))

            results.append(
                {
                    "page": page_no,
                    "input_md": rel_md,
                    "output_md": os.path.relpath(out_md_path, doc_dir),
                    "status": "ok",
                }
            )
        except Exception as e:
            errors.append({"page": page_no, "error": str(e)})
            results.append({"page": page_no, "status": "error"})

    preprocess_manifest = {
        "doc_id": manifest.get("doc_id"),
        "source_file": manifest.get("source_file"),
        "preprocess_started_at": now_iso_bkk(),
        "pages_total": len(pages),
        "pages_ok": sum(1 for r in results if r["status"] == "ok"),
        "pages_error": sum(1 for r in results if r["status"] == "error"),
        "pages": results,
        "errors": errors,
        "output_dir": "clean_pages_md",
        "preprocess_finished_at": now_iso_bkk(),
    }

    write_json(os.path.join(doc_dir, "preprocess_manifest.json"), preprocess_manifest)
    return preprocess_manifest


# -------------------------
# 5) CLI
# -------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--doc-dir",
        required=True,
        help="Path to a single doc output folder produced by ingestion.py (contains manifest.json)",
    )
    args = ap.parse_args()

    m = preprocess_document_dir(args.doc_dir)
    print(
        f"Preprocess done: doc_id={m.get('doc_id')} ok={m['pages_ok']}/{m['pages_total']} errors={m['pages_error']}"
    )
    print(f"Output: {os.path.join(args.doc_dir, 'clean_pages_md')}")
    print(f"Manifest: {os.path.join(args.doc_dir, 'preprocess_manifest.json')}")


if __name__ == "__main__":
    main()