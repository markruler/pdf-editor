# PDF Editor

![PDF Editor](misc/pdf-editor.png)

## Dependencies

- Google Tesseract OCR
- PyQt
- PyMuPDF

## Tesseract OCR 설치

- [tesseract](https://github.com/tesseract-ocr/tesseract)
  - Windows 11의 기본 설치 경로는 `C:\Program Files\Tesseract-OCR`
- [tessdata](https://github.com/tesseract-ocr/tessdata)는 다운로드 후 설치 경로의 `tessdata` 폴더에 복사
  - [kor](https://github.com/tesseract-ocr/tessdata/blob/main/kor.traineddata)
  - [세로 kor](https://github.com/tesseract-ocr/tessdata/blob/main/kor_vert.traineddata)

## Installation

```shell
# Virtual Environment 생성
python -m venv venv

# Windows 11
venv\Scripts\activate
# Unix-like
source venv/bin/activate

# 패키지 설치
pip install -r requirements.txt
```

```shell
make build
```

- `--onefile` 실행 파일을 하나의 단일 파일로 패키징.
- `--windowed` 콘솔 창 없이 GUI 모드로 실행.
- `--clean` 옵션은 빌드를 시작하기 전에 PyInstaller가 이전 빌드에서 생성한 임시 파일들을 삭제한다.

혹은 `.spec` 파일을 작성해서 빌드한다.

```shell
pyinstaller --clean app.spec
```
