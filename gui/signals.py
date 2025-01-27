from PyQt6.QtCore import QObject, pyqtSignal

class TextUpdateSignals(QObject):
    update_text = pyqtSignal(str)
    update_message = pyqtSignal(str)
    clear_text = pyqtSignal() 