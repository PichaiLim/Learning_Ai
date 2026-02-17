# RAG Pipeline
 1) [-] ingestion.py        → ได้ raw .md
 2) [-] preprocessing.py    → ได้ clean .md   
 3) [-] chunking.py
 4) [-] embedding.py
 5) [-] vector_store.py
 6) [-] retriever.py
 7) [-] generator.py

---

# Roadmap ทำ RAG แบบเป็นขั้น (ทำทีละชิ้นแล้วรันได้จริง)
## Step A — Ingestion: แปลงเอกสารเป็นข้อความ + เมตาดาต้า

- PDF → text (หรือ OCR ถ้าเป็นสแกน)
- เก็บเป็น “ก้อนข้อมูลดิบ” ก่อน (เช่น JSONL) เพื่อ debug ง่าย

## Step B — Chunking: ตัดข้อความเป็นชิ้น ๆ

- หลักง่าย ๆ:
- ตัดตามหัวข้อ/ย่อหน้า + จำกัดความยาว (เช่น 300–800 tokens)
- ใส่ overlap เล็กน้อย (เช่น 10–20%) กันบริบทขาด
- เก็บ chunk_id, chunk_index, doc_id, page_range

## Step C — Embedding: แปลง chunk เป็นเวกเตอร์

- เลือก embedding model ให้เหมาะภาษาไทย/เอกสารของคุณ
- ได้ผลลัพธ์เป็น vector + เก็บคู่กับ chunk

## Step D — Vector Store / Index: เลือกที่เก็บเวกเตอร์

- ทางเลือกยอดฮิต:
- PostgreSQL + pgvector (เหมาะกับคุณมาก เพราะคุณใช้ PostgreSQL 17 อยู่แล้ว)
- หรือ FAISS/Chroma (ง่ายและเร็วสำหรับต้นแบบ)

## Step E — Retriever: ดึง chunk ที่เกี่ยวข้อง

- ขั้นต่ำเริ่มจาก:
- Similarity search top-k (เช่น k=5–10)
แล้วค่อยอัปเกรดเป็น:
- Hybrid search (BM25 + vector)
- Rerank (เอาโมเดลมาจัดอันดับใหม่ให้แม่นขึ้น)

## Step F — Generator: ประกอบ prompt แล้วให้ LLM ตอบ

Prompt ที่ดีสำหรับ RAG ควรมี:

- “บริบทที่ดึงมา” (พร้อมแหล่งอ้างอิง)
- กติกาว่า ห้ามมโน ถ้าไม่มีข้อมูลในบริบท
- รูปแบบคำตอบที่ต้องการ (bullet, ตาราง, JSON, ฯลฯ)

## Step G — Evaluation: วัดความแม่น/ความคุ้ม

- อย่างน้อยทดสอบ 3 เรื่อง:
- Retrieval accuracy: ดึงถูกเรื่องไหม
- Answer faithfulness: ตอบอิง context จริงไหม
- Latency/Cost: ช้าไปไหม แพงไปไหม

# ขนาด Chunk ควรเท่าไร?
| Use Case | Recommended |
| --- | --- |
| เอกสารทั่วไป | 500–800 tokens |
| คู่มือเทคนิค | 800–1200 tokens |
| สลิป / เอกสารสั้น | 200–400 tokens |