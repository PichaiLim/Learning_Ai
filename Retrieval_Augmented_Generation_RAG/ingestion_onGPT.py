# ingestion.py
# -------------------------
# PDF -> Images (per page) -> OCR (Ollama Typhoon) -> Markdown per page + manifest.json
#
# Requirements:
#   pip install pymupdf requests
#
# Usage:
#   python ingestion.py --input ./pdfs --output ./data/raw --model typhoon
#
# Notes:
# - If your PDF is scanned, OCR path is correct.
# - If your PDF has a text layer, you can later add a "extract text directly" branch.

import os
import re
import json
import time
import hashlib
import argparse
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
from load_dotenv import load_dotenv

import fitz  # PyMuPDF
import requests

load_dotenv()


BKK_TZ = timezone(timedelta(hours=7))


def now_iso_bkk() -> str:
    return datetime.now(BKK_TZ).isoformat(timespec="seconds")


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def slugify_filename(name: str) -> str:
    # ทำ id ให้ปลอดภัยสำหรับ path
    name = os.path.splitext(os.path.basename(name))[0]
    name = re.sub(r"[^\w\-]+", "_", name, flags=re.UNICODE)
    return name.strip("_") or "document"


def sha1_of_file(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def list_pdfs(input_dir: str) -> List[str]:
    pdfs = []
    for root, _, files in os.walk(input_dir):
        for fn in files:
            if fn.lower().endswith(".pdf"):
                pdfs.append(os.path.join(root, fn))
    return sorted(pdfs)


def pdf_to_images(
    pdf_path: str,
    out_dir: str,
    dpi: int = 300,
    image_format: str = "png",
) -> List[Dict]:
    """
    Render each page of PDF to image.
    Returns list of dict: {page, image_path, width, height}
    """
    ensure_dir(out_dir)
    doc = fitz.open(pdf_path)

    zoom = dpi / 72  # PyMuPDF default is 72 dpi
    mat = fitz.Matrix(zoom, zoom)

    pages_info = []
    for i in range(len(doc)):
        page = doc.load_page(i)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        image_path = os.path.join(out_dir, f"page_{i+1:03d}.{image_format}")
        pix.save(image_path)

        pages_info.append(
            {
                "page": i + 1,
                "image_path": image_path,
                "width": pix.width,
                "height": pix.height,
            }
        )

    doc.close()
    return pages_info


def ocr_image_via_ollama(
    image_path: str,
    model: str = "typhoon",
    ollama_url: str = "http://localhost:11434/api/generate",
    timeout_sec: int = 120,
) -> str:
    """
    Call Ollama generate API with an image to do OCR-like extraction.
    Many vision models accept base64 images. We'll send base64 in 'images'.

    IMPORTANT:
    - Your typhoon model must support vision/OCR style input.
    - If your model expects a different endpoint or schema, adjust here.
    """
    import base64

    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    prompt = (
        "อ่านข้อความในภาพนี้ทั้งหมด แล้วจัดรูปแบบเป็น Markdown ที่อ่านง่าย "
        "คงหัวข้อ/รายการ/ตารางเท่าที่ทำได้ "
        "ไม่ต้องอธิบายเพิ่ม และอย่าเติมข้อมูลที่ไม่มีในภาพ"
    )

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "images": [img_b64],
    }

    r = requests.post(ollama_url, json=payload, timeout=timeout_sec)
    r.raise_for_status()
    data = r.json()

    # Ollama response usually has "response"
    return (data.get("response") or "").strip()


def write_page_markdown(
    out_path: str,
    text: str,
    metadata: Dict,
) -> None:
    """
    Save page OCR output as Markdown with metadata header.
    """
    header = (
        "<!--\n"
        + "\n".join([f"{k}: {v}" for k, v in metadata.items()])
        + "\n-->\n\n"
    )

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(text)
        f.write("\n")


def write_manifest(out_path: str, manifest: Dict) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def ingest_pdf(
    pdf_path: str,
    output_root: str,
    model: str,
    dpi: int = 300,
    ollama_url: str = "http://localhost:11434/v1",
    sleep_sec: float = 0.0,
) -> Dict:
    """
    Ingest a single PDF:
      - render pages to images
      - OCR each image
      - write page_XXX.md
      - write manifest.json
    """
    pdf_hash = sha1_of_file(pdf_path)
    base_id = slugify_filename(pdf_path)
    doc_id = f"{base_id}_{pdf_hash[:8]}"

    doc_out_dir = os.path.join(output_root, doc_id)
    img_dir = os.path.join(doc_out_dir, "images")
    md_dir = os.path.join(doc_out_dir, "pages_md")

    ensure_dir(doc_out_dir)
    ensure_dir(img_dir)
    ensure_dir(md_dir)

    started = now_iso_bkk()

    # 1) PDF -> images
    pages_info = pdf_to_images(pdf_path, img_dir, dpi=dpi, image_format="png")

    pages = []
    errors = []

    # 2) OCR each page
    for p in pages_info:
        page_no = p["page"]
        image_path = p["image_path"]
        md_path = os.path.join(md_dir, f"page_{page_no:03d}.md")

        meta = {
            "source_file": os.path.basename(pdf_path),
            "source_path": os.path.abspath(pdf_path),
            "doc_id": doc_id,
            "page": page_no,
            "dpi": dpi,
            "image_path": os.path.relpath(image_path, doc_out_dir),
            "ingested_at": now_iso_bkk(),
            "ocr_model": model,
        }

        try:
            text_md = ocr_image_via_ollama(
                image_path=image_path,
                model=model,
                ollama_url=ollama_url,
            )
            write_page_markdown(md_path, text_md, meta)
            pages.append(
                {
                    "page": page_no,
                    "image_path": os.path.relpath(image_path, doc_out_dir),
                    "md_path": os.path.relpath(md_path, doc_out_dir),
                    "width": p["width"],
                    "height": p["height"],
                    "status": "ok",
                }
            )
        except Exception as e:
            errors.append({"page": page_no, "error": str(e)})
            pages.append(
                {
                    "page": page_no,
                    "image_path": os.path.relpath(image_path, doc_out_dir),
                    "md_path": None,
                    "width": p["width"],
                    "height": p["height"],
                    "status": "error",
                }
            )

        if sleep_sec > 0:
            time.sleep(sleep_sec)

    finished = now_iso_bkk()

    manifest = {
        "doc_id": doc_id,
        "source_file": os.path.basename(pdf_path),
        "source_path": os.path.abspath(pdf_path),
        "source_sha1": pdf_hash,
        "started_at": started,
        "finished_at": finished,
        "dpi": dpi,
        "ocr_model": model,
        "pages_total": len(pages_info),
        "pages_ok": sum(1 for x in pages if x["status"] == "ok"),
        "pages_error": sum(1 for x in pages if x["status"] == "error"),
        "pages": pages,
        "errors": errors,
    }

    write_manifest(os.path.join(doc_out_dir, "manifest.json"), manifest)
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Folder containing PDF files")
    ap.add_argument("--output", default="./data/raw", help="Output root folder")
    ap.add_argument("--model", default=os.getenv("OLLAMA_MODEL"), help="Ollama model name")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--ollama-url", default=os.getenv("OLLAMA_URL"))
    ap.add_argument("--sleep", type=float, default=0.0, help="Sleep between pages (sec)")
    args = ap.parse_args()

    pdfs = list_pdfs(args.input)
    if not pdfs:
        print("No PDF files found.")
        return

    ensure_dir(args.output)

    all_results = []
    for pdf in pdfs:
        print(f"\n== Ingesting: {pdf}")
        m = ingest_pdf(
            pdf_path=pdf,
            output_root=args.output,
            model=args.model,
            dpi=args.dpi,
            ollama_url=args.ollama_url,
            sleep_sec=args.sleep,
        )
        print(
            f"   doc_id={m['doc_id']} ok={m['pages_ok']}/{m['pages_total']} errors={m['pages_error']}"
        )
        all_results.append(m)

    # Write a global index
    index_path = os.path.join(args.output, "_index.json")
    write_manifest(index_path, {"ingested_at": now_iso_bkk(), "documents": all_results})
    print(f"\nWrote index: {index_path}")


if __name__ == "__main__":
    main()