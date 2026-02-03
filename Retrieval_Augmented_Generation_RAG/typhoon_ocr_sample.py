print("Hello Typhoon OCR Sample \n")

import os
import sys
from typhoon_ocr import ocr_document


# Add the parent directory to sys.path to allow importing settings

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


try:

    from settings import get_typhoon_ocr_api_key

    typhoon_ocr_api_key = get_typhoon_ocr_api_key()

    print("Successfully imported typhoon_ocr_api_key from settings.")

except ImportError as e:

    print(f"Error importing settings: {e}")



class TyphoonOCR:

    def __init__(self, api_key):

        self.api_key = api_key

        self.base_url = "https://api.opentyphoon.ai/v1"


    def get_ocr_document(self, document_path):

        if not os.path.exists(document_path):

            raise FileNotFoundError(f"Document not found: {document_path}")
        

        # print("Document path: ", document_path)

        # print("API Key: ", self.api_key)
        jls_extract_var = document_path#r"C:/Users/Public/Public Programs/Learning_Ai/Retrieval_Augmented_Generation_RAG/media/PDPA_thailand.pdf"
        markdown_content = ocr_document(
            pdf_or_image_path=jls_extract_var,
            page_num=1,
            api_key=self.api_key
        )


        print("Markdown content: ", markdown_content)


if __name__ == "__main__":

    typhoon_ocr = TyphoonOCR(typhoon_ocr_api_key)

    typhoon_ocr.get_ocr_document(os.path.join(os.path.dirname(__file__), 'media', 'PDPA_thailand.pdf'))

