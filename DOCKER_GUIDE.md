# 🐳 คู่มือการใช้งาน Docker สำหรับ LLM RAG Application

> Stack: **Python (FastAPI)** + **PostgreSQL + pgvector** + **Docker Compose**

---

## 📁 โครงสร้างไฟล์

```
project/
├── Dockerfile              # Build image ของ app
├── docker-compose.yml      # รัน services ทั้งหมดพร้อมกัน
├── .dockerignore           # กันไฟล์ไม่จำเป็นออกจาก image
├── .env.example            # Template config (commit ได้)
├── .env                    # ค่าจริง (ห้าม commit!)
├── init.sql                # สร้าง DB schema ตอนเริ่มต้น
├── requirements.txt        # Python dependencies
└── src/
    └── main.py             # Application code
```

---

## 🚀 การเริ่มต้นใช้งาน (First Time Setup)

### 1. Clone โปรเจกต์
```bash
git clone https://github.com/PichaiLim/Learning_Ai.git
cd Learning_Ai
```

### 2. สร้างไฟล์ `.env` จาก template
```bash
cp .env.example .env
```

จากนั้นแก้ค่าในไฟล์ `.env`:
```env
POSTGRES_USER=rag_user
POSTGRES_PASSWORD=your_strong_password_here
POSTGRES_DB=rag_db

OPENAI_API_KEY=sk-...
```

> ⚠️ **ห้าม commit ไฟล์ `.env`** เด็ดขาด — ไฟล์นี้เก็บ API Key และรหัสผ่านจริง

### 3. Build และรัน
```bash
docker compose up -d --build
```

| Flag | ความหมาย |
|------|----------|
| `-d` | รันใน background (detached mode) |
| `--build` | Build image ใหม่ทุกครั้ง |

### 4. ตรวจสอบว่า services พร้อมใช้งาน
```bash
docker compose ps
```

ผลลัพธ์ที่ควรได้:
```
NAME            STATUS          PORTS
rag_app         Up (healthy)    0.0.0.0:8000->8000/tcp
rag_postgres    Up (healthy)    0.0.0.0:5432->5432/tcp
```

---

## 📋 คำสั่งที่ใช้บ่อย

### ดู Logs
```bash
# ดู logs ของทุก service แบบ real-time
docker compose logs -f

# ดู logs เฉพาะ app
docker compose logs -f app

# ดู logs เฉพาะ database
docker compose logs -f db
```

### หยุด / เริ่ม Services
```bash
# หยุดทุก service (เก็บ data ไว้)
docker compose stop

# เริ่มใหม่
docker compose start

# Restart เฉพาะ app (หลังแก้ code)
docker compose restart app
```

### หยุดและลบ Containers
```bash
# ลบ containers (เก็บ volume/data ไว้)
docker compose down

# ลบทุกอย่าง รวมถึง database data ด้วย ⚠️
docker compose down -v
```

---

## 🔄 Workflow การพัฒนา (Development)

### เมื่อแก้ไข Code
```bash
# Rebuild และ restart เฉพาะ app (ไม่ต้อง restart DB)
docker compose up -d --build app
```

### เมื่อเพิ่ม Python Package ใหม่
```bash
# 1. เพิ่มใน requirements.txt แล้ว
# 2. Build ใหม่
docker compose up -d --build app
```

### เมื่อแก้ไข init.sql (DB Schema)
```bash
# ต้องลบ volume เก่าก่อน เพราะ init.sql รันแค่ครั้งแรก
docker compose down -v
docker compose up -d --build
```

---

## 🗄️ การจัดการ Database

### เข้า PostgreSQL shell โดยตรง
```bash
docker compose exec db psql -U rag_user -d rag_db
```

คำสั่งใน psql ที่มีประโยชน์:
```sql
-- ดูตารางทั้งหมด
\dt

-- ดู schema ของตาราง
\d documents

-- ตรวจสอบ pgvector extension
SELECT * FROM pg_extension WHERE extname = 'vector';

-- ออกจาก psql
\q
```

### Backup Database
```bash
docker compose exec db pg_dump -U rag_user rag_db > backup.sql
```

### Restore Database
```bash
cat backup.sql | docker compose exec -T db psql -U rag_user -d rag_db
```

---

## 🛠️ pgAdmin (Database GUI) — Optional

เปิดใช้งาน pgAdmin เพื่อจัดการ DB ผ่าน browser:

```bash
docker compose --profile tools up -d pgadmin
```

จากนั้นเปิด browser ไปที่ `http://localhost:5050`

| Field | ค่า |
|-------|-----|
| Email | ค่าใน `PGADMIN_EMAIL` (.env) |
| Password | ค่าใน `PGADMIN_PASSWORD` (.env) |

**การเชื่อมต่อกับ PostgreSQL ใน pgAdmin:**
- Host: `db`  ← ชื่อ service ใน docker-compose
- Port: `5432`
- Database: ค่าใน `POSTGRES_DB`
- Username: ค่าใน `POSTGRES_USER`
- Password: ค่าใน `POSTGRES_PASSWORD`

---

## 🌐 API Endpoints

หลังจากรัน app สำเร็จ สามารถเข้าถึงได้ที่:

| URL | รายละเอียด |
|-----|------------|
| `http://localhost:8000` | Application หลัก |
| `http://localhost:8000/health` | Health check |
| `http://localhost:8000/docs` | Swagger UI (API docs) |
| `http://localhost:8000/redoc` | ReDoc (API docs) |

---

## 🔍 Debug และแก้ปัญหา

### เข้าไปใน container เพื่อ debug
```bash
# เข้าไปใน app container
docker compose exec app bash

# เข้าไปใน db container
docker compose exec db bash
```

### ดู resource usage
```bash
docker stats
```

### ดู networks และ volumes
```bash
# ดู networks
docker network ls

# ดู volumes
docker volume ls

# ดูรายละเอียด volume ของ postgres
docker volume inspect rag_postgres_data
```

### ปัญหาที่พบบ่อย

**❌ App ไม่สามารถเชื่อมต่อ DB ได้**
```bash
# ตรวจสอบว่า DB healthy แล้วหรือยัง
docker compose ps

# ดู logs ของ DB
docker compose logs db
```

**❌ Port 8000 หรือ 5432 ถูกใช้อยู่แล้ว**
```bash
# แก้ไข ports ใน docker-compose.yml
# เช่น เปลี่ยนจาก "8000:8000" เป็น "8001:8000"
```

**❌ `.env` ไม่ถูกโหลด**
```bash
# ตรวจสอบว่าไฟล์ .env อยู่ใน directory เดียวกับ docker-compose.yml
ls -la | grep .env
```

---

## 🔐 การทำงานของ `.env` กับ Docker

Docker **ไม่ได้ copy ไฟล์ `.env` เข้าไปใน image** แต่ **อ่านค่าจาก host แล้ว inject เป็น environment variable** ตอนรัน container โดยมีกลไก 2 ชั้น:

### ชั้นที่ 1 — `.dockerignore` (ป้องกันตอน Build)

```
.env
.env.*
```

ตอน `docker build` จะ **ข้าม `.env` ทั้งหมด** แม้จะมีคำสั่ง `COPY . .` ใน Dockerfile ก็ตาม ไฟล์ `.env` จะไม่มีอยู่ใน image เด็ดขาด

### ชั้นที่ 2 — `docker-compose.yml` (โหลดตอน Runtime)

```yaml
app:
  env_file:
    - .env   # อ่านจาก host แล้ว inject เป็น environment variable เข้า container
```

`.env` อยู่บน **host เครื่องของคุณ** → Docker อ่านค่าแล้ว inject เข้าไปตอน container เริ่มทำงาน → **ไม่มีไฟล์ `.env` อยู่ใน image เลย**

### ภาพรวมการทำงาน

```
Host Machine                        Docker Image
─────────────────                   ──────────────────────────
.env  ──── inject ──────────────►   DB_HOST=db        (env var)
                                    DB_USER=rag_user  (env var)
                                    OLLAMA_API_KEY=.. (env var)

          ❌ ไม่ได้ copy ──────►   (ไม่มีไฟล์ .env ใน image)
```

### ตรวจสอบ `.env` ด้วยตัวเอง

```bash
# ยืนยันว่าไม่มีไฟล์ .env อยู่ใน container
docker compose exec app find / -name ".env" 2>/dev/null

# ยืนยันว่า env var ถูก inject เข้าไปถูกต้อง
docker compose exec app env | grep DB_HOST
```

ผลที่ควรได้คือ **ไม่เจอไฟล์ `.env`** แต่ **เจอ `DB_HOST=db`** ซึ่งยืนยันว่า inject สำเร็จ

> ✅ API Key และรหัสผ่านปลอดภัย — ไม่ติดไปกับ image ที่ push ขึ้น Docker Hub หรือแชร์ให้คนอื่น

---

## 🖼️ การตรวจสอบว่าไฟล์รูปภาพไม่ได้เข้าไปใน Docker Image

มี 3 วิธีตรวจสอบ เรียงจากง่ายไปละเอียด:

### วิธีที่ 1 — ตรวจสอบก่อน Build ด้วย `docker build --dry-run` (เร็วที่สุด)

```bash
# ดูว่า Docker จะ copy ไฟล์อะไรเข้า image บ้าง (ไม่ได้ build จริง)
docker build --no-cache --progress=plain . 2>&1 | grep "COPY"
```

### วิธีที่ 2 — ค้นหาไฟล์รูปภาพใน Container หลัง Build

```bash
# ค้นหาไฟล์รูปภาพทุกนามสกุลใน container
docker compose exec app find /app -type f \( \
  -name "*.png"  -o \
  -name "*.jpg"  -o \
  -name "*.jpeg" -o \
  -name "*.gif"  -o \
  -name "*.bmp"  -o \
  -name "*.svg"  -o \
  -name "*.webp" \
\) 2>/dev/null
```

**ผลที่ควรได้:** ไม่มีผลลัพธ์ใดๆ (เงียบ) = ไม่มีไฟล์รูปภาพใน container ✅

### วิธีที่ 3 — ตรวจสอบ Image Layer โดยละเอียดด้วย `dive` (ละเอียดที่สุด)

`dive` เป็น tool ที่ช่วยดูได้ว่าแต่ละ layer ใน image มีไฟล์อะไรบ้าง

```bash
# ติดตั้ง dive
docker run --rm -it \
  -v /var/run/docker.sock:/var/run/docker.sock \
  wagoodman/dive:latest <ชื่อ image ของคุณ>
```

เช่น:
```bash
docker run --rm -it \
  -v /var/run/docker.sock:/var/run/docker.sock \
  wagoodman/dive:latest learning_ai-app
```

**วิธีใช้ใน dive UI:**

| ปุ่ม | การทำงาน |
|------|----------|
| `Tab` | สลับระหว่าง Layers / Files |
| `Ctrl+F` | Filter หาไฟล์ เช่น พิมพ์ `.png` |
| `Space` | ซ่อน/แสดงไฟล์ที่ไม่เปลี่ยนแปลง |

### วิธีที่ 4 — ดูขนาด Image เปรียบเทียบ (Sanity Check)

```bash
# ดูขนาด image ทั้งหมด
docker images | grep learning_ai

# ดูรายละเอียดขนาดแต่ละ layer
docker history learning_ai-app
```

> 💡 ถ้าขนาด image ใหญ่ผิดปกติ (เช่น เกิน 1GB โดยไม่มีเหตุผล) อาจมีไฟล์ขนาดใหญ่ติดเข้าไป ให้ตรวจสอบด้วย `dive` ต่อ

---

### สรุปการตรวจสอบไฟล์ที่ไม่ควรอยู่ใน Image

```bash
# รันคำสั่งเดียวตรวจสอบทุกอย่างพร้อมกัน
echo "=== ตรวจสอบ .env ===" && \
docker compose exec app find /app -name ".env*" 2>/dev/null && \
echo "=== ตรวจสอบ Images ===" && \
docker compose exec app find /app -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" -o -name "*.gif" -o -name "*.webp" -o -name "*.svg" \) 2>/dev/null && \
echo "=== ตรวจสอบ .md ===" && \
docker compose exec app find /app -name "*.md" 2>/dev/null && \
echo "=== ✅ เสร็จสิ้น (ไม่มีผลลัพธ์ = ปลอดภัย) ==="
```

---

## 🔒 Security Best Practices

1. **ห้าม commit `.env`** — ตรวจสอบ `.gitignore` ว่ามี `.env` อยู่แล้ว
2. **ปิด port 5432** ใน production — ลบหรือ comment บรรทัด `ports` ของ `db` service
3. **ใช้รหัสผ่านที่แข็งแรง** — อย่าใช้ค่า default จาก `.env.example`
4. **อย่า run ด้วย root user** — Dockerfile สร้าง `appuser` ให้แล้ว

---

## 📦 ตัวอย่าง Production Deployment

```bash
# รัน production โดยไม่ mount source code
docker compose -f docker-compose.yml up -d --build

# ดู logs แบบ tail
docker compose logs --tail=100 -f app
```

---

*อัปเดตล่าสุด: มีนาคม 2026*
