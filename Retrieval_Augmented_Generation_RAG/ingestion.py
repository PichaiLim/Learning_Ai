import sys
import os
from dotenv import load_dotenv
from pathlib import Path
from load_document import LoadDocument

# Add parent directory to path to allow importing settings
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from settings import BASE_DIR

load_dotenv()

# TODO Ingestion PDF to Markdown
class Ingestion:
    def __init__(self):
        self.load_document = LoadDocument()
        self.pdf_path = self.load_document.pdf_path
        self.output_path = self.load_document.output_path

    ## 1. Convert PDF to Image
    def convert_pdf_to_image(self):
        print("convert pdf to image")
        output_path = self.load_document.convert_pdf_to_image(
            pdf_path=str(self.pdf_path),
            output_path=str(self.output_path) # media/output/images
        )
        return output_path

    ## 2. Convert Image to Markdown
    ### 2.1 OCR
    def convert_image_to_raw_markdown(self, image_path: str):
        """
        Convert images in the given directory to raw markdown.
        """
        print("convert image to raw markdown")
        image_dir = Path(image_path)
        if not image_dir.exists():
            raise FileNotFoundError(f"Image directory not found: {image_path}")

        # Iterate over all images in the directory
        for image_file in image_dir.glob('*.jpg') + image_dir.glob('*.jpeg') + image_dir.glob('*.png'):
            print(f"Processing: {image_file.name}")
            output_markdown_path = self.output_path / 'markdown' / 'raw_markdown' / f"{image_file.stem}.md"
            
            self.load_document.convert_image_to_raw_markdown(
                image_path=str(image_file),
                output_path=str(output_markdown_path)
            )

    ### 2.2 Clean Markdown
    

    # def convert_pdf_to_image(self):
    #     self.load_document.convert_pdf_to_image()

    # def convert_image_to_markdown(self):
    #     self.load_document.convert_image_to_markdown()

    # def markdown_to_chunk(self):
    #     self.load_document.markdown_to_chunk()

    # def chunk_to_embedding(self):
    #     self.load_document.chunk_to_embedding()

    # def embedding_to_vector_store(self):
    #     self.load_document.embedding_to_vector_store()

    # def vector_store_to_retriever(self):
    #     self.load_document.vector_store_to_retriever()

    # def retriever_to_generator(self):
    #     self.load_document.retriever_to_generator()

    # def generator_to_evaluation(self):
    #     self.load_document.generator_to_evaluation()







# TODO Markdown to Chunk


# TODO Chunk to Embedding


# TODO Embedding to Vector Store


# TODO Vector Store to Retriever


# TODO Retriever to Generator


# TODO Generator to Evaluation

if __name__ == '__main__':
    ingestion = Ingestion()
    imgs = ingestion.convert_pdf_to_image()
    ingestion.convert_image_to_raw_markdown(image_path=str(imgs / 'markdown' / 'raw_markdown'))