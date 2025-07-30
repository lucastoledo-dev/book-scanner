import os, time
from threading import Thread
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from processors.CropDetector import CropDetector
from processors.Deskew import Deskew
from processors.ColorCorrection import ColorCorrection
from processors.OCR import OCR

class PipelineHandler(FileSystemEventHandler):
    def __init__(self, session_path):
        self.raw = os.path.join(session_path, "raw")
        self.processed = os.path.join(session_path, "processed")
        self.processors = [
            CropDetector(), Deskew(), ColorCorrection(), OCR()
        ]

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".jpg"):
            self.process(event.src_path)

    def process(self, path):
        img_path = path
        for p in self.processors:
            img_path = p.process(img_path)
        # move para processed
        fname = os.path.basename(path)
        os.replace(img_path, os.path.join(self.processed, fname))

class PipelineThread(Thread):
    def __init__(self, session_path):
        super().__init__(daemon=True)
        self.handler = PipelineHandler(session_path)

    def run(self):
        obs = Observer()
        obs.schedule(self.handler, self.handler.raw, recursive=False)
        obs.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            obs.stop()
        obs.join()
