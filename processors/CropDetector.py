import cv2, os

class CropDetector:
    def process(self, img_path):
        img = cv2.imread(img_path)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
        cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            c = max(cnts, key=cv2.contourArea)
            x,y,w,h = cv2.boundingRect(c)
            crop = img[y:y+h, x:x+w]
        else:
            crop = img
        out = img_path.replace("/raw/", "/processed/")
        cv2.imwrite(out, crop)
        return out
