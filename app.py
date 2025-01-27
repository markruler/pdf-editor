import sys
# import ctypes
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from gui.window import App

if __name__ == "__main__":
    # Windows 작업 표시줄 아이콘 설정
    # myappid = "markruler.pdf-editor.1.0"  # 임의의 문자열 ID
    # ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    app = QApplication(sys.argv)
    
    # 아이콘 설정
    icon_path = Path(__file__).parent / "assets" / "icon.ico"
    app.setWindowIcon(QIcon(str(icon_path)))
    
    window = App()
    window.show()
    sys.exit(app.exec())
