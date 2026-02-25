# RAG Pipeline (1–7) — สรุปหน้าที่แต่ละขั้นตอน

ระบบ **RAG: Retrieval-Augmented Generation** มักถูกแบ่งเป็นท่อส่งงาน (pipeline) 7 ขั้นตอนหลัก เพื่อเปลี่ยน “เอกสารดิบ” ให้กลายเป็น “คำตอบจาก LLM ที่อ้างอิงแหล่งข้อมูลได้”

---

## 1) [ingestion.py](ingestion.py) — ดึงข้อมูลเข้า + แปลงเป็น Raw

**หน้าที่**
- อ่านไฟล์ต้นทาง เช่น PDF / DOCX / HTML / TXT
- แปลงเป็นข้อความ/Markdown แบบ “ดิบ” (raw `.md`)
- เก็บ metadata พื้นฐาน เช่น ชื่อไฟล์, หน้า, เวลา, ที่มา

**ผลลัพธ์**
- `raw/*.md` (ยังมี noise: header/footer, เลขหน้า, OCR เพี้ยน, line-break แปลก ๆ ฯลฯ)

---

## 2) [preprocessing.py](preprocessing.py) — ทำความสะอาด + ทำให้เป็นมาตรฐาน (Clean)

**หน้าที่**
- ลบสิ่งรบกวน: header/footer ซ้ำ ๆ, เลขหน้า, watermark
- แก้รูปแบบข้อความ: ช่องว่าง, ตัวอักษรพิเศษ, unicode normalization
- (ถ้าเป็นไทย) อาจมี: normalize สระ/วรรณยุกต์, แก้ spacing เพี้ยนจาก OCR

**ผลลัพธ์**
- `clean/*.md` (อ่านรู้เรื่องขึ้น + พร้อมนำไป chunk)

---

## 3) [chunking.py](chunking.py) — หั่นเอกสารเป็นชิ้น ๆ (Chunks)

**หน้าที่**
- แบ่ง `clean.md` เป็น “chunk” ขนาดพอเหมาะสำหรับ embedding/retrieval
- ใช้กติกาเชิงโครงสร้าง: หัวข้อ (H1/H2), ย่อหน้า, bullet, ตาราง
- ตั้งค่า `chunk_size` / `overlap` เพื่อไม่ตัดบริบทหาย

**ผลลัพธ์**
- รายการ chunks พร้อม metadata  
  (เช่น `doc_id`, `chunk_id`, `heading`, `page`, `offsets`)

---

## 4) [embedding.py](embedding.py) — แปลง chunk เป็นเวกเตอร์ (Vectors)

**หน้าที่**
- ส่งข้อความของแต่ละ chunk เข้า embedding model
- ได้เวกเตอร์ตัวเลข (เช่น 768/1024/1536 มิติ) เพื่อใช้ค้นหาเชิงความหมาย (semantic)

**ผลลัพธ์**
- ชุดข้อมูลต่อ chunk: `(chunk_text, metadata, embedding_vector)`

---

## 5) [vector_store.py](vector_store.py) — ที่เก็บ/ดัชนีเวกเตอร์

**หน้าที่**
- บันทึกเวกเตอร์ + metadata ลงฐานข้อมูลเวกเตอร์  
  (เช่น FAISS / Chroma / pgvector / Milvus)
- สร้าง index เพื่อให้ค้นหา “ใกล้เคียง” ได้เร็ว (ANN index)

**ผลลัพธ์**
- Vector DB/Index ที่พร้อมให้ query และ filter ด้วย metadata

---

## 6) [retriever.py](retriever.py) — ตัวค้นคืน (Search/Recall)

**หน้าที่**
- รับคำถามผู้ใช้ → สร้าง query embedding
- ค้นหา `top-k` chunks ที่ใกล้เคียงจาก vector store
- อาจทำ rerank เพิ่ม (เช่น cross-encoder) + filter ตาม metadata (เอกสาร/หมวด/วันที่)

**ผลลัพธ์**
- “Context” ที่คัดมาแล้ว (chunks + แหล่งอ้างอิง)

---

## 7) [generator.py](generator.py) — ตัวตอบ (LLM Answering)

**หน้าที่**
- เอา “คำถาม + context ที่ retrieve มา” ป้อนเข้า LLM
- สั่งให้ตอบแบบอ้างอิงแหล่งที่มา/สรุป/ทำขั้นตอน ฯลฯ
- อาจมี logic กันหลอน: ถ้า context ไม่พอ → บอกไม่แน่ใจ/ขอข้อมูลเพิ่ม

**ผลลัพธ์**
- คำตอบสุดท้าย (พร้อม citations ถ้าระบบรองรับ)

---

## ภาพรวมการไหลของข้อมูล (Data Flow)

ต้นทางเอกสาร  
→ [ingestion.py](ingestion.py) (raw)  
→ [preprocessing.py](preprocessing.py) (clean)  
→ [chunking.py](chunking.py) (chunks)  
→ [embedding.py](embedding.py) (vectors)  
→ [vector_store.py](vector_store.py) (index/db)  
→ [retriever.py](retriever.py) (top-k context)  
→ [generator.py](generator.py) (answer)

