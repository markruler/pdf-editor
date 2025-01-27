import platform
import subprocess

def open_pdf(path: str):
    """시스템에 맞는 PDF 뷰어로 파일을 엽니다."""
    system = platform.system()
    if system == 'Windows':
        subprocess.Popen(["start", "", path], shell=True)
    elif system == "Darwin":
        subprocess.Popen(["open", "-a", "Preview", path])
    elif system == "Linux":
        subprocess.Popen(["xdg-open", path])
    else:
        print("Unsupported OS") 