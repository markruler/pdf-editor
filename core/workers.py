from PyQt6.QtCore import QThread, pyqtSignal
from concurrent.futures import ThreadPoolExecutor
import pymupdf
from PIL import Image
from pytesseract import image_to_string, pytesseract
import io

from config import configs

class OCRWorker(QThread):
    progress = pyqtSignal(str)  # 텍스트 업데이트용
    progress_percent = pyqtSignal(int)  # 프로그레스바용
    status_message = pyqtSignal(str)  # 상태바 메시지용
    error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, filename, first_page, last_page, tesseract_path=None):
        super().__init__()
        self.filename = filename
        self.first_page = int(first_page)
        self.last_page = int(last_page)
        self.executor = ThreadPoolExecutor(max_workers=configs["worker"]["max_workers"])
        self._stop = False
        
        # Tesseract 경로 설정
        if tesseract_path:
            pytesseract.tesseract_cmd = tesseract_path
        else:
            pytesseract.tesseract_cmd = configs["tesseract"]["default_cmd_path"]

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
            print(f"PDF 열기 성공: {self.filename}")
            print(f"총 페이지 수: {len(pdf_file)}")
            print(f"처리할 페이지 범위: {self.first_page} - {self.last_page}")
            
            total_pages = self.last_page - self.first_page + 1
            
            for i, page_index in enumerate(range(self.first_page, self.last_page + 1)):
                if self._stop:
                    print("작업 중단 요청됨")
                    break
                
                print(f"페이지 {page_index} 처리 중...")
                self.status_message.emit(f"OCR 텍스트 추출 중... (Page {page_index})")
                content = self.read_text(page_index, pdf_file, "eng+kor")
                if content:
                    print(f"텍스트 추출 완료: {len(content)} 글자")
                    self.progress.emit(f"=== Page {page_index} ===\n{content}\n")
                
                # 진행률 업데이트
                progress = int((i + 1) / total_pages * 100)
                self.progress_percent.emit(progress)
            
            pdf_file.close()
            if not self._stop:
                print("모든 페이지 처리 완료")
                self.finished.emit()

        except Exception as e:
            print(f"오류 발생: {str(e)}")
            self.error.emit(str(e))
            self.finished.emit()

    def stop(self):
        print("작업 중단 요청")
        self._stop = True
