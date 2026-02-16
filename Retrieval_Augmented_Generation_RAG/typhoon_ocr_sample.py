import os
import sys
import json
from typhoon_ocr import ocr_document

# Add the parent directory to sys.path to allow importing settings
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from settings import get_typhoon_ocr_api_key
    typhoon_ocr_api_key = get_typhoon_ocr_api_key()
    print("Successfully imported typhoon_ocr_api_key from settings.")
except ImportError as e:
    print(f"Error importing settings: {e}")
    sys.exit(1)


class TyphoonOCRWrapper:
    def __init__(self, api_key):
        self.api_key = api_key

    def process_document(self, input_pdf_path, output_md_path, output_json_path):
        """
        Runs OCR on the PDF, saves Markdown, and converts it to JSON.
        """
        if not os.path.exists(input_pdf_path):
            raise FileNotFoundError(f"Document not found: {input_pdf_path}")

        print(f"Processing PDF: {input_pdf_path}")
        
        # 1. Run OCR
        try:
            markdown_content = ocr_document(
                pdf_or_image_path=input_pdf_path,
                page_num=1, # TODO: might want to make this configurable
                api_key=self.api_key
            )
        except Exception as e:
             print(f"Error during OCR process: {e}", file=sys.stderr)
             return

        # 2. Save Markdown
        try:
            os.makedirs(os.path.dirname(output_md_path), exist_ok=True)
            with open(output_md_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            print(f"Markdown saved to: {output_md_path}")
        except Exception as e:
            print(f"Error saving Markdown file: {e}", file=sys.stderr)
            return

        # 3. Convert to JSON
        self._convert_md_to_json(output_md_path, output_json_path)

    def _convert_md_to_json(self, input_path, output_path):
        """
        Reads a markdown file, filters out empty lines, and saves the result as a JSON file.
        """
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                # Filter out empty or whitespace-only lines
                content_list = [line for line in f.read().splitlines() if line.strip()]

            # Print to console (optional, keeping consistent with previous behavior)
            print("JSON Output Preview:")
            print(json.dumps(content_list, ensure_ascii=False, indent=4))

            # Write to JSON file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(content_list, f, ensure_ascii=False, indent=4)
            
            print(f"JSON saved to: {output_path}")

        except FileNotFoundError:
            print(f"Error: The file {input_path} was not found during JSON conversion.", file=sys.stderr)
        except Exception as e:
            print(f"An error occurred during JSON conversion: {e}", file=sys.stderr)


def main():
    # Ensure stdout uses UTF-8 to avoid encoding errors on Windows
    sys.stdout.reconfigure(encoding='utf-8')
    print("Hello Typhoon OCR Sample\n")

    base_dir = os.path.dirname(__file__)
    
    # Define paths
    pdf_input = os.path.join(base_dir, 'media', 'PDPA_thailand.pdf')
    md_output = os.path.join(base_dir, 'media', 'output', 'PDPA_thailand.md')
    json_output = os.path.join(base_dir, 'media', 'output', 'PDPA_thailand.json')

    # Initialize and run
    ocr_service = TyphoonOCRWrapper(typhoon_ocr_api_key)
    ocr_service.process_document(pdf_input, md_output, json_output)


if __name__ == "__main__":
    main()

