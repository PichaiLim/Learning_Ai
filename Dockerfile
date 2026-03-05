# ============================================================
# Dockerfile สำหรับ LLM RAG Application
# ============================================================

# ใช้ Python base image แบบ slim เพื่อลดขนาด
FROM python:3.11-slim

# ตั้ง working directory
WORKDIR /app

# ติดตั้ง system dependencies ที่จำเป็น
# - libpq-dev: สำหรับ PostgreSQL (psycopg2)
# - gcc: สำหรับ compile C extensions
# - curl: สำหรับ health check
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements ก่อน (Docker layer caching)
COPY requirements.txt .

# ติดตั้ง Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy source code (ไฟล์ที่ไม่อยู่ใน .dockerignore)
COPY . .

# สร้าง non-root user เพื่อความปลอดภัย
RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
