# ✅ import libraries
import os
import argparse
import requests
import re
import json
import fitz  # PyMuPDF
import hashlib
from PIL import Image
# ✅ load ai model
import ollama

# ✅ load environment variables
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

# ✅ load environment variables
load_dotenv()


# ✅ ingestion.py
## PDF -> Images (per page) -> OCR (Ollama Typhoon) -> Markdown per page + manifest.json
### ✅ Util functions
def now_iso_bkk()->str:
    return datetime.now(timezone(timedelta(hours=7))).isoformat(timespec="seconds")

##### ✅ 0.1. ensure directory exists
def ensure_dir(path: str) -> None:
    """
    Ensure directory exists.
    """
    os.makedirs(path, exist_ok=True)

def slugify_filename(name:str)->str:
    """
    Slugify filename.
    """
    # ทำ id ให้ปลอดภัยสำหรับ path
    name = os.path.splitext(os.path.basename(name))[0]
    # name = re.sub(r"[^a-zA-Z0-9\-_\.]", "_", name, flags=re.UNICODE)
    name = re.sub(r"[^\w\-]+", "_", name, flags=re.UNICODE)
    return name

def sha1_of_file(path: str)->str:
    """
    Calculate SHA-1 hash of file.
    """
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

### 1. PDF -> Images (per page)
##### 1.1. open pdf
def list_pdfs(input_dir: str) -> List[str]:
    """
    List all PDF files in directory.
    """
    pdfs = []
    for root, _, files in os.walk(input_dir):
        for fn in files:
            if fn.lower().endswith(".pdf"):
                pdfs.append(os.path.join(root, fn))
    return sorted(pdfs)

##### 1.2. render each page of PDF to image
def pdf_to_images(pdf_path:str, out_dir:str, dpi:int=300, image_format:str="png")-> List[Dict]:
    """
    Render each page of PDF to image.
    Returns list of dict: {page, image_path, width, height}
    """
    ensure_dir(out_dir)
    doc = fitz.open(pdf_path)

    zoom = dpi / 72 # PyMuPDF default is 72 dpi
    mat = fitz.Matrix(zoom, zoom)

    pages_info = [] # list()
    for i in range(len(doc)):
        page = doc.load_page(i) # 
        pix = page.get_pixmap(matrix=mat, alpha=False)
        image_path = os.path.join(out_dir, f"page_{i+1:03d}.{image_format}")
        pix.save(image_path)

        pages_info.append({
            "page": i + 1,
            "image_path": image_path,
            "width": pix.width,
            "height": pix.height,
        })
    
    doc.close()
    return pages_info

##### 1.3. save image
##### 1.4. return list of dict: {page, image_path, width, height}
### 2. OCR (Ollama Typhoon)
##### 2.1. call ollama generate API with an image to do OCR-like extraction
##### 2.2. return text markdown
def resize_image(image_path:str, max_dim:int=1024) -> str:
    """
    Resize image so longest side <= max_dim.
    Saves resized copy with _resized suffix, returns new path.
    """
    img = Image.open(image_path)
    w, h = img.size
    if max(w, h) <= max_dim:
        return image_path  # no resize needed
    scale = max_dim / max(w, h)
    new_w, new_h = int(w * scale), int(h * scale)
    img_resized = img.resize((new_w, new_h), Image.LANCZOS)
    base, ext = os.path.splitext(image_path)
    resized_path = f"{base}_resized{ext}"
    img_resized.save(resized_path)
    return resized_path

def ocr_image_via_ollama(image_path:str, model:str=os.getenv("OLLAMA_MODEL"), ollama_url:str=os.getenv("OLLAMA_URL", "http://localhost:11434"), timeout_sec:int=os.getenv("OLLAMA_TIMEOUT", 120),)-> str:
    """
    Call Ollama generate API with an image to do OCR-like extraction.
    Many vision models accept base64 images. We'll send base64 in 'images'.

    IMPORTANT:
    - Your typhoon model must support vision/OCR style input.
    - If your model expects a different endpoint or schema, adjust here.
    """
    import base64
    print(f"\n== image_path: {image_path}")

    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    """ markdown format """
    prompt = (
        "Instructions:\n"
        "- Only return the clean Markdown.\n"
        "- Do not include any explanation or extra text.\n"
        "- You must include all information on the page.\n\n"

        "Formatting Rules:\n"
        "- Tables: Render tables using <table>...</table> in clean HTML format.\n"
        "- Equations: Render equations using LaTeX syntax with inline ($...$) and block ($$...$$).\n"
        "- Images/Charts/Diagrams: Wrap any clearly defined visual areas (e.g. charts, diagrams, pictures) in:\n\n"

        "<figure>\n"
        "Describe the image’s main elements (people, objects, text), note any contextual clues (place, event, culture), mention visible text and its meaning, provide deeper analysis when relevant (especially for financial charts, graphs, or documents), comment on style or architecture if relevant, then give a concise overall summary. Describe in Thai.\n"
        "</figure>\n"

        "- Page Numbers: Wrap page numbers in <page_number>...</page_number> (e.g., <page_number>14</page_number>).\n"
        "- Checkboxes: Use ☐ for unchecked and ☑ for checked boxes.\n"
    )
    
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "images": [img_b64],
    }
    """

    """ json format """
    """prompt = (
        "อ่านข้อความในภาพนี้ทั้งหมด "
        "แล้ว return เป็น JSON format ดังนี้เท่านั้น:\n"
        "{\n"
        '  "title": "หัวข้อหลักของเอกสาร",\n'
        '  "content": "เนื้อหาทั้งหมดในภาพ",\n'
        '  "tables": [],\n'
        '  "lists": [],\n'
        '  "pages": []\n'
        "}\n"
        "ห้าม return ข้อความอื่นนอกจาก JSON และอย่าเติมข้อมูลที่ไม่มีในภาพ"
    )
    """

    # ✅ ใช้ Client เพื่อกำหนด timeout และ host
    client = ollama.Client(
        host=ollama_url, # ✅ กำหนด host
        timeout=timeout_sec, # ✅ กำหนด timeout
    )

    response = client.chat(
        model=model,
        messages=[
            {
                "role": "user", # ✅ กำหนด role
                "content": prompt, # ✅ ส่ง prompt ใน message
                "images": [img_b64],  # ✅ ส่ง image ใน message
            }
        ],
        # format='json', # ✅ ไม่ต้องใช้ format='json' เพราะเราส่ง markdown format
        options={
            "temperature": float(os.getenv("temperature", "0.1")), # ✅ กำหนด temperature 0.1
            "top_p": float(os.getenv("top_p", "0.6")), # ✅ กำหนด top_p 0.6
            "repeat_penalty": float(os.getenv("repeat_penalty", "1.1")), # ✅ กำหนด repeat_penalty 1.1
            "top_k": int(os.getenv("top_k", "40")), # ✅ กำหนด top_k 40
            "max_tokens": int(os.getenv("max_tokens", "1000")), # ✅ กำหนด max_tokens 1000
        }
    )

    # ✅ ดึง text จาก response ถูกต้อง markdown format
    return response.message.content

def write_page_markdown(output_path:str, text:str, metadata:Dict)->None:
    """
    Write page markdown to file.
    Save page OCR output as Markdown with metadata header.
    """
    header = (
        "<!--\n"
        + "\n".join([f"{k}: {v}" for k, v in metadata.items()])
        + "\n-->\n\n"
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header)
        f.write(text)
        f.write("\n")

def write_manifest(out_path: str, manifest: Dict) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


### 3. Markdown per page + manifest.json
##### 3.1. save page OCR output as Markdown with metadata header
##### 3.2. return list of dict: {page, image_path, width, height}
def ingest_pdf(pdf_path:str, output_root:str, model:str, dpi:int=300, ollama_url:str = os.getenv("OLLAMA_URL", "htpp://localhost:11434"), sleep_sec:float = 0.0) -> Dict:
    """
    Ingest a single PDF:
        - render page to images
        - OCR each image
        - write page__xxx.md
        --- write manifest.json
        --- return list of dict: {page, image_path, width, height}
    """
    # ✅ คำนวน hash
    pdf_hash = sha1_of_file(pdf_path)
    base_id = slugify_filename(name=pdf_path)
    doc_id = f"{base_id}_{pdf_hash[:8]}"

    # print(f"PDF Hash: {pdf_hash}")
    # print(f"Base ID: {base_id}")
    # print(f"Document ID: {doc_id}")
    # print("="*80)

    # ✅ สร้าง output directory
    doc_out_dir = os.path.join(output_root, doc_id)
    img_dir = os.path.join(doc_out_dir, 'images')
    md_dir = os.path.join(doc_out_dir, 'pages_md')

    # ✅ สร้าง directory
    ensure_dir(doc_out_dir)
    ensure_dir(img_dir)
    ensure_dir(md_dir)

    # ✅ บันทึก started at
    started = now_iso_bkk()

    # print(f"Ingesting PDF: {pdf_path}")
    # print(f"Output directory: {doc_out_dir}")
    # print(f"Started at: {started}")
    # print("="*80)

    # 1) PDF -> Images
    pages_info = pdf_to_images(pdf_path=pdf_path, out_dir=img_dir, dpi=dpi, image_format="png")

    pages = []
    errors = []

    # 2) OCR each page
    for page in pages_info:
        page_no = page['page']
        image_path = page['image_path']
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
            "ollama_url": ollama_url,
        }

        # print(meta)
        # print("="*80)

        # ✅ retry with progressively smaller images on GGML errors
        retry_sizes = [None, 1024, 768, 512]  # None = original size
        success = False
        last_error = None

        for max_dim in retry_sizes:
            try:
                # ✅ resize image if needed
                ocr_path = image_path
                if max_dim is not None:
                    ocr_path = resize_image(image_path, max_dim=max_dim)

                # ✅ ดึง text จาก image
                text_md = ocr_image_via_ollama(
                    image_path=ocr_path,
                    model=model,
                    ollama_url=ollama_url
                )
                # ✅ บันทึก text เป็น markdown
                write_page_markdown(output_path=md_path, text=text_md, metadata=meta)
                # ✅ เพิ่ม metadata ลง list
                resized_note = f" (resized to max {max_dim}px)" if max_dim else ""
                pages.append(
                    {
                        "page": page_no,
                        "image_path": os.path.relpath(image_path, doc_out_dir),
                        "md_path": os.path.relpath(md_path, doc_out_dir),
                        "width": page['width'],
                        "height": page['height'],
                        "status": "ok" + resized_note,
                    }
                )
                success = True
                break  # ✅ success, no need to retry
            except Exception as e:
                last_error = e
                if "GGML_ASSERT" in str(e) and max_dim != retry_sizes[-1]:
                    dim_label = max_dim or 'original'
                    next_dim = retry_sizes[retry_sizes.index(max_dim) + 1]
                    print(f"   Page {page_no}: GGML error at {dim_label}, retrying with max {next_dim}px...")
                    continue
                else:
                    # print(f"   Page {page_no}: non-GGML error or last retry, give up")
                    break  # non-GGML error or last retry, give up

        if not success:
            # ✅ เพิ่ม error ลง list
            errors.append({"page": page_no, "error": str(last_error)})
            pages.append({
                "page": page_no,
                "image_path": os.path.relpath(image_path, doc_out_dir),
                "md_path": None,
                "width": page['width'],
                "height": page['height'],
                "error": str(last_error),
                "status": "error",
            })
        
        # ✅ รอ sleep_sec
        if sleep_sec > 0:
            time.sleep(sleep_sec)

    # ✅ บันทึก manifest
    finished = now_iso_bkk()

    # ✅ สร้าง manifest
    manifest = {
        "doc_id": doc_id,
        "source_file": os.path.basename(pdf_path),
        "source_path": os.path.abspath(pdf_path),
        "source_sha1": pdf_hash,
        "started_at": started,
        "finished_at": finished,
        "dpi": dpi,
        "ocr_model": model,
        "ollama_url": ollama_url,
        "pages_total": len(pages_info),
        "pages_ok": sum(1 for x in pages if x["status"] == "ok"),
        "pages_error": sum(1 for x in pages if x["status"] == "error"),
        "pages": pages,
        "errors": errors,
    }

    # ✅ บันทึก manifest
    write_manifest(os.path.join(doc_out_dir, "manifest.json"), manifest)
    return manifest
            

### 4. Main function
def main():
    print("Ingesting PDF to Markdown") # Title name
    print("========================================"*5)

    parser = argparse.ArgumentParser(description="Ingest PDF to Markdown")
    # pdf
    parser.add_argument("--input", default=str(Path(__file__).parent / 'media'), type=str, required=False, help="Input directory")
    parser.add_argument("--output", default=str(Path(__file__).parent / 'data/raw'), type=str, required=False, help="Output directory")

    # ollama
    parser.add_argument("--image_path", default=str(Path(__file__).parent / 'media'/'output'/'images'/'page_1.jpeg'), type=str, required=False, help="Image path")
    parser.add_argument("--ollama_url", default=os.getenv("OLLAMA_URL", "http://localhost:11434"), type=str, required=False, help="Ollama URL")
    parser.add_argument("--model", default=os.getenv("OLLAMA_MODEL", "scb10x/typhoon-ocr1.5-3b"), type=str, required=False, help="Ollama model")
    parser.add_argument("--timeout", default=os.getenv("OLLAMA_TIMEOUT", 120), type=int, required=False, help="Timeout in seconds")
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--sleep_sec", type=float, default=0.0, help="Sleep between pages (sec)")

    args = parser.parse_args()

    # list pdf
    pdfs = list_pdfs(args.input)
    if not pdfs:
        print("No PDF files found in the input directory.")
        return
    
    ensure_dir(args.output)
    
    all_results = [] # list()
    for pdf_path in pdfs:
        print(f"\n== Ingesting: {pdf_path}")
        m = ingest_pdf(
            pdf_path=pdf_path,
            output_root=args.output,
            model=args.model,
            dpi=args.dpi,
            ollama_url=args.ollama_url,
            sleep_sec=args.sleep_sec,
        )
        print(
            f"   doc_id={m['doc_id']} ok={m['pages_ok']}/{m['pages_total']} errors={m['pages_error']}"
        )

        all_results.append(m)

    print(f"\n== Summary: {len(all_results)} PDFs ingested.")
    print(f"\n== Results: {all_results}")

    # ocr image via ollama
    # print("\n== ocr image via ollama")
    # ocr_result = ocr_image_via_ollama(
    #     image_path=args.image_path,
    #     model=args.model,
    #     ollama_url=args.ollama_url,
    #     timeout_sec=args.timeout,
    # )
    # print(f"\n== ocr_result: {ocr_result}")
    
    

if __name__ == "__main__":
    main()