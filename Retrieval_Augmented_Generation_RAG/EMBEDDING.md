# EMBEDDING.md
## RAG Pipeline — Stage 4: Embedding Layer (Chunks → Vectors)

เอกสารนี้อธิบาย “Embedding Layer” ที่อยู่หลัง **Chunking** และก่อน **Vector Store / Retrieval**  
เป้าหมายคือแปลงข้อความแต่ละ chunk ให้เป็นเวกเตอร์ตัวเลข (embedding) เพื่อใช้ค้นหาความคล้าย (similarity search) ในระบบ RAG

---

## 1) Context (สิ่งที่ทำมาก่อนหน้า)

### 1.1 Ingestion
```
PDF → Images (per page) → OCR (Ollama Typhoon) → pages_md/page_XXX.md + manifest.json
```

### 1.2 Preprocessing
```
data/raw/<doc_id>/
  clean_pages_md/
  preprocess_manifest.json
```

### 1.3 Chunking (อินพุตของ Embedding)
ผลลัพธ์จาก `chunking.py`:
```
data/raw/<doc_id>/
  chunks/
    chunks.jsonl
    chunk_manifest.json
```

ไฟล์ `chunks.jsonl` เป็น JSONL (1 บรรทัด = 1 chunk) โดยมีอย่างน้อย:
- `chunk_id`, `doc_id`, `source_file`
- `page_start`, `page_end`
- `text` (ข้อความ chunk)
- `meta` (metadata เพิ่มเติม)

---

## 2) Embedding Layer คืออะไร?

Embedding คือการแปลงข้อความให้เป็นเวกเตอร์ตัวเลข (เช่น 768 หรือ 1024 มิติ)  
เวกเตอร์นี้ทำให้เราสามารถ:
- เปรียบเทียบ “ความคล้าย” ระหว่างคำถามผู้ใช้กับ chunk ได้
- ดึง chunk ที่เกี่ยวข้องมากที่สุด (Top-K) มาเป็น context ให้ LLM ตอบ

> สำคัญ: โมเดล OCR (เช่น typhoon OCR) มักไม่ใช่ embedding model  
> คุณควรใช้ embedding model โดยเฉพาะ เช่น `nomic-embed-text`, `bge-m3`, ฯลฯ (ตามที่ติดตั้งใน Ollama)

---

## 3) Output ของ Embedding

เมื่อรัน `embedding.py` จะได้:

```
data/raw/<doc_id>/
  embeddings/
    embeddings.jsonl
    embedding_manifest.json
```

### 3.1 embeddings.jsonl
JSONL: 1 บรรทัด = 1 embedding record

ตัวอย่าง:
```json
{
  "chunk_id": "PDPA_abcd_p001_h_0001_1a2b3c4d",
  "doc_id": "PDPA_abcd1234",
  "source_file": "PDPA_thailand.pdf",
  "page_start": 1,
  "page_end": 1,
  "heading_path": ["บทนำ"],
  "text": "...",
  "meta": {...},
  "embedding_model": "nomic-embed-text",
  "embedding_dim": 768,
  "vector": [0.0123, -0.0456, ...],
  "embedded_at": "2026-02-24T..."
}
```

### 3.2 embedding_manifest.json
ไฟล์สรุป:
- จำนวน chunk ทั้งหมดที่นำเข้า
- จำนวนที่ embed สำเร็จ/ล้มเหลว
- รายละเอียด error (ถ้ามี)
- ชื่อ model และ base_url ของ Ollama ที่ใช้

---

## 4) Ollama Embedding Endpoints

ในโค้ดตัวอย่าง `embedding.py` จะพยายามเรียก:

1) `POST {base_url}/api/embeddings` (preferred)  
payload:
```json
{"model":"<embedding_model>","prompt":"<text>"}
```

2) fallback: `POST {base_url}/api/embed`  
payload:
```json
{"model":"<embedding_model>","input":"<text>"}
```

> เหตุผลที่มี fallback: บางเวอร์ชัน/บาง build ของ Ollama ใช้ schema ไม่เหมือนกัน

---

## 5) วิธีรัน (CLI Usage)

### 5.1 ติดตั้ง dependency
```bash
pip install requests
```

### 5.2 รัน embedding
```bash
python embedding.py --doc-dir "PATH_TO/data/raw/<doc_id>" --model "nomic-embed-text"
```

### 5.3 ทดสอบแค่บางส่วนก่อน (แนะนำ)
```bash
python embedding.py --doc-dir "..." --model "nomic-embed-text" --limit 20
```

### 5.4 ตัวอย่าง (Windows)
```bat
python "C:\Users\Public\Public Programs\Learning_Ai\Retrieval_Augmented_Generation_RAG\embedding.py" ^
  --doc-dir "C:\Users\Public\Public Programs\Learning_Ai\Retrieval_Augmented_Generation_RAG\media\output\data\raw\<doc_id>" ^
  --model "nomic-embed-text"
```

---

## 6) อธิบายการทำงานของ embedding.py (ตามส่วนหลัก)

### 6.1 Utilities
- `now_iso_bkk()` : เวลาประทับใน output/manifest
- `ensure_dir()` : สร้างโฟลเดอร์ `embeddings/`
- `read_jsonl()` : อ่าน `chunks.jsonl`
- `write_jsonl()` : เขียน `embeddings.jsonl`
- `write_json()` : เขียน `embedding_manifest.json`
- `safe_float_list()` : บังคับให้ vector เป็น `list[float]` แบบปลอดภัย

### 6.2 Ollama Embedding Client
- `ollama_embed(text, model, base_url, timeout)`  
  เรียก Ollama เพื่อสร้าง embedding
  - ลอง `/api/embeddings` ก่อน
  - ถ้าไม่สำเร็จค่อย fallback ไป `/api/embed`
  - ถ้า error ให้โยนรายละเอียด status/body กลับมาเพื่อ debug

### 6.3 Pipeline Orchestrator
- `embed_doc_dir(doc_dir, model, base_url, ...)`
  1) อ่าน `chunks/chunks.jsonl`
  2) วนทีละ chunk → ส่ง `text` ไปทำ embedding
  3) เขียนผลเป็น `embeddings/embeddings.jsonl`
  4) เก็บ error list ใน `embeddings/embedding_manifest.json`

---

## 7) Best Practices / Notes

- แนะนำทดสอบด้วย `--limit 20` ก่อนเสมอ เพื่อเช็คว่า:
  - endpoint ถูก
  - model ชื่อถูก
  - ได้ embedding vector จริง

- ถ้า error บอกว่า model ไม่พบ ให้:
  - ตรวจด้วย `ollama list`
  - เปลี่ยนเป็น embedding model ที่ติดตั้งแล้ว

- ถ้าเวกเตอร์ขนาดเปลี่ยน (dim ไม่เท่ากัน) ให้ตรวจว่า:
  - คุณใช้ model เดียวกันตลอดทั้ง dataset
  - ไม่ได้สลับ embedding model ระหว่างรัน

---

## 8) Next Step หลัง Embedding

ขั้นต่อไปคือ Vector Store:
1) อ่าน `embeddings/embeddings.jsonl`
2) สร้างตารางใน PostgreSQL (pgvector)
3) INSERT:
   - `chunk_id`, `doc_id`, `page_start`, `text`, `metadata`
   - `vector` (pgvector column)
4) ทำ index เพื่อค้นหา similarity ได้เร็ว

---

## Appendix: Suggested Folder Layout

```
Retrieval_Augmented_Generation_RAG/
  ingestion.py
  preprocessing.py
  chunking.py
  embedding.py
  vector_store.py
  retriever.py
  generator.py

media/
  PDPA_thailand.pdf
  output/
    data/
      raw/
        <doc_id>/
          chunks/
            chunks.jsonl
            chunk_manifest.json
          embeddings/
            embeddings.jsonl
            embedding_manifest.json
```

---

End of Document
