import os
from ollama import chat
from typhoon_ocr import ocr_document
from dotenv import load_dotenv
load_dotenv()

# ============================================================================
# TODO: OLLAMA AI : using model typhoon ocr
# Example: https://ollama.com/scb10x/typhoon-ocr1.5-3b
# ============================================================================
print("Ollama model: ", os.getenv("OLLAMA_MODEL"))
context = input("Enter your context: ")
response = chat(
    model=os.getenv("OLLAMA_MODEL"),
    messages=[
        {
            'role': 'user', 
            'content': context
        }
    ],
)
print(response.message.content)

# ============================================================================
# TODO PDF to IMAGE
# ============================================================================
from pdf2image import convert_from_path, convert_from_bytes
from pdf2image.exceptions import (
    PDFInfoNotInstalledError,
    PDFPageCountError,
    PDFSyntaxError
)

# Convert PDF to images
base_dir = os.path.dirname(__file__)
pdf_path = os.path.join(base_dir, 'media', 'PDPA_thailand.pdf')
output_path = os.path.join(base_dir, 'media\output')

images = convert_from_path(pdf_path)
for i, image in enumerate(images):
    image.save(f'{output_path}/images/page_{i+1}.jpg', 'JPEG')


