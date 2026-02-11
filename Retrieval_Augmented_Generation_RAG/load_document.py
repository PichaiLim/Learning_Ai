import os
from pathlib import Path
from typing import Optional, Literal
from dotenv import load_dotenv
from pdf2image import convert_from_path
import img2pdf

load_dotenv()


class LoadDocument:
    """
    Document loader utility for converting between PDF and image formats.
    
    Supports:
    - PDF to Image conversion
    - Image to PDF conversion
    - File type detection
    """
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.pdf_path = self.base_dir / 'media' / 'PDPA_thailand.pdf'
        self.output_path = self.base_dir / 'media' / 'output'
    
    def document_in_folder(self, folder_path: str, file_name: str) -> Optional[str]:
        """
        Find a document in the specified folder.
        
        Args:
            folder_path: Path to the folder to search
            file_name: Name of the file to find
            
        Returns:
            The filename if found, None otherwise
        """
        folder = Path(folder_path)
        if not folder.exists() or not folder.is_dir():
            raise ValueError(f"Invalid folder path: {folder_path}")
        
        for file in folder.iterdir():
            if file.name == file_name:
                return file.name
        return None
    
    def check_type_original_file(self, file_path: str) -> Literal['pdf', 'image', 'other']:
        """
        Check the type of the file based on its extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            'pdf', 'image', or 'other'
        """
        file_extension = Path(file_path).suffix.lower().lstrip('.')
        
        if file_extension == 'pdf':
            return 'pdf'
        elif file_extension in ['jpg', 'jpeg', 'png', 'bmp', 'tiff', 'gif']:
            return 'image'
        else:
            return 'other'
    
    def convert_pdf_to_image(
        self, 
        pdf_path: str, 
        output_path: str, 
        dpi: int = 300, 
        orientation: Literal['portrait', 'landscape'] = 'portrait', 
        image_format: str = 'JPEG'
    ) -> None:
        """
        Convert PDF to images.
        
        Args:
            pdf_path: Path to the PDF file
            output_path: Path to save the output images
            dpi: Resolution (default: 300)
            orientation: 'portrait' (แนวตั้ง) or 'landscape' (แนวนอน)
            image_format: Output format (default: 'JPEG')
            
        Raises:
            ValueError: If the file is not a PDF
            FileNotFoundError: If the PDF file doesn't exist
        """
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        if self.check_type_original_file(pdf_path) != 'pdf':
            raise ValueError(f"File is not a PDF: {pdf_path}")
        
        output_dir = Path(output_path) / 'images'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        images = convert_from_path(pdf_path, dpi=dpi, orientation=orientation)
        for i, image in enumerate(images, start=1):
            output_file = output_dir / f'page_{i}.{image_format.lower()}'
            image.save(output_file, image_format.upper())
    
    def convert_image_to_pdf(self, image_path: str, output_path: str) -> None:
        """
        Convert image to PDF.
        
        Args:
            image_path: Path to the image file
            output_path: Path to save the output PDF
            
        Raises:
            ValueError: If the file is not an image
            FileNotFoundError: If the image file doesn't exist
        """
        image_file = Path(image_path)
        if not image_file.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        if self.check_type_original_file(image_path) != 'image':
            raise ValueError(f"File is not an image: {image_path}")
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "wb") as f:
            f.write(img2pdf.convert(str(image_file)))


if __name__ == '__main__':
    load_document = LoadDocument()
    found_file = load_document.document_in_folder(
        str(load_document.base_dir), 
        'PDPA_thailand.pdf'
    )
    print(f"Found file: {found_file}")