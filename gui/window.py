from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                           QTextEdit, QFileDialog, QGroupBox, QSplitter,
                           QStatusBar)
from PyQt6.QtGui import QIntValidator, QIcon
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtCore import QObject, Qt
from pypdf import PdfReader, PdfWriter
from pytesseract import pytesseract

from config import configs
from core import Worker
from utils.pdf import open_pdf
from .signals import TextUpdateSignals

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        # 창 제목
        self.setWindowTitle("PDF Editor")

        # 창 사이즈
        self.resize(1200, 800)

        # 아이콘 설정
        icon_path = Path(__file__).parent.parent / "assets" / "icon.ico"
        self.setWindowIcon(QIcon(str(icon_path)))

        # PDF 문서 객체
        self.pdf_document = QPdfDocument(self)

        # 상태바 설정
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.page_label = QLabel()
        self.statusBar.addPermanentWidget(self.page_label)

        # 중앙 위젯 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QHBoxLayout(central_widget)
        
        # 좌측 컨트롤 패널
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        control_panel.setMaximumWidth(400)
        
        self.original_filename = ""
        self._create_widgets(control_layout)
        
        # PDF 뷰어
        self.pdf_view = QPdfView(self)
        self.pdf_view.setDocument(self.pdf_document)
        # 페이지 표시 설정
        self.pdf_view.setPageMode(QPdfView.PageMode.MultiPage)  # 모든 페이지 표시
        # self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)  # 너비에 맞춤
        self.pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)  # 전체 페이지가 보이도록
        self.pdf_view.setPageSpacing(10)  # 페이지 간 간격
        
        # 페이지 변경 시그널 연결
        self.pdf_view.pageNavigator().currentPageChanged.connect(self.update_page_info)
        
        # 스플리터 추가
        splitter = QSplitter()
        splitter.addWidget(control_panel)
        splitter.addWidget(self.pdf_view)
        splitter.setStretchFactor(1, 1)  # PDF 뷰어가 더 많은 공간을 차지하도록
        
        main_layout.addWidget(splitter)
        
        # 시그널 초기화는 위젯 생성 후에 수행
        self.signals = TextUpdateSignals()
        self.signals.update_text.connect(self.text_widget.append)
        self.signals.update_message.connect(self.message_label.setText)
        self.signals.clear_text.connect(self.text_widget.clear)
        
        self.worker = None

    def _create_widgets(self, main_layout):
        # Tesseract 설정 영역
        self._create_tesseract_settings(main_layout)

        # Open PDF 버튼
        open_btn = QPushButton("Open PDF")
        open_btn.clicked.connect(self.open_pdf)
        main_layout.addWidget(open_btn)

        # 페이지 정보 레이블
        self.page_info_label = QLabel()
        main_layout.addWidget(self.page_info_label)

        # 페이지 입력 영역
        self._create_page_inputs(main_layout)

        # 메시지 레이블
        self.message_label = QLabel()
        main_layout.addWidget(self.message_label)

        # OCR 버튼
        ocr_btn = QPushButton("Extract Text (OCR)")
        ocr_btn.clicked.connect(self.start_read_thread)
        main_layout.addWidget(ocr_btn)

        # 버튼들
        self._create_buttons(main_layout)

        # 텍스트 영역
        self._create_text_area(main_layout)

    def update_page_info(self, current_page):
        total_pages = self.pdf_document.pageCount()
        self.page_label.setText(f"Page {current_page + 1} of {total_pages}")

    def open_pdf(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open PDF", "", "PDF files (*.pdf);;All files (*.*)")
        
        if filename:
            self.original_filename = filename
            self.pdf_document.load(filename)
            total_pages = self.pdf_document.pageCount()
            self.page_info_label.setText(f"Total pages: {total_pages}")
            
            # 페이지 입력 필드의 validator 업데이트
            validator = QIntValidator(1, total_pages)
            self.first_page_entry.setValidator(validator)
            self.last_page_entry.setValidator(validator)
            
            # 기본값 설정
            self.first_page_entry.setText("1")
            self.last_page_entry.setText(str(total_pages))
            
            # 페이지 정보 초기화
            self.update_page_info(0)

    def _create_tesseract_settings(self, main_layout):
        group_box = QGroupBox("Tesseract OCR Settings")
        layout = QVBoxLayout()

        # Tesseract 경로 입력
        path_layout = QHBoxLayout()
        path_label = QLabel("Tesseract Path:")
        self.tesseract_path = QLineEdit()
        self.tesseract_path.setText(configs["tesseract"]["cmd_path"] or configs["tesseract"]["default_cmd_path"])
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_tesseract)

        path_layout.addWidget(path_label)
        path_layout.addWidget(self.tesseract_path)
        path_layout.addWidget(browse_btn)

        layout.addLayout(path_layout)
        group_box.setLayout(layout)
        main_layout.addWidget(group_box)

    def _browse_tesseract(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Tesseract Executable", "", 
            "Executable files (*.exe);;All files (*.*)")
        
        if filename:
            self.tesseract_path.setText(filename)
            configs["tesseract"]["cmd_path"] = filename

    def _create_page_inputs(self, main_layout):
        labels = ["First page", "Last page"]
        entries = []

        for label in labels:
            layout = QHBoxLayout()
            label_widget = QLabel(label)
            entry = QLineEdit()
            entry.setValidator(self._create_validator())
            
            layout.addWidget(label_widget)
            layout.addWidget(entry)
            main_layout.addLayout(layout)
            entries.append(entry)

        self.first_page_entry, self.last_page_entry = entries

    def _create_buttons(self, main_layout):
        button_layout = QHBoxLayout()
        
        # Undo 버튼
        undo_btn = QPushButton("Undo (Ctrl + Y)")
        undo_btn.clicked.connect(self.undo)
        button_layout.addWidget(undo_btn)

        # Redo 버튼
        redo_btn = QPushButton("Redo (Ctrl + Z)")
        redo_btn.clicked.connect(self.redo)
        button_layout.addWidget(redo_btn)

        main_layout.addLayout(button_layout)

        # Write outlines 버튼
        write_btn = QPushButton("Write outlines")
        write_btn.clicked.connect(self.write_outlines)
        main_layout.addWidget(write_btn)

    def _create_text_area(self, main_layout):
        self.text_widget = QTextEdit()
        self.text_widget.setUndoRedoEnabled(True)
        main_layout.addWidget(self.text_widget)

    def _create_validator(self):
        return QIntValidator()

    def start_read_thread(self):
        if not self.original_filename:
            self.signals.update_message.emit("먼저 PDF 파일을 열어주세요.")
            return

        self.signals.clear_text.emit()

        first_page = self.first_page_entry.text()
        last_page = self.last_page_entry.text()

        if not all([first_page, last_page]):
            self.signals.update_message.emit("페이지 번호를 입력해주세요.")
            return

        first_page = int(first_page)
        last_page = int(last_page)
        total_pages = self.pdf_document.pageCount()

        if first_page > last_page:
            self.signals.update_message.emit("시작 페이지가 마지막 페이지보다 클 수 없습니다.")
            return

        if first_page < 1 or last_page > total_pages:
            self.signals.update_message.emit(f"페이지 번호는 1에서 {total_pages} 사이여야 합니다.")
            return

        self.signals.update_message.emit(f"텍스트 추출 중... ({first_page} - {last_page} 페이지)")

        tesseract_path = self.tesseract_path.text()
        if tesseract_path:
            pytesseract.tesseract_cmd = tesseract_path
        else:
            pytesseract.tesseract_cmd = configs["tesseract"]["default_cmd_path"]
        
        # 이전 worker가 있다면 정리
        if self.worker is not None and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        
        # 새로운 worker 생성 및 시작
        self.worker = Worker(self.original_filename, first_page, last_page, self)
        self.worker.progress.connect(self.signals.update_text.emit)
        self.worker.error.connect(self.signals.update_message.emit)
        self.worker.finished.connect(lambda: self.signals.update_message.emit("텍스트 추출이 완료되었습니다."))
        self.worker.start()

    def undo(self):
        self.text_widget.undo()

    def redo(self):
        self.text_widget.redo()

    def write_outlines(self):
        if not self.original_filename:
            self.signals.update_message.emit("먼저 PDF 파일을 열어주세요.")
            return

        path = self.original_filename
        pdf_reader = PdfReader(path)
        pdf_writer = PdfWriter()

        for page in pdf_reader.pages:
            pdf_writer.add_page(page)

        lines = [line.strip() for line in self.text_widget.toPlainText().split('\n')
                if line.strip()]

        for line in lines:
            pdf_writer.add_outline_item(title=line, page_number=1)

        output_path = f"{path.replace('.pdf', '')}.outline.pdf"
        pdf_writer.write(output_path)

        open_pdf(output_path) 