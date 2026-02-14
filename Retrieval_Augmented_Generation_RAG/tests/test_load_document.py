import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add parent directory to path to import load_document
sys.path.insert(0, str(Path(__file__).parent.parent))
from load_document import LoadDocument


class TestLoadDocument(unittest.TestCase):
    """Unit tests for LoadDocument class."""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.loader = LoadDocument()
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures after each test method."""
        if self.temp_path.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_init(self):
        """Test LoadDocument initialization."""
        self.assertIsInstance(self.loader.base_dir, Path)
        self.assertIsInstance(self.loader.pdf_path, Path)
        self.assertIsInstance(self.loader.output_path, Path)
        self.assertTrue(str(self.loader.pdf_path).endswith('PDPA_thailand.pdf'))
    
    def test_document_in_folder_file_exists(self):
        """Test finding a document that exists in folder."""
        # Create test file
        test_file = self.temp_path / 'test.pdf'
        test_file.touch()
        
        result = self.loader.document_in_folder(str(self.temp_path), 'test.pdf')
        self.assertEqual(result, 'test.pdf')
    
    def test_document_in_folder_file_not_exists(self):
        """Test searching for a document that doesn't exist."""
        result = self.loader.document_in_folder(str(self.temp_path), 'nonexistent.pdf')
        self.assertIsNone(result)
    
    def test_document_in_folder_invalid_path(self):
        """Test with invalid folder path."""
        with self.assertRaises(ValueError) as context:
            self.loader.document_in_folder('/invalid/path', 'test.pdf')
        self.assertIn('Invalid folder path', str(context.exception))
    
    def test_document_in_folder_file_as_path(self):
        """Test with a file path instead of folder path."""
        test_file = self.temp_path / 'test.pdf'
        test_file.touch()
        
        with self.assertRaises(ValueError) as context:
            self.loader.document_in_folder(str(test_file), 'test.pdf')
        self.assertIn('Invalid folder path', str(context.exception))
    
    def test_check_type_original_file_pdf(self):
        """Test file type detection for PDF files."""
        self.assertEqual(self.loader.check_type_original_file('document.pdf'), 'pdf')
        self.assertEqual(self.loader.check_type_original_file('document.PDF'), 'pdf')
        self.assertEqual(self.loader.check_type_original_file('/path/to/file.pdf'), 'pdf')
    
    def test_check_type_original_file_images(self):
        """Test file type detection for image files."""
        image_extensions = ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'gif']
        for ext in image_extensions:
            with self.subTest(ext=ext):
                self.assertEqual(
                    self.loader.check_type_original_file(f'image.{ext}'), 
                    'image'
                )
                self.assertEqual(
                    self.loader.check_type_original_file(f'image.{ext.upper()}'), 
                    'image'
                )
    
    def test_check_type_original_file_other(self):
        """Test file type detection for other file types."""
        other_files = ['document.txt', 'data.csv', 'script.py', 'video.mp4']
        for file in other_files:
            with self.subTest(file=file):
                self.assertEqual(self.loader.check_type_original_file(file), 'other')
    
    @patch('load_document.convert_from_path')
    def test_convert_pdf_to_image_success(self, mock_convert):
        """Test successful PDF to image conversion."""
        # Create test PDF file
        test_pdf = self.temp_path / 'test.pdf'
        test_pdf.touch()
        
        # Mock converted images
        mock_image = MagicMock()
        mock_convert.return_value = [mock_image, mock_image]
        
        output_path = self.temp_path / 'output'
        self.loader.convert_pdf_to_image(
            str(test_pdf), 
            str(output_path),
            dpi=300,
            orientation='portrait',
            image_format='JPEG'
        )
        
        # Verify convert_from_path was called correctly
        mock_convert.assert_called_once_with(
            str(test_pdf), 
            dpi=300, 
            orientation='portrait'
        )
        
        # Verify images were saved
        self.assertEqual(mock_image.save.call_count, 2)
    
    def test_convert_pdf_to_image_file_not_found(self):
        """Test PDF to image conversion with non-existent file."""
        with self.assertRaises(FileNotFoundError) as context:
            self.loader.convert_pdf_to_image(
                '/nonexistent/file.pdf',
                str(self.temp_path)
            )
        self.assertIn('PDF file not found', str(context.exception))
    
    def test_convert_pdf_to_image_not_pdf(self):
        """Test PDF to image conversion with non-PDF file."""
        # Create image file instead of PDF
        test_image = self.temp_path / 'test.jpg'
        test_image.touch()
        
        with self.assertRaises(ValueError) as context:
            self.loader.convert_pdf_to_image(
                str(test_image),
                str(self.temp_path)
            )
        self.assertIn('File is not a PDF', str(context.exception))
    
    @patch('load_document.img2pdf.convert')
    def test_convert_image_to_pdf_success(self, mock_img2pdf):
        """Test successful image to PDF conversion."""
        # Create test image file
        test_image = self.temp_path / 'test.jpg'
        test_image.touch()
        
        mock_img2pdf.return_value = b'fake_pdf_content'
        
        output_pdf = self.temp_path / 'output.pdf'
        self.loader.convert_image_to_pdf(str(test_image), str(output_pdf))
        
        # Verify img2pdf.convert was called
        mock_img2pdf.assert_called_once_with(str(test_image))
        
        # Verify output file was created
        self.assertTrue(output_pdf.exists())
    
    def test_convert_image_to_pdf_file_not_found(self):
        """Test image to PDF conversion with non-existent file."""
        with self.assertRaises(FileNotFoundError) as context:
            self.loader.convert_image_to_pdf(
                '/nonexistent/image.jpg',
                str(self.temp_path / 'output.pdf')
            )
        self.assertIn('Image file not found', str(context.exception))
    
    def test_convert_image_to_pdf_not_image(self):
        """Test image to PDF conversion with non-image file."""
        # Create PDF file instead of image
        test_pdf = self.temp_path / 'test.pdf'
        test_pdf.touch()
        
        with self.assertRaises(ValueError) as context:
            self.loader.convert_image_to_pdf(
                str(test_pdf),
                str(self.temp_path / 'output.pdf')
            )
        self.assertIn('File is not an image', str(context.exception))
    
    @patch('load_document.convert_from_path')
    def test_convert_pdf_to_image_landscape(self, mock_convert):
        """Test PDF to image conversion with landscape orientation."""
        test_pdf = self.temp_path / 'test.pdf'
        test_pdf.touch()
        
        mock_image = MagicMock()
        mock_convert.return_value = [mock_image]
        
        output_path = self.temp_path / 'output'
        self.loader.convert_pdf_to_image(
            str(test_pdf),
            str(output_path),
            orientation='landscape'
        )
        
        mock_convert.assert_called_once_with(
            str(test_pdf),
            dpi=300,
            orientation='landscape'
        )
    
    @patch('load_document.convert_from_path')
    def test_convert_pdf_to_image_custom_dpi(self, mock_convert):
        """Test PDF to image conversion with custom DPI."""
        test_pdf = self.temp_path / 'test.pdf'
        test_pdf.touch()
        
        mock_image = MagicMock()
        mock_convert.return_value = [mock_image]
        
        output_path = self.temp_path / 'output'
        self.loader.convert_pdf_to_image(
            str(test_pdf),
            str(output_path),
            dpi=150
        )
        
        mock_convert.assert_called_once_with(
            str(test_pdf),
            dpi=150,
            orientation='portrait'
        )


if __name__ == '__main__':
    unittest.main()
