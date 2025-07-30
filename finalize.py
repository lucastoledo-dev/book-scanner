import os
from threading import Thread, Event
import img2pdf

class FinalizeThread(Thread):
    def __init__(self, session_path):
        super().__init__(daemon=True)
        self.processed = os.path.join(session_path, "processed")
        self.final = os.path.join(session_path, "final")
        self.trigger = Event()

    def run(self):
        self.trigger.wait()
        imgs = sorted(os.listdir(self.processed))
        paths = [os.path.join(self.processed, f) for f in imgs]
        pdf_path = os.path.join(self.final, "scan.pdf")
        with open(pdf_path, "wb") as f:
            f.write(img2pdf.convert(paths))

    def trigger_finalize(self):
        self.trigger.set()
