# PREPROCESSING.md
## RAG Pipeline — Stage 2: Preprocessing Layer (OCR Markdown Cleaning)

เอกสารนี้อธิบาย “Preprocessing Layer” ที่อยู่ระหว่าง **Ingestion (OCR → .md)** และ **Chunking**  
เป้าหมายคือทำให้ Markdown ที่ได้จาก OCR “สะอาด + มีโครงสร้าง + พร้อมทำ Chunking/Embedding”

---

## 1) Context (สิ่งที่ทำมาก่อนหน้า)

Ingestion ของโปรเจกต์ทำงานแบบนี้:

```
PDF → Images (per page) → OCR (Ollama Typhoon) → pages_md/page_XXX.md + manifest.json
```

ผลลัพธ์ (ตัวอย่าง):

```
data/raw/<doc_id>/
  manifest.json
  images/
    page_001.png
    ...
  pages_md/
    page_001.md
    page_002.md
    ...
```

ไฟล์ `page_XXX.md` จะมี metadata header แบบนี้:

```md
<!--
source_file: PDPA_thailand.pdf
source_path: ...
doc_id: ...
page: 1
dpi: 300
ingested_at: 2026-02-24T...
ocr_model: typhoon
-->

... OCR text ...
```

---

## 2) Preprocessing Layer คืออะไร?

Preprocessing คือขั้นตอน “ทำความสะอาดข้อความ” เพื่อ:

- ลด noise จาก OCR (ช่องว่างเกิน, เส้นคั่น, เลขหน้า)
- กรอง header/footer ที่ซ้ำทุกหน้า (แบบ baseline)
- Normalize ภาษาไทย/Unicode (แบบเบา ๆ)
- ใส่ **Page Marker** เพื่อช่วย debug และทำ citation ใน RAG
- เก็บ metadata ต่อหน้าไว้เหมือนเดิม (เพิ่ม `preprocessed_at`)

---

## 3) Output ที่ได้จาก Preprocessing

เมื่อรัน `preprocessing.py` จะได้:

```
data/raw/<doc_id>/
  clean_pages_md/
    page_001.md
    page_002.md
    ...
  preprocess_manifest.json
```

ตัวอย่างไฟล์ผลลัพธ์ `clean_pages_md/page_001.md`:

```md
<!--
source_file: PDPA_thailand.pdf
doc_id: PDPA_thailand_abcd1234
page: 1
...
preprocessed_at: 2026-02-24T...
preprocess_version: 1.0
-->

--- PAGE 1 ---

... cleaned text ...
```

---

## 4) วิธีรัน (CLI Usage)

### 4.1 รันกับเอกสาร 1 ชุด (doc directory)

> `--doc-dir` ต้องชี้ไปยังโฟลเดอร์ที่มี `manifest.json`

```bash
python preprocessing.py --doc-dir "PATH_TO/data/raw/<doc_id>"
```

### 4.2 ตัวอย่าง (Windows)

```bat
python "C:\Users\Public\Public Programs\Learning_Ai\Retrieval_Augmented_Generation_RAG\preprocessing.py" ^
  --doc-dir "C:\Users\Public\Public Programs\Learning_Ai\Retrieval_Augmented_Generation_RAG\media\output\data\raw\<doc_id>"
```

---

## 5) อธิบายการทำงานของ `preprocessing.py` (ตามส่วนหลัก)

### 5.1 Utilities
ฟังก์ชันพื้นฐานสำหรับเวลา/ไฟล์/โฟลเดอร์

- `now_iso_bkk()`  
  คืนเวลาปัจจุบันแบบ ISO ใน timezone ไทย (UTC+7)

- `ensure_dir(path)`  
  สร้างโฟลเดอร์ถ้ายังไม่มี เพื่อกัน error ตอนเขียน output

- `read_text(path)` / `write_text(path, text)`  
  อ่าน/เขียนไฟล์ `.md`

- `read_json(path)` / `write_json(path, data)`  
  อ่าน/เขียนไฟล์ `.json` (manifest)

---

### 5.2 Parse Metadata Header (สำคัญมาก)
OCR output ต่อหน้าเป็น markdown ที่มี metadata ใน HTML comment

- `split_md_metadata(md_text) -> (meta_dict, body_text)`  
  แยก metadata header ออกมาเป็น `dict` และคืน body ที่เป็นข้อความจริง

- `build_md_with_metadata(meta, body) -> str`  
  ประกอบไฟล์ `.md` กลับ โดยคง metadata ไว้ และเขียน body ที่ clean แล้ว

> เหตุผล: metadata ช่วยทำ citation/trace ต่อได้ในขั้น Chunking และ RAG Answer

---

### 5.3 Cleaning Rules (Preprocessing Rules)
ชุดกฎที่ใช้ลด noise แบบ baseline (ปรับได้ภายหลัง)

- `normalize_thai_composition_basic(text)`  
  Normalize Unicode (NFC) แบบเบา ๆ เพื่อให้สระ/วรรณยุกต์นิ่งขึ้น

- `remove_page_number_lines(text)`  
  ลบบรรทัดที่เป็น “หน้า 12” / “Page 12” แบบล้วน ๆ (noise)

- `remove_separator_lines(text)`  
  ลบบรรทัดเส้นคั่นยาว เช่น `-----`, `=====` เพื่อลด clutter

- `remove_repeated_header_footer_simple(text)`  
  Baseline: ตัดหัว/ท้ายแบบง่าย (เช่น บรรทัดสั้น ๆ ที่มีคำว่า “บริษัท/รายงาน” หรือ “สงวนลิขสิทธิ์”)
  > ไม่ aggressive เพื่อกันตัดเนื้อหาจริงพลาด  
  > ถ้าเอกสารมี pattern ชัด สามารถอัปเกรดเป็น “เรียนรู้ header/footer ที่ซ้ำข้ามหน้า” ได้

- `normalize_whitespace(text)`  
  ลดช่องว่างซ้ำ + ตัด whitespace ท้ายบรรทัด  
  มีข้อยกเว้น: บรรทัดที่ขึ้นต้นด้วย `|` จะไม่ลด spacing เพื่อไม่ทำลายตาราง Markdown

- `add_page_marker(body, page)`  
  ใส่ marker `--- PAGE N ---` เพื่อให้ chunk/citation ง่าย

- `preprocess_body(body, page)`  
  รวมทุกกฎเป็น pipeline เดียว (จุดนี้เป็นจุดหลักที่ใช้ปรับลำดับ/เพิ่มกฎ)

---

### 5.4 Orchestrator (คุมงานทั้งเอกสาร)
- `preprocess_document_dir(doc_dir)`  
  ทำงานกับเอกสาร 1 ชุด (1 `<doc_id>`):
  1) อ่าน `manifest.json`
  2) วนหน้าแต่ละหน้าใน `pages_md/`
  3) แยก metadata + clean body
  4) เขียนไป `clean_pages_md/`
  5) สรุปผลเป็น `preprocess_manifest.json`

ผลสรุปที่บันทึกใน `preprocess_manifest.json`:
- pages_total, pages_ok, pages_error
- path ของ input/output ต่อหน้า
- errors list สำหรับ debug

---

## 6) Best Practices / Notes

- อย่าลบ header/footer แบบแรงเกินไปตั้งแต่แรก  
  เริ่มจาก baseline แล้วค่อยปรับ rule ตามเอกสารจริง

- ควรเก็บข้อมูล 3 ชั้นเพื่อ debug:
  1) images/page_XXX.png
  2) pages_md/page_XXX.md (raw OCR)
  3) clean_pages_md/page_XXX.md (cleaned)

- Preprocessing เป็นขั้นที่ช่วย RAG “แม่นขึ้นมาก”  
  เพราะ noise จะไปทำให้ embedding และ retrieval เพี้ยนได้

---

## 7) Next Step หลัง Preprocessing

หลังได้ `clean_pages_md/` แล้ว ขั้นต่อไปคือ:

1) Chunking (ตัดเป็นก้อนความหมาย + overlap + metadata)
2) Embedding
3) Vector Store (เช่น pgvector)
4) Retrieval
5) Generation

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
```

---

End of Document
