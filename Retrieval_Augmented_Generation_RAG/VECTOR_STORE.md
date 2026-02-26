# VECTOR_STORE.md
## RAG Pipeline — Stage 5: Vector Store Layer (Embeddings → PostgreSQL + pgvector)

เอกสารนี้อธิบายการใช้งาน **`vector_store.py`** แบบละเอียด:
- อธิบายโค้ดสำคัญทีละส่วน
- วิธีติดตั้ง dependency
- วิธีเตรียม PostgreSQL + pgvector (โดยเฉพาะบน Docker)
- วิธีเชื่อมต่อฐานข้อมูล “หลายรูปแบบ” (รันบน Host / รันใน Container / Docker Compose)
- วิธีรัน, ตรวจผล, และแก้ปัญหาที่พบบ่อย

> เป้าหมาย: เอา `embeddings.jsonl` ที่ได้จาก Stage 4 (Embedding) ไปเก็บลง PostgreSQL (pgvector) เพื่อทำ similarity search ได้เร็วและอ้างอิงได้

---

## 0) Quick Map: Vector Store อยู่ตรงไหนใน Pipeline

```
Ingestion  →  Preprocessing  →  Chunking  →  Embedding  →  Vector Store  →  Retrieval  →  Generation
```

อินพุตของ Stage นี้:
```
data/raw/<doc_id>/embeddings/embeddings.jsonl
```

เอาต์พุตของ Stage นี้:
- ข้อมูลถูก INSERT/UPSERT ลงตาราง PostgreSQL: `rag_chunks`
- มี index สำหรับค้นหาเวกเตอร์ (HNSW) และ filter ตาม doc/source

---

## 1) สิ่งที่ต้องมี (Prerequisites)

### 1.1 ต้องมี embeddings.jsonl ก่อน
ไฟล์นี้มาจาก `embedding.py` (Stage 4)

โครงสร้างขั้นต่ำต่อ 1 บรรทัด:
- `chunk_id` (ต้อง unique)
- `doc_id`
- `source_file`
- `page_start`, `page_end`
- `text`
- `meta` (dict)
- `embedding_model`
- `embedding_dim`
- `vector` (list[float])

### 1.2 PostgreSQL ต้องมี pgvector
ใน DB ต้องสามารถรันได้:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

> ถ้าเป็น Docker แนะนำใช้ image ที่มี pgvector มาให้เลย เช่น `pgvector/pgvector:pg17`

---

## 2) ติดตั้ง (Installation)

### 2.1 Python dependencies
ติดตั้งใน venv หรือใน container:
```bash
pip install psycopg[binary] pgvector
```

- `psycopg[binary]` = psycopg v3 (driver PostgreSQL)
- `pgvector` = adapter ให้ psycopg เข้าใจชนิดข้อมูล `vector(...)`

> ถ้าคุณใช้ `requirements.txt` ให้เพิ่ม:
```
psycopg[binary]
pgvector
```

### 2.2 ตรวจว่า pgvector ใช้ได้
หลังเชื่อมต่อ DB แล้วลอง:
```sql
SELECT extname FROM pg_extension WHERE extname='vector';
```

---

## 3) เตรียม PostgreSQL + pgvector บน Docker (แนะนำ)

### 3.1 Docker run (เร็วสุด)
```bash
docker run --name pgvector17 -d \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=ragdb \
  -p 5432:5432 \
  pgvector/pgvector:pg17
```

เช็คว่า container รันอยู่:
```bash
docker ps
```

ลองเช็ค extension:
```bash
docker exec -it pgvector17 psql -U postgres -d ragdb -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 3.2 Docker Compose (แนะนำสำหรับโปรเจกต์)
`docker-compose.yml` ตัวอย่าง:

```yaml
services:
  db:
    image: pgvector/pgvector:pg17
    container_name: rag_db
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: ragdb
    ports:
      - "5432:5432"
    volumes:
      - rag_pgdata:/var/lib/postgresql/data

volumes:
  rag_pgdata:
```

รัน:
```bash
docker compose up -d
```

---

## 4) การเชื่อมต่อฐานข้อมูล (Connection Patterns) — ใช้แบบไหนขึ้นกับคุณ

`vector_store.py` รับพารามิเตอร์:
- `--db-url` : connection string ของ PostgreSQL

รูปแบบมาตรฐาน:
```
postgresql://<user>:<password>@<host>:<port>/<database>
```

ด้านล่างคือ “รูปแบบที่ใช้จริง” ตามสถานการณ์

---

### Pattern A) รัน Python บนเครื่อง Host (Windows/macOS/Linux) → เชื่อมไป Docker DB
เงื่อนไข:
- container Postgres ต้องเปิด port ออกมาที่ host เช่น `-p 5432:5432`

ใช้:
```
postgresql://postgres:postgres@localhost:5432/ragdb
```

ตัวอย่างรัน:
```bash
python vector_store.py --doc-dir "PATH_TO/data/raw/<doc_id>" \
  --db-url "postgresql://postgres:postgres@localhost:5432/ragdb"
```

> Windows: อย่าลืมครอบ path ที่มีช่องว่างด้วย `"`

---

### Pattern B) รัน Python “ใน container app” (Docker Compose เดียวกัน) → เชื่อมไป service db
เงื่อนไข:
- app และ db อยู่ใน network ของ compose เดียวกัน
- host ต้องเป็น “ชื่อ service” ไม่ใช่ localhost

ใช้:
```
postgresql://postgres:postgres@db:5432/ragdb
```

ตัวอย่าง:
```bash
python vector_store.py --doc-dir "/app/media/output/data/raw/<doc_id>" \
  --db-url "postgresql://postgres:postgres@db:5432/ragdb"
```

> เหมาะมากสำหรับ cross-platform เพราะไม่สน OS และไม่ติด path ช่องว่างของ Windows

---

### Pattern C) DB อยู่บนเครื่อง/เซิร์ฟเวอร์อื่น (LAN/VPS/NAS)
ใช้ host เป็น IP หรือ domain:
```
postgresql://postgres:postgres@192.168.1.50:5432/ragdb
```

อย่าลืม:
- เปิดพอร์ต
- ตั้ง `pg_hba.conf`/firewall ให้เข้าถึงได้
- SSL (ถ้าต้องการ)

---

## 5) วิธีใช้ vector_store.py (Step-by-step)

### 5.1 ตรวจว่ามีไฟล์ input
ต้องมี:
```
<doc_dir>/embeddings/embeddings.jsonl
```

### 5.2 รันคำสั่ง
```bash
python vector_store.py --doc-dir "PATH_TO/data/raw/<doc_id>" \
  --db-url "postgresql://postgres:postgres@localhost:5432/ragdb"
```

พารามิเตอร์เสริม:
- `--batch-size 200` : จำนวนแถวต่อ batch (เพิ่มได้ถ้าเครื่องแรง)
- `--no-setup` : ไม่สร้าง extension/table (ถ้าคุณสร้างเองแล้ว)
- `--no-index` : ไม่สร้าง index (ถ้าคุณอยากสร้างเอง/ควบคุมเอง)

ตัวอย่าง “ไม่สร้าง table/index”:
```bash
python vector_store.py --doc-dir "..." --db-url "..." --no-setup --no-index
```

---

## 6) ตารางที่สร้าง (Schema) และเหตุผล

`vector_store.py` จะสร้างตารางนี้ถ้ายังไม่มี:

- `chunk_id TEXT PRIMARY KEY` : key หลักของ chunk
- `doc_id TEXT` : ใช้ filter ตามเอกสาร
- `source_file TEXT` : ใช้ filter ตามไฟล์
- `page_start/page_end INT` : ใช้ citation/อ้างอิงหน้า
- `heading_path TEXT[]` : เก็บเส้นทางหัวข้อ (ถ้ามี)
- `text TEXT` : เนื้อหา chunk
- `meta JSONB` : metadata ทั้งหมด
- `embedding_model TEXT`
- `embedding_dim INT`
- `vector VECTOR(dim)` : คอลัมน์เวกเตอร์ pgvector
- `embedded_at TIMESTAMPTZ`
- `inserted_at TIMESTAMPTZ`

### Index ที่สร้าง
- `idx_rag_chunks_doc_id` : เร็วเวลาคัดเฉพาะเอกสาร
- `idx_rag_chunks_source_file` : เร็วเวลาคัดตามไฟล์
- `idx_rag_chunks_vector_hnsw` : เร็วเวลาค้นหา similarity (cosine)

> ถ้า pgvector/pg เวอร์ชันคุณไม่รองรับ hnsw index จะ error → ให้แจ้งผม ผมจะปรับเป็น ivfflat ให้

---

## 7) อธิบายโค้ด vector_store.py (ส่วนสำคัญ)

### 7.1 การเปิด pgvector + สร้าง schema
- `ensure_pgvector_enabled(conn)`  
  รัน `CREATE EXTENSION IF NOT EXISTS vector;`

- `ensure_table(conn, embedding_dim)`  
  สร้างตาราง `rag_chunks` โดยกำหนด `VECTOR(embedding_dim)`  
  > dim ต้อง “ตรง” กับ embedding model ที่ใช้

- `ensure_indexes(conn)`  
  สร้าง index ทั้ง filter index และ vector index (HNSW cosine)

### 7.2 การ upsert
- `UPSERT_SQL`  
  INSERT แล้วถ้า `chunk_id` ซ้ำ → UPDATE ข้อมูลใหม่  
  ทำให้รันซ้ำได้ ไม่ต้องลบข้อมูลเก่า

### 7.3 แปลง record จาก embeddings.jsonl
- `row_from_embedding_record(r)`  
  - ดึง `heading_path`, `meta`, `vector`
  - แปลง `meta` เป็น JSON string เพื่อส่งเข้า `jsonb`
  - ตรวจว่า `vector` เป็น list และไม่ว่าง

### 7.4 batch insert
- `upsert_embeddings(conn, records, batch_size)`  
  ใช้ `executemany()` ใส่ batch เพื่อเร็วขึ้น

### 7.5 main pipeline
- `store_doc_dir(doc_dir, db_url, ...)`  
  - อ่าน embeddings.jsonl
  - หา `embedding_dim`
  - connect DB + register_vector(conn)
  - setup table/index (ถ้าไม่ปิด)
  - upsert ทั้งหมด
  - คืน manifest สรุปผล

---

## 8) วิธีตรวจว่าข้อมูลเข้า DB แล้ว (Verification)

### 8.1 นับจำนวนแถว
```sql
SELECT COUNT(*) FROM rag_chunks;
```

### 8.2 ดูตัวอย่าง 5 แถว
```sql
SELECT chunk_id, doc_id, page_start, left(text, 120) AS preview
FROM rag_chunks
LIMIT 5;
```

### 8.3 เช็ค dim
```sql
SELECT embedding_dim, COUNT(*)
FROM rag_chunks
GROUP BY embedding_dim;
```

---

## 9) ตัวอย่าง Query similarity search (ไว้เช็คเบื้องต้น)

> ปกติ Retrieval จะทำ: embed คำถาม → ได้ vector q → ค้นหา top-k

ตัวอย่าง SQL (cosine distance):
```sql
SELECT chunk_id, doc_id, page_start, text,
       1 - (vector <=> $1) AS cosine_similarity
FROM rag_chunks
ORDER BY vector <=> $1
LIMIT 5;
```

- `$1` = query vector (ต้องส่งจาก python)
- `<=>` = cosine distance operator ของ pgvector

---

## 10) Troubleshooting (ปัญหาที่พบบ่อย)

### 10.1 error: `extension "vector" is not available`
สาเหตุ:
- image Postgres ไม่มี pgvector

วิธีแก้:
- ใช้ `pgvector/pgvector:pg17` หรือ build เพิ่ม extension

### 10.2 error: permission denied to create extension
สาเหตุ:
- user ไม่มีสิทธิ์ CREATE EXTENSION

วิธีแก้:
- ใช้ user ที่เป็น superuser (เช่น postgres) หรือให้ DBA สร้าง extension ให้ก่อน
- แล้วรันด้วย `--no-setup`

### 10.3 error: dimension mismatch
สาเหตุ:
- vector ที่ insert dim ไม่เท่ากับ `VECTOR(dim)` ใน table

วิธีแก้:
- ต้องใช้ embedding model เดียวกันทั้งชุด
- หรือสร้าง table แยก per model/dim
- หรือ drop/recreate table ให้ตรง dim

### 10.4 HNSW index create failed
สาเหตุ:
- pgvector เวอร์ชันเก่า/ไม่รองรับ

วิธีแก้:
- ปรับเป็น IVFFLAT (ผมทำให้ได้ถ้าคุณต้องการ)

---

## 11) Best Practices (แนะนำสำหรับ production)

- ใช้ `db` service name ใน docker-compose แทน `localhost` เพื่อ cross-platform
- เก็บ `db-url` ใน `.env` และให้โค้ดอ่านเป็น default
- รัน `--limit` ใน embedding stage เพื่อเช็คก่อน embed ทั้งหมด
- ใช้ `chunk_id` เป็น key เสมอ เพื่อ upsert ได้
- เพิ่ม field เช่น `tenant_id`, `department`, `doc_type` ใน `meta` เพื่อ filter ได้ในอนาคต

---

## Appendix A: ตัวอย่าง .env (แนะนำ)
```env
POSTGRES_DB=ragdb
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

DB URL ใน container:
```
postgresql://postgres:postgres@db:5432/ragdb
```

---

End of Document
