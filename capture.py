import cv2
import time
import os
from threading import Thread, Lock

class CaptureThread(Thread):
    def __init__(self, session_path, source):
        super().__init__(daemon=True)
        self.raw_dir     = os.path.join(session_path, "raw")
        self.source      = source
        self.running     = True
        self.cap         = None
        self.last_frame  = None
        self._frame_lock = Lock()

    def run(self):
        # Abre a câmera UMA vez, usando DirectShow no Windows
        if self.source.isdigit():
            idx = int(self.source)
            backend = cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_V4L2
            self.cap = cv2.VideoCapture(idx, backend)
        else:
            self.cap = cv2.VideoCapture(self.source)

        if not self.cap.isOpened():
            print(f"[ERROR] Não foi possível acessar a câmera: {self.source}")
            return

        prev_gray = None
        count     = 0

        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            # Guarda thread-safe para o preview
            with self._frame_lock:
                self.last_frame = frame.copy()

            # detecção de estabilidade
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev_gray is None:
                prev_gray = gray
                continue

            diff     = cv2.absdiff(prev_gray, gray)
            motion   = cv2.countNonZero(diff)
            prev_gray = None if motion < 10000 else gray

            if motion < 10000:
                path = os.path.join(self.raw_dir, f"{count:04d}.jpg")
                cv2.imwrite(path, frame)
                count += 1
                time.sleep(0.5)

        self.cap.release()

    def stop(self):
        self.running = False

    def get_frame(self):
        """Retorna o último frame capturado (ou None)."""
        with self._frame_lock:
            return None if self.last_frame is None else self.last_frame.copy()
