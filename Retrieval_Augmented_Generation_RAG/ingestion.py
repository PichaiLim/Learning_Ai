# import libraries
import os
import argparse
import requests
import json
import fitz  # PyMuPDF

# load ai model
import ollama

# load environment variables
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

# load environment variables
load_dotenv()


# ingestion.py
## PDF -> Images (per page) -> OCR (Ollama Typhoon) -> Markdown per page + manifest.json
# ensure directory exists
def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

### 1. PDF -> Images (per page)
##### 1.1. open pdf
def list_pdfs(input_dir: str) -> List[str]:
    pdfs = []
    for root, _, files in os.walk(input_dir):
        for fn in files:
            if fn.lower().endswith(".pdf"):
                pdfs.append(os.path.join(root, fn))
    return sorted(pdfs)

##### 1.2. render each page of PDF to image
def pdf_to_images(pdf_path:str, out_dir:str, dpi:int=300, image_format:str="png",)-> List[Dict]:
    """
    Render each page of PDF to image.
    Returns list of dict: {page, image_path, width, height}
    """
    ensure_dir(out_dir)
    doc = fitz.open(pdf_path)

    zoom = dpi / 72 # PyMuPDF default is 72 dpi
    mat = fitz.Matrix(zoom, zoom)

    pages_info = [] # list()
    if i in range(len(doc)):
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
def ocr_image_via_ollama(image_path:str, model:str=os.getenv("OLLAMA_MODEL"), ollama_url:str=os.getenv("OLLAMA_URL", "http://localhost:11434"), timeout_sec:int=120,)-> str:
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
            "temperature": os.getenv("temperature", 0.1), # ✅ กำหนด temperature 0.1
            "top_p": os.getenv("top_p", 0.6), # ✅ กำหนด top_p 0.6
            "repeat_penalty": os.getenv("repeat_penalty", 1.1), # ✅ กำหนด repeat_penalty 1.1
            "top_k": os.getenv("top_k", 40), # ✅ กำหนด top_k 40
            "max_tokens": os.getenv("max_tokens", 1000), # ✅ กำหนด max_tokens 1000
        }
    )

    # ✅ ดึง text จาก response ถูกต้อง markdown format
    return response.message.content

    
##### 2.2. return text
### 3. Markdown per page + manifest.json
##### 3.1. save page OCR output as Markdown with metadata header
##### 3.2. return list of dict: {page, image_path, width, height}

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
    parser.add_argument("--timeout", default=120, type=int, required=False, help="Timeout in seconds")

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
        m = {
            "pdf_path": pdf_path,
            "output_root": args.output,
        }

        all_results.append(m)

    print(f"\n== Summary: {len(all_results)} PDFs ingested.")
    print(f"\n== Results: {all_results}")

    # ocr image via ollama
    print("\n== ocr image via ollama")
    ocr_result = ocr_image_via_ollama(
        image_path=args.image_path,
        model=args.model,
        ollama_url=args.ollama_url,
        timeout_sec=args.timeout,
    )
    print(f"\n== ocr_result: {ocr_result}")
    
    

if __name__ == "__main__":
    main()