#!/usr/bin/env bash
set -euo pipefail

echo "==> Atualizando sistema"
apt update && apt upgrade -y

echo "==> Instalando pacotes"
apt install -y python3 python3-venv python3-pip ffmpeg v4l-utils tesseract-ocr libtesseract-dev git

PROJECT_DIR="/opt/book-scanner"
echo "==> Criando $PROJECT_DIR"
mkdir -p "$PROJECT_DIR" && chown $SUDO_USER:"$SUDO_USER" "$PROJECT_DIR"

echo "==> Criando virtualenv"
sudo -u $SUDO_USER bash -lc "
cd '$PROJECT_DIR'
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install opencv-python watchdog img2pdf flask pillow pytesseract
"

echo "==> Criando estrutura de pastas"
sudo -u $SUDO_USER bash -lc "
cd '$PROJECT_DIR'
mkdir -p processors templates static/css static/js data/sessions
"

cat << EOF
✅ Setup concluído em $PROJECT_DIR
Use:
  cd $PROJECT_DIR
  source venv/bin/activate
  flask run --host=0.0.0.0
EOF
