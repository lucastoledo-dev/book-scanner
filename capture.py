import cv2, time, os
from threading import Thread, Lock
import numpy as np

class CaptureThread(Thread):
    def __init__(self, session_path, source):
        super().__init__(daemon=True)
        self.raw_dir      = os.path.join(session_path, "raw")
        self.source       = source
        self.running      = True

        self._frame_lock   = Lock()
        self._contour_lock = Lock()
        self.last_frame    = None
        self.last_contour  = None

        # parâmetros de detecção
        self.min_area_ratio   = 0.20
        self.max_area_ratio   = 0.90
        self.min_aspect       = 0.5
        self.max_aspect       = 2.0

        # limiar de similaridade de histogramas
        # 1.0 = idêntico; quanto menor, menos parecido
        self.hist_threshold   = 0.7

        self.last_hist = None  # histograma da última página salva

    def run(self):
        # abre a câmera
        if self.source.isdigit():
            idx     = int(self.source)
            backend = cv2.CAP_DSHOW if os.name=='nt' else cv2.CAP_V4L2
            cap = cv2.VideoCapture(idx, backend)
        else:
            cap = cv2.VideoCapture(self.source)

        if not cap.isOpened():
            print(f"[ERROR] não abriu fonte {self.source}")
            return

        # lê dimensões
        ret, tmp = cap.read()
        if not ret:
            print("[ERROR] não leu frame inicial.")
            return
        h, w = tmp.shape[:2]
        frame_area = h * w
        print(f"[INFO] captura iniciada: resolução {w}×{h}")

        while self.running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            # guarda frame para preview
            with self._frame_lock:
                self.last_frame = frame.copy()

            # detecta contorno quadrilátero
            gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5,5), 0)
            edged   = cv2.Canny(blurred, 50, 150)
            cnts, _ = cv2.findContours(edged,
                                       cv2.RETR_LIST,
                                       cv2.CHAIN_APPROX_SIMPLE)

            found = None
            for c in cnts:
                peri   = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.02 * peri, True)
                if len(approx) != 4:
                    continue
                area = cv2.contourArea(approx)
                aratio = area / frame_area
                if aratio < self.min_area_ratio or aratio > self.max_area_ratio:
                    continue
                x,y,ww,hh = cv2.boundingRect(approx)
                aspect = max(ww,hh) / min(ww,hh)
                if aspect < self.min_aspect or aspect > self.max_aspect:
                    continue
                found = approx
                break

            with self._contour_lock:
                self.last_contour = found

            # se detectou página, extrai crop e compara histograma
            if found is not None:
                x,y,ww,hh = cv2.boundingRect(found)
                crop = frame[y:y+hh, x:x+ww]
                hsv  = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                # histograma 2D HxS
                hist = cv2.calcHist([hsv], [0,1], None,
                                    [50, 60],
                                    [0,180, 0,256])
                cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)

                new_page = False
                if self.last_hist is None:
                    new_page = True
                else:
                    # compara correlação
                    corr = cv2.compareHist(self.last_hist, hist,
                                           cv2.HISTCMP_CORREL)
                    if corr < self.hist_threshold:
                        new_page = True

                if new_page:
                    # captura full frame
                    fname = os.path.join(self.raw_dir,
                                         f"{int(time.time())}.jpg")
                    cv2.imwrite(fname, frame)
                    print(f"[CAPTURED] {fname}")
                    # atualiza referência
                    self.last_hist = hist.copy()

            time.sleep(0.1)

        cap.release()

    def stop(self):
        self.running = False

    def get_frame(self):
        with self._frame_lock:
            return None if self.last_frame is None else self.last_frame.copy()

    def get_contour(self):
        with self._contour_lock:
            return None if self.last_contour is None else self.last_contour.copy()
