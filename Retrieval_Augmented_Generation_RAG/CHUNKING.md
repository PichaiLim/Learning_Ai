# CHUNKING.md
## RAG Pipeline — Stage 3: Chunking Layer (Clean Markdown → Chunks)

เอกสารนี้อธิบาย “Chunking Layer” ที่อยู่หลัง **Preprocessing** และก่อน **Embedding**  
เป้าหมายคือแบ่งข้อความที่ clean แล้วให้เป็น “ก้อนข้อมูล” (chunks) ที่ขนาดพอดีสำหรับการทำ embedding และ retrieval ในระบบ RAG

---

## 1) Context (สิ่งที่ทำมาก่อนหน้า)

### 1.1 Ingestion (ทำแล้ว)
```
PDF → Images (per page) → OCR (Ollama Typhoon) → pages_md/page_XXX.md + manifest.json
```

### 1.2 Preprocessing (ทำแล้ว/กำลังทำ)
ผลลัพธ์จาก `preprocessing.py`:
```
data/raw/<doc_id>/
  clean_pages_md/
    page_001.md
    page_002.md
  preprocess_manifest.json
```

ไฟล์ `clean_pages_md/page_XXX.md` จะมี metadata header และ page marker:

```md
<!--
source_file: PDPA_thailand.pdf
doc_id: PDPA_thailand_abcd1234
page: 1
preprocessed_at: 2026-02-24T...
preprocess_version: 1.0
-->

--- PAGE 1 ---

... cleaned text ...
```

---

## 2) Chunking Layer คืออะไร?

Chunking คือขั้นตอนแบ่งข้อความที่ clean แล้วให้เป็นหน่วยเล็กพอดี เพื่อ:

- ทำ **Embedding** ได้แม่นขึ้น (ลด noise และลดความยาวต่อชิ้น)
- ทำ **Retrieval** ได้ตรงประเด็น (ดึงเฉพาะส่วนที่เกี่ยวข้อง)
- ประหยัด token/เวลา ในขั้น generation
- รองรับการอ้างอิง (citation) โดยพก metadata (doc/page/section) ไปกับ chunk

> ถ้าไม่ทำ chunking แล้ว embed ทั้งเอกสาร: retrieval จะเพี้ยน/ช้า และคำตอบจะอ้างอิงยาก

---

## 3) Output ของ Chunking

เมื่อรัน `chunking.py` จะได้:

```
data/raw/<doc_id>/
  chunks/
    chunks.jsonl
    chunk_manifest.json
```

### 3.1 chunks.jsonl
- รูปแบบ JSONL: 1 บรรทัด = 1 chunk
- เหมาะมากสำหรับ pipeline embedding เพราะอ่านทีละบรรทัดได้

ตัวอย่าง 1 บรรทัด:

```json
{"chunk_id":"...","doc_id":"...","source_file":"...","page_start":1,"page_end":1,"heading_path":["บทนำ"],"text":"...","meta":{"chunk_mode":"headings","chunk_index_on_page":1,"chunked_at":"..."}}
```

### 3.2 chunk_manifest.json
ไฟล์สรุป:
- โหมด chunking
- จำนวน chunk ทั้งหมด
- จำนวนหน้า
- error list (ถ้ามี) เพื่อ debug

---

## 4) โหมด Chunking ที่รองรับ (2 แบบ)

### 4.1 Mode: headings (แนะนำถ้าเอกสารมีหัวข้อ)
ใช้ `#`, `##`, `###` ใน Markdown เพื่อแบ่งเป็นส่วน ๆ ก่อน แล้วค่อย pack ให้ไม่เกินขนาดที่กำหนด

**ข้อดี**
- ได้ chunk ที่ “มีความหมาย” และมีเส้นทางหัวข้อ (heading_path)
- retrieval แม่นขึ้น

**เหมาะกับ**
- คู่มือ
- เอกสารนโยบาย/ข้อกำหนด
- เอกสารที่มีหัวข้อชัด

### 4.2 Mode: sliding (แนะนำถ้า OCR ไม่มีหัวข้อชัด)
แบ่งด้วย “หน้าต่างเลื่อน” ตามจำนวนคำ + overlap

**ข้อดี**
- ทนทานกับข้อความ OCR ที่ไม่มีโครงสร้าง
- คุมขนาดได้สม่ำเสมอ

**เหมาะกับ**
- เอกสาร scan ที่ OCR ออกมาเป็นย่อหน้ายาว ๆ
- เอกสารที่หัวข้อหาย/เพี้ยน

---

## 5) ค่าแนะนำ (Recommended Settings)

| สถานการณ์ | max_words | overlap_words | หมายเหตุ |
|---|---:|---:|---|
| เอกสารทั่วไป | 600–800 | 80–140 | ค่าเริ่มต้นดี |
| เอกสารเทคนิคยาว | 800–1200 | 120–200 | เนื้อหาต่อเนื่อง |
| เอกสารสั้น/สลิป | 200–400 | 40–80 | ลดขนาด chunk |

> ในโค้ดตัวอย่าง เราใช้ “จำนวนคำ” แทน token เพื่อหลีกเลี่ยง dependency  
> ถ้าต้องการความแม่นจริง ควรใช้ tokenizer (เช่น tiktoken) ในอนาคต

---

## 6) วิธีรัน (CLI Usage)

### 6.1 รันแบบ headings
```bash
python chunking.py --doc-dir "PATH_TO/data/raw/<doc_id>" --mode headings
```

### 6.2 รันแบบ sliding
```bash
python chunking.py --doc-dir "PATH_TO/data/raw/<doc_id>" --mode sliding --max-words 700 --overlap-words 120
```

### 6.3 ตัวอย่าง (Windows)
```bat
python "C:\Users\Public\Public Programs\Learning_Ai\Retrieval_Augmented_Generation_RAG\chunking.py" ^
  --doc-dir "C:\Users\Public\Public Programs\Learning_Ai\Retrieval_Augmented_Generation_RAG\media\output\data\raw\<doc_id>" ^
  --mode headings
```

---

## 7) อธิบายการทำงานของ chunking.py (ตามส่วนหลัก)

### 7.1 Utilities
- `now_iso_bkk()` : เวลาประทับใน metadata/manifest
- `ensure_dir()` : สร้างโฟลเดอร์ `chunks/`
- `read_text()` : อ่านไฟล์ `.md`
- `read_json()` / `write_json()` : อ่าน/เขียน `manifest.json` / `chunk_manifest.json`
- `write_jsonl()` : เขียน `chunks.jsonl`
- `sha1_text()` : ทำ hash ของข้อความเพื่อทำ chunk_id ที่ไม่ชนกัน
- `count_words()` / `split_words()` : นับ/แยกคำแบบง่ายเพื่อคุมขนาด chunk

### 7.2 Parse Metadata Header
- `split_md_metadata()` : แยก metadata header (`<!-- ... -->`) ออกจาก body ของ markdown  
  เหตุผล: metadata ต้องติดไปกับ chunk เพื่อการอ้างอิงและ debug

### 7.3 Page Marker Helpers
- `extract_page_from_body()` : อ่านเลขหน้าออกจาก `--- PAGE N ---` ถ้ามี
- `remove_page_marker()` : ลบ marker ก่อน chunk เพื่อไม่ให้ซ้ำในทุก chunk
- `normalize_newlines()` : ลดบรรทัดว่างซ้ำ ทำให้ chunk สะอาดและสม่ำเสมอ

### 7.4 Heading-based Chunking
- `split_by_headings()` : แยกเอกสารตามหัวข้อ `# ..` `## ..` `### ..`
- `pack_blocks_to_chunks()` : รวม block หลายส่วนให้ได้ chunk ที่ไม่เกิน `max_words`  
  ถ้า block ใหญ่เกิน → แตกย่อยแบบ sliding ภายใน block  
  ผลลัพธ์จะมี `heading_path` เพื่อระบุเส้นทางหัวข้อของ chunk

### 7.5 Sliding Window Chunking
- `sliding_window_chunks()` : แบ่งข้อความเป็นก้อนด้วยหน้าต่างเลื่อน  
  มี overlap เพื่อกันบริบทขาดตรงรอยต่อ

### 7.6 Orchestrator (คุมงานทั้งเอกสาร)
- `resolve_doc_pages()` : หาไฟล์หน้า input ที่ต้อง chunk  
  - ถ้ามี `preprocess_manifest.json` จะใช้ output จาก `clean_pages_md/`
  - ถ้าไม่มี จะ fallback ไป `pages_md/` จาก ingestion
- `chunk_document_dir()` : วนทุกหน้า → สร้าง chunks ตาม mode → เขียน output เป็น JSONL + manifest

---

## 8) Quality Checklist (เช็คก่อนทำ Embedding)

ก่อนเข้า Embedding แนะนำตรวจ:
- `chunks.jsonl` มี chunk_id ไม่ซ้ำ
- chunk มี `doc_id`, `source_file`, `page_start`
- chunk ไม่สั้นเกินไป (เช็ค min_words)
- ไม่มี header/footer noise ซ้ำในทุก chunk (ถ้ามีให้กลับไปปรับ preprocessing)

---

## 9) Next Step หลัง Chunking

ขั้นต่อไปคือ Embedding:
1) อ่าน `chunks/chunks.jsonl` ทีละบรรทัด
2) ส่ง `text` ไปทำ embedding
3) เก็บ embedding + metadata ลง Vector DB (เช่น PostgreSQL + pgvector)

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
          manifest.json
          images/
          pages_md/
          clean_pages_md/
          preprocess_manifest.json
          chunks/
            chunks.jsonl
            chunk_manifest.json
```

---

End of Document
