import cv2
import time
import os
from threading import Thread, Lock
from skimage.metrics import structural_similarity as compare_ssim
import numpy as np

class CaptureThread(Thread):
    def __init__(self, session_path, source):
        super().__init__(daemon=True)
        self.raw_dir       = os.path.join(session_path, "raw")
        self.source        = source
        self.running       = True

        self._frame_lock   = Lock()
        self._contour_lock = Lock()
        self.roi           = None          # (x,y,w,h) definido pelo usuário
        self.last_frame    = None

        self.last_crop     = None
        self.ssim_thresh   = 0.90
        self.cooldown      = 1.0
        self.last_capture  = 0

    def set_roi(self, x, y, w, h):
        """Define a região de interesse."""
        self.roi = (x, y, w, h)

    def get_roi(self):
        return self.roi

    def run(self):
        # abre a câmera
        if self.source.isdigit():
            idx     = int(self.source)
            backend = cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_V4L2
            cap     = cv2.VideoCapture(idx, backend)
        else:
            cap     = cv2.VideoCapture(self.source)

        if not cap.isOpened():
            print(f"[ERROR] não abriu fonte {self.source}")
            return

        # leitura inicial apenas para garantir que funciona
        ret, tmp = cap.read()
        if not ret:
            print("[ERROR] não leu frame inicial.")
            return
        print("[INFO] captura iniciada")

        while self.running:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            now = time.time()
            # atualiza último frame para preview
            with self._frame_lock:
                self.last_frame = frame.copy()

            # processa somente se ROI estiver definida e cooldown vencido
            if self.roi and (now - self.last_capture) > self.cooldown:
                x, y, w, h = self.roi
                crop       = frame[y:y+h, x:x+w]
                gray       = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                rs         = cv2.resize(gray, (300, 300))

                # decide se captura
                if self.last_crop is None:
                    do_cap = True
                    score  = None
                else:
                    score  = compare_ssim(self.last_crop, rs)
                    do_cap = (score < self.ssim_thresh)

                # **debug print seguro**
                score_str = "n/a" if score is None else f"{score:.2f}"
                action    = "CAPTURE" if do_cap else "skip"
                print(f"[DEBUG] ssim={score_str} → {action}")

                if do_cap:
                    fname = os.path.join(self.raw_dir, f"{int(now)}.jpg")
                    cv2.imwrite(fname, frame)
                    print(f"[CAPTURED] {fname}")
                    self.last_crop    = rs
                    self.last_capture = now

            time.sleep(0.1)

        cap.release()

    def stop(self):
        self.running = False

    def get_frame(self):
        with self._frame_lock:
            return None if self.last_frame is None else self.last_frame.copy()

    def get_contour(self):
        # compatibilidade, não usado neste modo de captura
        return None
