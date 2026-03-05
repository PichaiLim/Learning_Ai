# 🐳 คู่มือการใช้งาน Docker สำหรับ LLM RAG Application

> Stack: **Python (FastAPI)** + **PostgreSQL + pgvector** + **Docker Compose**

---

## 📑 สารบัญ

- [✅ Prerequisites (สิ่งที่ต้องมีก่อน)](#-prerequisites-สิ่งที่ต้องมีก่อน)
- [📁 โครงสร้างไฟล์](#-โครงสร้างไฟล์)
- [🚀 การเริ่มต้นใช้งาน (First Time Setup)](#-การเริ่มต้นใช้งาน-first-time-setup)
  - [1. Clone โปรเจกต์](#1-clone-โปรเจกต์)
  - [2. สร้างไฟล์ `.env` จาก template](#2-สร้างไฟล์-env-จาก-template)
  - [3. Build และรัน](#3-build-และรัน)
  - [4. ตรวจสอบว่า services พร้อมใช้งาน](#4-ตรวจสอบว่า-services-พร้อมใช้งาน)
- [📋 คำสั่งที่ใช้บ่อย](#-คำสั่งที่ใช้บ่อย)
  - [ดู Logs](#ดู-logs)
  - [หยุด / เริ่ม Services](#หยุด--เริ่ม-services)
  - [หยุดและลบ Containers](#หยุดและลบ-containers)
- [🔄 Workflow การพัฒนา (Development)](#-workflow-การพัฒนา-development)
  - [เมื่อแก้ไข Code](#เมื่อแก้ไข-code)
  - [เมื่อเพิ่ม Python Package ใหม่](#เมื่อเพิ่ม-python-package-ใหม่)
  - [เมื่อแก้ไข init.sql (DB Schema)](#เมื่อแก้ไข-initsql-db-schema)
- [🗄️ การจัดการ Database](#️-การจัดการ-database)
  - [เข้า PostgreSQL shell โดยตรง](#เข้า-postgresql-shell-โดยตรง)
  - [Backup Database](#backup-database)
  - [Restore Database](#restore-database)
- [🛠️ pgAdmin (Database GUI) — Optional](#️-pgadmin-database-gui--optional)
- [🌐 API Endpoints](#-api-endpoints)
- [🔍 Debug และแก้ปัญหา](#-debug-และแก้ปัญหา)
  - [เข้าไปใน container เพื่อ debug](#เข้าไปใน-container-เพื่อ-debug)
  - [ดู resource usage](#ดู-resource-usage)
  - [ดู networks และ volumes](#ดู-networks-และ-volumes)
  - [ปัญหาที่พบบ่อย](#ปัญหาที่พบบ่อย) (DB / Port / .env / Ollama / OOMKilled)
- [🔐 การทำงานของ `.env` กับ Docker](#-การทำงานของ-env-กับ-docker)
  - [ชั้นที่ 1 — .dockerignore (ป้องกันตอน Build)](#ชั้นที่-1--dockerignore-ป้องกันตอน-build)
  - [ชั้นที่ 2 — docker-compose.yml (โหลดตอน Runtime)](#ชั้นที่-2--docker-composeyml-โหลดตอน-runtime)
  - [ภาพรวมการทำงาน](#ภาพรวมการทำงาน)
  - [ตรวจสอบ .env ด้วยตัวเอง](#ตรวจสอบ-env-ด้วยตัวเอง)
- [🖼️ การตรวจสอบว่าไฟล์รูปภาพไม่ได้เข้าไปใน Docker Image](#️-การตรวจสอบว่าไฟล์รูปภาพไม่ได้เข้าไปใน-docker-image)
  - [วิธีที่ 1 — ตรวจสอบก่อน Build](#วิธีที่-1--ตรวจสอบก่อน-build-ด้วย-docker-build---dry-run-เร็วที่สุด)
  - [วิธีที่ 2 — ค้นหาไฟล์รูปภาพใน Container หลัง Build](#วิธีที่-2--ค้นหาไฟล์รูปภาพใน-container-หลัง-build)
  - [วิธีที่ 3 — ตรวจสอบ Image Layer ด้วย dive](#วิธีที่-3--ตรวจสอบ-image-layer-โดยละเอียดด้วย-dive-ละเอียดที่สุด)
  - [วิธีที่ 4 — ดูขนาด Image เปรียบเทียบ](#วิธีที่-4--ดูขนาด-image-เปรียบเทียบ-sanity-check)
  - [สรุปการตรวจสอบไฟล์ที่ไม่ควรอยู่ใน Image](#สรุปการตรวจสอบไฟล์ที่ไม่ควรอยู่ใน-image)
- [🔒 Security Best Practices](#-security-best-practices)
- [⚡ การกำหนดการใช้ GPU และ CPU](#-การกำหนดการใช้-gpu-และ-cpu)
  - [ตรวจสอบก่อนว่ามี GPU ใช้ได้ใน Docker หรือไม่](#ตรวจสอบก่อนว่ามี-gpu-ใช้ได้ใน-docker-หรือไม่)
  - [🎮 การใช้ GPU (NVIDIA)](#-การใช้-gpu-nvidia)
  - [🖥️ การใช้ CPU Only](#️-การใช้-cpu-only-ไม่มี-gpu)
  - [📊 เปรียบเทียบ GPU vs CPU สำหรับ Typhoon 3B](#-เปรียบเทียบ-gpu-vs-cpu-สำหรับ-typhoon-3b)
  - [🗂️ RAM Layout เมื่อรันบน 8 GB](#️-ram-layout-เมื่อรันบน-8-gb)
  - [ปรับ .env ให้ประหยัด Resource บน 8 GB](#ปรับ-env-ให้ประหยัด-resource-บน-8-gb)
  - [ตรวจสอบการใช้ Resource จริงขณะรัน](#ตรวจสอบการใช้-resource-จริงขณะรัน)
- [📦 ตัวอย่าง Production Deployment](#-ตัวอย่าง-production-deployment)
  - [ข้อแตกต่างจาก Development](#ข้อแตกต่างจาก-development)
  - [ขั้นตอน Deploy](#ขั้นตอน-deploy)
  - [ปิด Port DB ใน Production](#ปิด-port-db-ใน-production)
  - [ตรวจสอบ .gitignore ก่อน Push](#ตรวจสอบ-gitignore-ก่อน-push)

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

## ✅ Prerequisites (สิ่งที่ต้องมีก่อน)

ตรวจสอบว่าติดตั้งครบก่อนเริ่มใช้งาน:

```bash
# ตรวจสอบ Docker
docker --version
# ต้องการ: Docker 24.0 ขึ้นไป

# ตรวจสอบ Docker Compose
docker compose version
# ต้องการ: Docker Compose v2.0 ขึ้นไป (สังเกตว่าใช้ "compose" ไม่มี "-")

# ตรวจสอบว่า Docker daemon กำลังทำงานอยู่
docker info
```

| สิ่งที่ต้องการ | เวอร์ชันขั้นต่ำ | ดาวน์โหลด |
|---|---|---|
| Docker Desktop (Windows/Mac) | 4.25+ | [docs.docker.com](https://docs.docker.com/get-docker/) |
| Docker Engine (Linux) | 24.0+ | [docs.docker.com](https://docs.docker.com/engine/install/) |
| Docker Compose Plugin | v2.0+ | มาพร้อม Docker Desktop อัตโนมัติ |
| RAM | 8 GB ขึ้นไป | — |

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

จากนั้นแก้ค่าในไฟล์ `.env` อย่างน้อยส่วนที่จำเป็น:
```env
# Ollama (Local LLM)
OLLAMA_MODEL="scb10x/typhoon-ocr1.5-3b"
OLLAMA_BASE_URL_LOCAL="http://ollama:11434/v1"   # ชี้ไปที่ service ใน Docker

# Typhoon OCR
TYPHOON_OCR_API_KEY=your_key_here

# PostgreSQL
DB_HOST=db                                        # ชื่อ service ใน docker-compose
DB_NAME=rag_db
DB_USER=rag_user
DB_PASSWORD=your_strong_password_here
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
- Database: ค่าใน `DB_NAME`
- Username: ค่าใน `DB_USER`
- Password: ค่าใน `DB_PASSWORD`

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

**❌ Ollama โหลด Model ไม่สำเร็จ / ช้ามาก**
```bash
# ตรวจสอบ logs ของ Ollama
docker compose logs ollama

# โหลด model ใหม่อีกครั้งด้วยตัวเอง
docker compose exec ollama ollama pull scb10x/typhoon-ocr1.5-3b

# ตรวจสอบว่า model พร้อมใช้งาน
docker compose exec ollama ollama list
```

**❌ RAM ไม่พอ / Container ถูก kill กลางคัน (OOMKilled)**
```bash
# ตรวจสอบว่า container ถูก kill เพราะ OOM หรือเปล่า
docker inspect rag_ollama | grep -i "oomkilled"
# ถ้าเจอ "OOMKilled": true → ต้องเพิ่ม RAM limit หรือลด MAX_TOKENS ใน .env
```

**❌ Ollama ไม่ตอบสนอง / Timeout**
```bash
# ตรวจสอบว่า OLLAMA_TIMEOUT ตั้งไว้พอหรือไม่ (default 300 วินาที)
# เพิ่มใน .env
OLLAMA_TIMEOUT=600
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

## ⚡ การกำหนดการใช้ GPU และ CPU

### ตรวจสอบก่อนว่ามี GPU ใช้ได้ใน Docker หรือไม่

```bash
# ตรวจสอบ GPU ที่มีในเครื่อง
nvidia-smi

# ตรวจสอบว่า Docker มองเห็น GPU หรือเปล่า
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
```

---

### 🎮 การใช้ GPU (NVIDIA)

#### ขั้นตอนที่ 1 — ติดตั้ง NVIDIA Container Toolkit

```bash
# Ubuntu / Debian
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

#### ขั้นตอนที่ 2 — กำหนดใน `docker-compose.yml`

```yaml
services:
  # ─── Ollama (ใช้ GPU) ──────────────────────────────────
  ollama:
    image: ollama/ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1          # จำนวน GPU (all = ใช้ทุกตัว)
              capabilities: [gpu]
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"

  # ─── App ───────────────────────────────────────────────
  app:
    build: .
    environment:
      OLLAMA_BASE_URL_LOCAL: "http://ollama:11434/v1"   # ชี้ไปที่ ollama service
    depends_on:
      - ollama
    deploy:
      resources:
        limits:
          memory: 1g

volumes:
  ollama_data:
```

#### ขั้นตอนที่ 3 — โหลด Model เข้า Ollama

```bash
# หลัง docker compose up แล้ว ให้โหลด model
docker compose exec ollama ollama pull scb10x/typhoon-ocr1.5-3b

# ตรวจสอบว่า model พร้อมใช้งาน
docker compose exec ollama ollama list
```

---

### 🖥️ การใช้ CPU Only (ไม่มี GPU)

ไม่ต้องติดตั้ง NVIDIA Toolkit เพิ่ม แค่กำหนดใน `docker-compose.yml`:

```yaml
services:
  ollama:
    image: ollama/ollama          # ใช้ image เดิมได้ (รองรับ CPU อัตโนมัติ)
    environment:
      OLLAMA_NUM_THREADS: "4"     # จำนวน CPU threads ที่ให้ใช้
    deploy:
      resources:
        limits:
          memory: 4g
          cpus: "4"               # จำกัด CPU สูงสุด 4 cores
        reservations:
          memory: 3g
          cpus: "2"               # จอง CPU ขั้นต่ำ 2 cores
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
```

> ⚠️ CPU จะช้ากว่า GPU ประมาณ **5–10 เท่า** สำหรับ model ขนาด 3B parameters

---

### 📊 เปรียบเทียบ GPU vs CPU สำหรับ Typhoon 3B

| หัวข้อ | GPU (NVIDIA 4GB+) | CPU Only (8 GB RAM) |
|--------|-------------------|----------------------|
| **ความเร็ว** | ~30–50 tokens/วินาที | ~3–8 tokens/วินาที |
| **RAM ที่ใช้** | VRAM ~3 GB | RAM ~3.5 GB |
| **การติดตั้ง** | ต้องติดตั้ง NVIDIA Toolkit | ไม่ต้องทำอะไรเพิ่ม |
| **เหมาะกับ** | Production / งานหนัก | Development / ทดสอบ |

---

### 🗂️ RAM Layout เมื่อรันบน 8 GB

```
RAM 8 GB — CPU Mode
├── OS + Docker             ~1.0 GB
├── Ollama (Typhoon 3B)     ~3.5 GB  ← ตัวกินหลัก
├── PostgreSQL + pgvector   ~0.5 GB
├── FastAPI App             ~0.5 GB
└── Buffer เหลือ            ~2.5 GB  ✅ ปลอดภัย

VRAM (GPU Mode) — ถ้ามี GPU 4 GB+
├── Typhoon 3B model        ~3.0 GB
└── Buffer เหลือ            ~1.0 GB  ✅
RAM จะเหลือใช้ได้อีก ~6 GB สำหรับส่วนอื่น
```

---

### ปรับ `.env` ให้ประหยัด Resource บน 8 GB

```env
# ลด context → ประหยัด RAM
MAX_TOKENS=512          # ลดจาก 1000
CHUNK_SIZE=500          # ลดจาก 700
OVERLAP=50              # ลดจาก 100
```

---

### ตรวจสอบการใช้ Resource จริงขณะรัน

```bash
# ดู CPU / RAM / GPU usage แบบ real-time
docker stats

# ดูเฉพาะ Ollama
docker stats rag_ollama

# ตรวจสอบว่า Ollama ใช้ GPU จริง (ควรเห็น GPU % > 0)
watch -n 1 nvidia-smi
```

---

## 📦 ตัวอย่าง Production Deployment

### ข้อแตกต่างจาก Development

| | Development | Production |
|---|---|---|
| Source code mount | ✅ มี (`./src:/app/src`) | ❌ ไม่มี (ใช้จาก image เลย) |
| Port DB เปิดออกนอก | ✅ เปิด `5432` | ❌ ปิด (ปลอดภัยกว่า) |
| Debug mode | ✅ เปิด | ❌ ปิด |
| Restart policy | ไม่กำหนด | `unless-stopped` |

### ขั้นตอน Deploy

```bash
# 1. ตรวจสอบ .gitignore ก่อน push ขึ้น server
cat .gitignore | grep ".env"
# ต้องเห็น .env อยู่ใน .gitignore

# 2. Build image สำหรับ production
docker compose -f docker-compose.yml up -d --build

# 3. ตรวจสอบ services พร้อมใช้งาน
docker compose ps

# 4. ดู logs แบบ tail
docker compose logs --tail=100 -f app
```

### ปิด Port DB ใน Production

แก้ไข `docker-compose.yml` โดย comment บรรทัด ports ของ db ออก:

```yaml
db:
  image: pgvector/pgvector:pg16
  # ports:           ← comment ออกใน production
  #   - "5432:5432"  ← DB จะถูก access ได้เฉพาะจากภายใน network Docker เท่านั้น
```

### ตรวจสอบ .gitignore ก่อน Push

```bash
# ตรวจสอบว่าไฟล์สำคัญไม่ติดไปกับ git
git status --ignored | grep -E ".env|*.png|*.jpg"

# ถ้ายังไม่มี .gitignore ให้สร้าง
echo ".env" >> .gitignore
echo "*.png" >> .gitignore
echo "*.jpg" >> .gitignore
echo "*.jpeg" >> .gitignore
```

---

*อัปเดตล่าสุด: มีนาคม 2026*