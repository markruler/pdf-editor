run:
	python app.py
.PHONY: run

build:
	pyinstaller --onefile --windowed --clean --add-data "assets/*;assets" --add-data "configs.toml;." --icon assets/icon.ico app.py
.PHONY: build
