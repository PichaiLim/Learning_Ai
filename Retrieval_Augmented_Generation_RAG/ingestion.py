import sys
import os
from dotenv import load_dotenv
from load_document import LoadDocument

# Add parent directory to path to allow importing settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from settings import BASE_DIR

load_dotenv()

# TODO Ingestion PDF to Markdown
## 1. Convert PDF to Image


## 2. Convert Image to Markdown

### 2.1 OCR


### 2.2 Clean Markdown


# TODO Markdown to Chunk


# TODO Chunk to Embedding


# TODO Embedding to Vector Store


# TODO Vector Store to Retriever


# TODO Retriever to Generator


# TODO Generator to Evaluation