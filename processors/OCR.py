# processors/OCR.py
import os
import pytesseract

class OCR:
    def process(self, img_path):
        try:
            text = pytesseract.image_to_string(img_path, lang='eng')
            txt_path = os.path.splitext(img_path)[0] + '.txt'
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(text)
        except pytesseract.TesseractNotFoundError:
            # pula OCR se não encontrar o executável
            pass
        return img_path
