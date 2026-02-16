import os
import sys
from dotenv import load_dotenv

# Add parent directory to path to allow importing settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from settings import BASE_DIR
from typhoon_ocr import ocr_document

def process_document_to_markdown(input_path, output_path):
    """
    Performs OCR on a document and saves the resulting markdown to a file.
    """
    load_dotenv()
    
    # OCR document
    markdown = ocr_document(
        pdf_or_image_path=input_path, 
        base_url=os.getenv("OLLAMA_BASE_URL_LOCAL"), 
        api_key=os.getenv("OLLAMA_API_KEY"), 
        model=os.getenv("OLLAMA_MODEL")
    )
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save markdown to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown)
    
    print(f'Markdown saved to {output_path}')
    return markdown

if __name__ == "__main__":
    input_file = os.path.join(BASE_DIR, 'Retrieval_Augmented_Generation_RAG', 'media', 'output', 'images', 'page_1.jpg')
    output_file = os.path.join(BASE_DIR, 'Retrieval_Augmented_Generation_RAG', 'media', 'output', 'markdown', 'page_1.md')
    
process_document_to_markdown(input_file, output_file)