from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                           QTextEdit, QFileDialog, QGroupBox, QSplitter,
                           QStatusBar, QProgressBar)
from PyQt6.QtGui import QIntValidator, QIcon
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtCore import QObject, Qt, QTimer
from pypdf import PdfReader, PdfWriter
from pytesseract import pytesseract
import pymupdf
import os

from config import configs
from utils.pdf import open_pdf
from .signals import TextUpdateSignals
from core import OCRWorker

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

        # 프로그레스바 추가
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.statusBar.addPermanentWidget(self.progress_bar)

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
        ocr_layout = QHBoxLayout()
        
        self.ocr_btn = QPushButton("Extract Text (OCR)")
        self.ocr_btn.clicked.connect(self.start_read_thread)
        ocr_layout.addWidget(self.ocr_btn)

        # Stop 버튼
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_read_thread)
        self.stop_btn.setEnabled(False)  # 초기에는 비활성화
        ocr_layout.addWidget(self.stop_btn)

        main_layout.addLayout(ocr_layout)

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

        outline_layout = QHBoxLayout()
        
        # Write outlines 버튼
        write_btn = QPushButton("Write outlines")
        write_btn.clicked.connect(self.write_outlines)
        outline_layout.addWidget(write_btn)

        # Copy outlines 버튼
        copy_btn = QPushButton("Copy outlines from...")
        copy_btn.clicked.connect(self.copy_outlines)
        outline_layout.addWidget(copy_btn)

        main_layout.addLayout(outline_layout)

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

        # 프로그레스바 초기화 및 표시
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.statusBar.showMessage("OCR 텍스트 추출 중...")
        
        # 이전 worker가 있다면 정리
        if self.worker is not None and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        
        # 새로운 worker 생성 및 시작
        tesseract_path = self.tesseract_path.text() or None
        self.worker = OCRWorker(self.original_filename, first_page, last_page, tesseract_path)
        self.worker.progress.connect(self.signals.update_text.emit)
        self.worker.progress_percent.connect(self.progress_bar.setValue)
        self.worker.status_message.connect(self.statusBar.showMessage)
        self.worker.error.connect(self.on_ocr_error)
        self.worker.finished.connect(self.on_ocr_complete)
        self.worker.start()

        # 버튼 상태 변경
        self.ocr_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def stop_read_thread(self):
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.progress_bar.setVisible(False)  # 프로그레스바 숨기기
            self.statusBar.showMessage("텍스트 추출이 중단되었습니다.", 3000)  # 상태바 메시지 업데이트
            # 버튼 상태 복원
            self.ocr_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def on_ocr_complete(self):
        self.progress_bar.setVisible(False)
        self.statusBar.showMessage("OCR 텍스트 추출이 완료되었습니다.", 3000)
        # 버튼 상태 복원
        self.ocr_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def on_ocr_error(self, error_message):
        self.progress_bar.setVisible(False)
        self.statusBar.showMessage(f"OCR 오류 발생: {error_message}", 5000)
        # 버튼 상태 복원
        self.ocr_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

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

        output_path = f"{path.replace('.pdf', '')}_created_outline.pdf"
        pdf_writer.write(output_path)

        open_pdf(output_path)

    def copy_outlines(self):
        if not self.original_filename:
            self.signals.update_message.emit("먼저 대상 PDF 파일을 열어주세요.")
            return

        # 아웃라인을 복사할 소스 PDF 파일 선택
        source_filename, _ = QFileDialog.getOpenFileName(
            self, "Select PDF with outlines", "", "PDF files (*.pdf);;All files (*.*)")
        
        if not source_filename:
            return

        try:
            # PyMuPDF로 소스 PDF 열기
            source_doc = pymupdf.open(source_filename)
            print("\n=== PyMuPDF 문서 정보 ===")
            print(f"총 페이지 수: {len(source_doc)}")
            
            # 소스 PDF의 아웃라인 읽기
            source_pdf = PdfReader(source_filename)
            outlines = source_pdf.outline
            if not outlines:
                self.signals.update_message.emit("선택한 PDF 파일에 아웃라인이 없습니다.")
                source_doc.close()
                return

            # 대상 PDF 준비
            target_pdf = PdfReader(self.original_filename)
            pdf_writer = PdfWriter()

            # 모든 페이지 복사
            for page in target_pdf.pages:
                pdf_writer.add_page(page)

            # 아웃라인 복사
            self._copy_outline_items(outlines, pdf_writer, source_doc)

            # 최종 파일 경로 생성
            output_dir = os.path.dirname(self.original_filename)
            base_name = os.path.splitext(os.path.basename(self.original_filename))[0]
            output_path = os.path.join(output_dir, f"{base_name}_copied_outline.pdf")

            # 파일명 중복 확인 및 처리
            i = 1
            while os.path.exists(output_path):
                output_path = os.path.join(output_dir, f"{base_name}_copied_outline_{i}.pdf")
                i += 1

            # 파일 저장
            pdf_writer.write(output_path)
            source_doc.close()

            # PDF 뷰어에서 현재 파일 닫기
            # self.pdf_document.close()

            self.signals.update_message.emit("아웃라인이 성공적으로 복사되었습니다.")
            
            # 잠시 대기 후 새 파일 열기
            QTimer.singleShot(100, lambda: open_pdf(output_path))

        except Exception as e:
            self.signals.update_message.emit(f"아웃라인 복사 중 오류가 발생했습니다: {str(e)}")
            print(f"아웃라인 복사 중 오류가 발생했습니다: {str(e)}")

    def _copy_outline_items(self, outlines, pdf_writer, source_doc, parent=None):
        """재귀적으로 아웃라인 항목을 복사"""
        if not outlines:
            return

        for item in outlines:
            if isinstance(item, list):
                # 하위 아웃라인이 있는 경우 재귀적으로 처리
                self._copy_outline_items(item, pdf_writer, source_doc, current_parent)
            else:
                # 아웃라인 항목 추가
                title = item.title
                page_number = 0

                # 디버깅을 위한 정보 출력
                print(f"\n=== 아웃라인 항목: {title} ===")
                print(f"item type: {type(item)}")
                
                if hasattr(item, 'page'):
                    page_obj = item.page.get_object()
                    print(f"page object: {page_obj}")
                    
                    # PyMuPDF로 페이지 번호 확인
                    try:
                        if hasattr(page_obj, 'indirect_reference'):
                            page_ref = page_obj.indirect_reference
                            page_xref = page_ref.idnum
                            for page_num in range(len(source_doc)):
                                if source_doc[page_num].xref == page_xref:
                                    print(f"PyMuPDF page number: {page_num + 1}")
                                    page_number = page_num
                                    break
                    except Exception as e:
                        print(f"PyMuPDF page number error: {str(e)}")

                # 현재 아웃라인 항목 추가
                current_parent = pdf_writer.add_outline_item(
                    title=title,
                    page_number=page_number,
                    parent=parent
                )

                # 하위 항목이 있는 경우 재귀적으로 처리
                if isinstance(item, dict) and '/First' in item:
                    self._process_child_items(item, pdf_writer, current_parent, source_doc)

    def _process_child_items(self, parent_item, pdf_writer, outline_parent, source_doc):
        """하위 아웃라인 항목을 처리"""
        current = parent_item['/First'].get_object()
        while current:
            title = current.get('/Title', '')
            page_number = 0

            # 디버깅을 위한 정보 출력
            print(f"\n=== 하위 아웃라인 항목: {title} ===")
            print(f"current type: {type(current)}")

            # 페이지 번호 추출 시도
            try:
                if '/D' in current:
                    dest = current['/D']
                    print(f"Destination object: {dest}")
                    if isinstance(dest, list) and len(dest) > 0:
                        page_ref = dest[0].get_object()
                        print(f"Page object: {page_ref}")
                        
                        if hasattr(page_ref, 'indirect_reference'):
                            ref = page_ref.indirect_reference
                            page_xref = ref.idnum
                            for page_num in range(len(source_doc)):
                                if source_doc[page_num].xref == page_xref:
                                    print(f"PyMuPDF page number: {page_num + 1}")
                                    page_number = page_num
                                    break
                elif '/Dest' in current:
                    dest = current['/Dest']
                    print(f"Destination object: {dest}")
                    if isinstance(dest, list) and len(dest) > 0:
                        page_ref = dest[0].get_object()
                        print(f"Page object: {page_ref}")
                        
                        if hasattr(page_ref, 'indirect_reference'):
                            ref = page_ref.indirect_reference
                            page_xref = ref.idnum
                            for page_num in range(len(source_doc)):
                                if source_doc[page_num].xref == page_xref:
                                    print(f"PyMuPDF page number: {page_num + 1}")
                                    page_number = page_num
                                    break
            except Exception as e:
                print(f"Error extracting page number: {str(e)}")
                page_number = 0

            # 현재 아웃라인 항목 추가
            current_outline = pdf_writer.add_outline_item(
                title=title,
                page_number=page_number,
                parent=outline_parent
            )

            # 하위 항목이 있는 경우 재귀적으로 처리
            if '/First' in current:
                self._process_child_items(current, pdf_writer, current_outline, source_doc)

            # 다음 형제 항목으로 이동
            if '/Next' in current:
                current = current['/Next'].get_object()
            else:
                break 
