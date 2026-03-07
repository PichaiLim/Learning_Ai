# RETRIEVAL.md
## RAG Pipeline — Stage 6: Retrieval (User Question → Query Embedding → Top‑K Chunks)

เอกสารนี้อธิบาย “Retrieval Layer” แบบใช้งานได้จริงกับโปรเจกต์คุณ (PostgreSQL 17 + pgvector + Ollama)

> เป้าหมาย: เมื่อผู้ใช้ “พิมพ์คำถาม” ระบบจะ **ดึงข้อมูลที่เกี่ยวข้องที่สุด** จากฐานข้อมูลเวกเตอร์ (pgvector) เพื่อนำไปให้ LLM ตอบใน Stage 7

---

## 1) Retrieval อยู่ตรงไหนใน Pipeline

```
Ingestion → Preprocessing → Chunking → Embedding → Vector Store → Retrieval → Generation
```

ก่อนเริ่ม Stage 6 ต้องมี:
- มีข้อมูลในตาราง `rag_chunks` แล้ว (จาก `vector_store.py`)
- มี Ollama embedding model สำหรับ “embed คำถาม” (เช่น `nomic-embed-text`, `bge-m3`)

---

## 2) Input / Output

### Input
- `question` : ข้อความคำถามจากผู้ใช้
- `top_k` : จำนวน chunk ที่อยากได้ (เช่น 5 หรือ 10)
- `doc_id` (optional) : ถ้าอยากจำกัดค้นหาในเอกสารเดียว

### Output
รายการ chunk ที่เกี่ยวข้องมากที่สุด (Top‑K) โดยมี:
- `chunk_id`, `doc_id`, `source_file`
- `page_start`, `page_end`
- `heading_path`
- `text` (เนื้อหา chunk)
- `meta`
- `cosine_distance` (ค่ายิ่งน้อยยิ่งคล้าย)

---

## 3) หลักการทำงาน (Step-by-step)

### Step 1: Query Embedding
นำ `question` ไปสร้าง embedding vector ด้วย embedding model

- Endpoint หลัก (preferred):
  - `POST /api/embeddings` ด้วย payload:
    ```json
    {"model":"<EMBED_MODEL>","prompt":"<question>"}
    ```

- Fallback:
  - `POST /api/embed` ด้วย payload:
    ```json
    {"model":"<EMBED_MODEL>","input":"<question>"}
    ```

> ควรใช้ embedding model “ตัวเดียวกับที่ใช้ embed chunks” เพื่อให้เวกเตอร์อยู่ใน space เดียวกัน

### Step 2: Similarity Search ใน pgvector
ใช้ cosine distance:

- operator: `vector <=> qvec`
- เรียงจาก “ใกล้สุด” ไป “ไกลสุด”

ตัวอย่าง SQL:
```sql
SELECT chunk_id, doc_id, source_file, page_start, page_end, heading_path, text, meta,
       (vector <=> $1) AS cosine_distance
FROM rag_chunks
ORDER BY vector <=> $1
LIMIT 5;
```

### Step 3: (Optional) Filtering
ถ้าต้องการจำกัดขอบเขต:
- filter ตาม `doc_id`
- หรือ filter ตาม metadata ใน `meta` (jsonb)

ตัวอย่าง filter doc_id:
```sql
... WHERE doc_id = $2 ...
```

---

## 4) ตั้งค่า (Environment Variables) ที่แนะนำ

ใน `.env` (ภายในโปรเจกต์ แต่ไม่ commit):
```env
DATABASE_URL=postgresql://postgres:postgres@db:5432/ragdb

# Ollama รันที่เครื่อง host:
OLLAMA_URL=http://host.docker.internal:11434

# embedding model:
EMBED_MODEL=nomic-embed-text

TOP_K=5
```

---

## 5) ใช้งานด้วย `retriever.py`

### 5.1 ทดสอบเรียกแบบ CLI
ใน container `app`:
```bash
python retriever.py --question "PDPA คืออะไร" --top-k 5
```

### 5.2 ทดสอบค้นหาเฉพาะ doc_id
```bash
python retriever.py --question "ข้อมูลส่วนบุคคลคืออะไร" --top-k 5 --doc-id PDPA_abcd1234
```

### 5.3 ใช้เป็นฟังก์ชันในโค้ด
```python
from retriever import retrieve_top_k

retrieved = retrieve_top_k(
    question="PDPA คืออะไร",
    top_k=5,
)
print(retrieved["results"][0]["text"])
```

---

## 6) การปรับคุณภาพ Retrieval (ของจริงที่ใช้บ่อย)

### 6.1 เลือก Top‑K ที่เหมาะ
- `top_k=3` ถ้าเอกสารสั้น/คำถามตรง
- `top_k=5–10` ถ้าเอกสารยาว/คำถามกว้าง
- มากเกินไป → prompt บวม/LLM หลุดประเด็น

### 6.2 Metadata Filters
แนะนำให้ใส่ metadata ใน `meta` ตั้งแต่ chunking/preprocessing เช่น:
- `doc_type`, `language`, `department`, `year`
แล้ว filter ใน SQL ด้วย `meta->>'doc_type' = 'policy'` เป็นต้น

### 6.3 Hybrid Retrieval (อนาคต)
ผสม BM25 (text search) + vector search เพื่อกัน “คีย์เวิร์ดเฉพาะ” หลุด  
(ทำได้ด้วย PostgreSQL full‑text หรือ Elasticsearch)

### 6.4 Reranking (Optional)
หลังได้ Top‑K จาก vector search แล้ว:
- ใช้ reranker (cross‑encoder) จัดลำดับใหม่
- หรือใช้ LLM สั้น ๆ จัดอันดับใหม่  
*(ถ้าคุณอยาก ผมทำ `reranker.py` เพิ่มให้ได้)*

---

## 7) Troubleshooting

### 7.1 ได้ผลลัพธ์ไม่ตรง/หลุด
เช็ค:
- embed model ของ query ตรงกับ embed model ของ chunks ไหม
- chunking เล็ก/ใหญ่เกินไปไหม
- preprocessing ยังมี header/footer noise ซ้ำไหม

### 7.2 connect DB ไม่ได้
- ใน docker compose ต้องใช้ host `db` (ไม่ใช่ localhost)
- ตรวจ `DATABASE_URL`

### 7.3 เรียก Ollama ไม่ได้จาก container
- ตั้ง `OLLAMA_URL=http://host.docker.internal:11434`
- Linux ต้องมี `extra_hosts: host.docker.internal:host-gateway`

---

End of Document
