import io
from concurrent.futures import ThreadPoolExecutor

import pymupdf
from PIL import Image
from PyQt6.QtCore import QThread, pyqtSignal
from pytesseract import image_to_string

from config import configs

class Worker(QThread):
    finished = pyqtSignal()
    progress = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, filename, first_page, last_page, parent=None):
        super().__init__(parent)
        self.filename = filename
        self.first_page = int(first_page)
        self.last_page = int(last_page)
        self.executor = ThreadPoolExecutor(max_workers=configs["worker"]["max_workers"])

    def read_text(self, page_index: int, pdf_file: pymupdf.Document, lang: str):
        page = pdf_file[page_index - 1]
        image_li = page.get_images()

        if not image_li:
            return ""

        for img in image_li:
            base_image = pdf_file.extract_image(img[0])
            image = Image.open(io.BytesIO(base_image["image"]))
            txt = image_to_string(image, lang=lang)

            return (txt.strip()
                    .replace("\r\n", "\n")
                    .replace("\n\n", "\n")
                    .replace(" ", ""))

    def run(self):
        try:
            pdf_file = pymupdf.open(self.filename)
            
            for page_index in range(self.first_page, self.last_page + 1):
                content = self.read_text(page_index, pdf_file, "eng+kor")
                if content:
                    self.progress.emit(content)
            
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e)) 