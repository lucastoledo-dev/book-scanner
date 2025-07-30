# capture.py
import cv2
import time
import os
from threading import Thread, Lock

class CaptureThread(Thread):
    def __init__(self, session_path, source):
        super().__init__(daemon=True)
        self.raw_dir       = os.path.join(session_path, "raw")
        self.source        = source
        self.running       = True

        # sincronização
        self._frame_lock   = Lock()
        self._contour_lock = Lock()
        self.last_frame    = None
        self.last_contour  = None

        # detecta contornos que ocupem ≥20% do frame (sem limite superior)
        self.min_area_ratio = 0.20  

        # estado: 'idle' (aguardando página) ou 'waiting' (aguardando remover)
        self.state = 'idle'

    def run(self):
        # abre a câmera UMA vez
        if self.source.isdigit():
            idx     = int(self.source)
            backend = cv2.CAP_DSHOW if os.name=='nt' else cv2.CAP_V4L2
            cap     = cv2.VideoCapture(idx, backend)
        else:
            cap     = cv2.VideoCapture(self.source)

        if not cap.isOpened():
            print(f"[ERROR] não abriu fonte {self.source}")
            return

        # lê um frame só para pegar tamanho
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

            # atualiza último frame (para preview)
            with self._frame_lock:
                self.last_frame = frame.copy()

            # pre‐processamento e extração de contornos
            gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5,5), 0)
            edged   = cv2.Canny(blurred, 50, 150)
            cnts, _ = cv2.findContours(edged,
                                       cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)

            found = None
            # pega o maior quadrilátero que ocupe ≥ min_area_ratio
            for c in sorted(cnts, key=cv2.contourArea, reverse=True):
                peri   = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.02 * peri, True)
                if len(approx) != 4:
                    continue
                area  = cv2.contourArea(approx)
                if area / frame_area < self.min_area_ratio:
                    continue
                found = approx
                break

            # guarda para o preview
            with self._contour_lock:
                self.last_contour = found

            # ----- lógica de captura -----
            if self.state == 'idle':
                if found is not None:
                    # capturar no primeiro quadro que surgir o contorno
                    fname = os.path.join(self.raw_dir,
                                         f"{int(time.time())}.jpg")
                    cv2.imwrite(fname, frame)
                    print(f"[CAPTURED] {fname}")
                    self.state = 'waiting'
            else:  # 'waiting'
                # só volta a idle quando o contorno some (vc retira a página)
                if found is None:
                    self.state = 'idle'

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
