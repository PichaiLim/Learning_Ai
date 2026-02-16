import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import sys

# Add parent directory to path to allow importing the module under test
# This assumes the test is run from the tests directory or the root directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Mock typhoon_ocr and settings before importing the module
# This is necessary if these modules are not available in the test environment
sys.modules['typhoon_ocr'] = MagicMock()
sys.modules['settings'] = MagicMock()

try:
    import ollama_with_typhoon_ocr_on_local
except ImportError:
    # If the import fails (e.g. strict dependency checks), we might need to adjust mocking
    # But usually sys.modules hack is enough.
    pass

class TestOllamaWithTyphoonOcr(unittest.TestCase):
    
    def setUp(self):
        # ensure environment variables are mocked or handled if used directly at module level
        pass

    @patch('ollama_with_typhoon_ocr_on_local.ocr_document')
    @patch('ollama_with_typhoon_ocr_on_local.os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    @patch('ollama_with_typhoon_ocr_on_local.load_dotenv')
    @patch('ollama_with_typhoon_ocr_on_local.os.getenv')
    def test_process_document_to_markdown(self, mock_getenv, mock_load_dotenv, mock_file, mock_makedirs, mock_ocr):
        """
        Test the process_document_to_markdown function.
        """
        # Setup inputs
        input_path = os.path.join('path', 'to', 'input.pdf')
        output_path = os.path.join('path', 'to', 'output', 'output.md')
        expected_markdown = "# Test Markdown Content"
        
        # Configure mocks
        mock_ocr.return_value = expected_markdown
        
        # Mock environment variables
        env_vars = {
            "OLLAMA_BASE_URL_LOCAL": "http://localhost:11434",
            "OLLAMA_API_KEY": "test_key",
            "OLLAMA_MODEL": "test_model"
        }
        mock_getenv.side_effect = lambda k: env_vars.get(k)

        # Execute functionality
        result = ollama_with_typhoon_ocr_on_local.process_document_to_markdown(input_path, output_path)
        
        # Assertions
        
        # 1. Check load_dotenv called
        mock_load_dotenv.assert_called_once()
        
        # 2. Check ocr_document called with correct parameters
        mock_ocr.assert_called_once_with(
            pdf_or_image_path=input_path,
            base_url="http://localhost:11434",
            api_key="test_key",
            model="test_model"
        )
        
        # 3. Check os.makedirs called to create output directory
        mock_makedirs.assert_called_once_with(os.path.dirname(output_path), exist_ok=True)
        
        # 4. Check file opened and written
        mock_file.assert_called_once_with(output_path, 'w', encoding='utf-8')
        mock_file.return_value.write.assert_called_once_with(expected_markdown)
        
        # 5. Check return value
        self.assertEqual(result, expected_markdown)

if __name__ == '__main__':
    unittest.main()
