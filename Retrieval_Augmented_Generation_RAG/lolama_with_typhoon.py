import os
import sys
# Add parent directory to path to allow importing settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from settings import BASE_DIR
from typhoon_ocr import ocr_document
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Path to the PDF or image
# C:\Users\Public\Public Programs\Learning_Ai\Retrieval_Augmented_Generation_RAG\media\output\images\page_1.jpg
# pdf_or_image = os.path.join(BASE_DIR, 'Retrieval_Augmented_Generation_RAG', 'media', 'output', 'images', 'page_1.jpg')
pdf_or_image_folder = os.path.join(BASE_DIR, 'Retrieval_Augmented_Generation_RAG', 'media', 'output', 'images')
pdf_or_image = os.path.join(pdf_or_image_folder, 'page_1.jpg')
print(f'PDF OR IMAGE PATH: {pdf_or_image}')

# OCR document
markdown = ocr_document(pdf_or_image_path=pdf_or_image, base_url=os.getenv("OLLAMA_BASE_URL_LOCAL"), api_key=os.getenv("OLLAMA_API_KEY"), model=os.getenv("OLLAMA_MODEL"))
print(markdown)

# Save markdown to file
# C:\Users\Public\Public Programs\Learning_Ai\Retrieval_Augmented_Generation_RAG\media\output\markdown
markdown_folder= os.path.join(BASE_DIR, 'Retrieval_Augmented_Generation_RAG', 'media', 'output', 'markdown')
# Create the directory if it doesn't exist
if not os.path.exists(markdown_folder):
    os.makedirs(markdown_folder)
    print(f'Markdown folder created: {markdown_folder}')
else:
    print(f'Markdown folder already exists: {markdown_folder}')

# C:\Users\Public\Public Programs\Learning_Ai\Retrieval_Augmented_Generation_RAG\media\output\markdown\page_1.md
markdown_file = os.path.join(markdown_folder, 'page_1.md')
with open(markdown_file, 'w', encoding='utf-8') as f:
    f.write(markdown)
    print(f'Markdown saved to {markdown_file}') 