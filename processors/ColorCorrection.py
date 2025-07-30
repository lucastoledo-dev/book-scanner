from PIL import Image, ImageEnhance

class ColorCorrection:
    def process(self, img_path):
        img = Image.open(img_path)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.1)
        img.save(img_path)
        return img_path
