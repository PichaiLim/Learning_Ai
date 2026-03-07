# GENERATION.md
## RAG Pipeline — Stage 7: Generation (Top‑K Chunks → Prompt → LLM Answer + Citations)

เอกสารนี้อธิบาย “Generation Layer” ที่เอา output จาก Retrieval (Stage 6) มาทำคำตอบด้วย LLM (Ollama)

> เป้าหมาย: สร้างคำตอบที่ “อ้างอิงจากเอกสาร” พร้อม citation [S1], [S2] และกัน hallucination ให้มากที่สุด

---

## 1) Generation อยู่ตรงไหนใน Pipeline

```
... → Vector Store → Retrieval → Generation → Answer
```

Stage 7 จะทำ 3 อย่าง:
1) “จัดรูป” chunks ให้เป็น context
2) “เขียน prompt” ให้ LLM ตอบโดยอ้างอิง context เท่านั้น
3) “เรียก Ollama” เพื่อสร้างคำตอบ แล้วแสดงแหล่งอ้างอิง

---

## 2) Input / Output

### Input
- `question` : คำถามผู้ใช้
- `retrieved.results` : รายการ chunk top‑k จาก Stage 6

### Output
- `answer` : ข้อความคำตอบภาษาไทย
- `sources` : รายการแหล่งอ้างอิงที่แมปกับ [S1], [S2], ...

---

## 3) Prompt Pattern ที่แนะนำ (ลด hallucination)

แนวคิดหลัก:
- ระบุ “กติกาชัดเจน” ว่าห้ามเดา
- ถ้าไม่พบใน context ให้ตอบว่าไม่พบ
- บังคับให้ใส่ citation

ตัวอย่าง template:
```
คุณคือผู้ช่วย RAG ที่ตอบโดยอ้างอิงจาก CONTEXT เท่านั้น

กติกา:
1) ถ้าคำตอบไม่มีใน CONTEXT ให้ตอบว่า "ไม่พบข้อมูลในเอกสารที่ให้มา"
2) ตอบเป็นภาษาไทย กระชับ ชัดเจน
3) ใส่อ้างอิงท้ายประโยคด้วย [S1], [S2]

CONTEXT:
[S1] ...
[S2] ...

QUESTION:
...

ANSWER:
```

---

## 4) การจัด Context (Context Packing)

### 4.1 ทำไมต้องจำกัดความยาว
ถ้า top‑k เยอะ + chunk ยาว → prompt บวม → ช้า + อาจหลุดประเด็น

แนะนำ:
- จำกัดความยาวรวม context (เช่น 12,000 chars)
- ตัด context ถ้าเกิน

### 4.2 ใส่ label/citation ให้ทุก chunk
รูปแบบที่คนอ่านเข้าใจง่าย:
- `[S1] file.pdf p.3-3 | Heading Path`
- ตามด้วย text

---

## 5) ใช้งานด้วย `generator.py`

### 5.1 การรันแบบสองสเต็ป (retriever → generator)
```bash
python retriever.py --question "PDPA คืออะไร" --top-k 5 > retrieved.json
python generator.py --question "PDPA คืออะไร" --retrieved-json retrieved.json
```

### 5.2 ใช้เป็นฟังก์ชัน
```python
from retriever import retrieve_top_k
from generator import generate_answer

retrieved = retrieve_top_k("PDPA คืออะไร", top_k=5)
out = generate_answer("PDPA คืออะไร", retrieved)
print(out["answer"])
```

---

## 6) ตั้งค่า (Environment Variables)

```env
OLLAMA_URL=http://host.docker.internal:11434
LLM_MODEL=typhoon
```

> ถ้าคุณใช้ LLM ตัวอื่นใน Ollama ก็เปลี่ยน `LLM_MODEL`

---

## 7) แนวทางเพิ่มคุณภาพคำตอบ (ของจริงที่ใช้บ่อย)

### 7.1 เพิ่ม “Answer Style”
เช่น ให้ตอบเป็น bullet + สรุปท้าย:
- สรุปใจความ
- ข้อยกเว้น/เงื่อนไข
- อ้างอิงท้ายข้อ

### 7.2 ให้ LLM แยก “คำตอบ” กับ “หลักฐาน”
เช่นให้ format:
- คำตอบ:
- หลักฐาน: [S1]..., [S2]...

### 7.3 Multi-turn Chat (เก็บประวัติ)
ถ้าต้องการถามต่อเนื่อง:
- เก็บ chat history สั้น ๆ
- แต่ต้องกันไม่ให้ history กลบ context

### 7.4 Guardrail
- ถ้า similarity ต่ำเกิน (distance สูง) → แจ้งว่าไม่มั่นใจ/ไม่พบข้อมูล
- ทำ threshold เช่น ถ้า `cosine_distance > 0.35` ให้ตอบว่า “ไม่พบข้อมูลชัดเจน”

---

## 8) Troubleshooting

### 8.1 LLM ไม่ใส่ citation
- เพิ่มกติกาใน prompt ให้ชัดขึ้น
- จำกัดรูปแบบ citation ให้เป็น `[S#]` เท่านั้น

### 8.2 LLM ตอบนอก context
- เพิ่มประโยค “ห้ามใช้ความรู้ภายนอก”
- ลด context ให้เฉพาะส่วนที่เกี่ยวข้อง
- เพิ่ม threshold + fallback message

---

End of Document
