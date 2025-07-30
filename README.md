# Book Scanner

## Visão geral
Sistema de captura manual de páginas de livro via webcam/celular, com pós-processamento e geração de PDF.

## Pré-requisitos
- Windows (PowerShell Admin) ou Ubuntu 22.04+
- Python 3.11+, FFmpeg, Tesseract OCR

## Instalação

### Windows
```powershell
.\setup_scanner_windows.ps1
cd C:\book-scanner
.\venv\Scripts\Activate.ps1
flask run --host=0.0.0.0
