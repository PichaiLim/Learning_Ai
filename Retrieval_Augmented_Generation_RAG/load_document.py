import os
from dotenv import load_dotenv
from pdf2image import convert_from_path
load_dotenv()

# ============================================================================
# TODO: LOAD DOCUMENT
# 1) Get document all in folder
# 2) Using pdf2image to convert pdf to image
# 3) Using img2pdf to convert image to pdf
# ============================================================================
class LoadDocument:
    def __init__(self):
        self.base_dir = os.path.dirname(__file__)
        self.pdf_path = os.path.join(self.base_dir, 'media', 'PDPA_thailand.pdf')
        self.output_path = os.path.join(self.base_dir, 'media/output')

    def documetn_in_folder(self, folder_path, file_name):
        for file in os.listdir(folder_path):
            if not file.endswith(file_name):
                continue
            return file
        return None

    # TODO: Convert PDF to Image
    # pdf_path : พาธไฟล์ PDF
    # output_path : พาธโฟลเดอร์ที่จะบันทึกรูปภาพ
    # orientation='portrait' : แนวตั้ง
    # orientation='landscape' : แนวนอน
    # dpi=300 : ความละเอียด
    # image_format='JPEG' : รูปแบบไฟล์
    def convert_pdf_to_image(self, pdf_path, output_path, dpi=300, orientation='portrait', image_format='JPEG'):
        images = convert_from_path(pdf_path, dpi=dpi, orientation=orientation)
        for i, image in enumerate(images):
            image.save(f'{output_path}/images/page_{i+1}.{image_format}', image_format.upper())

if __name__ == '__main__':
    load_document = LoadDocument()
    print(load_document.documetn_in_folder(load_document.base_dir, 'PDPA_thailand.pdf'))