# capture/screen.py
import threading
import time
from mss import mss
from PIL import Image
from ingest.ocr import ocr_image
from ingest.embed import embed_image
from db.init import table

class ScreenCapturer(threading.Thread):
    def __init__(self, interval=15):
        super().__init__(daemon=True)
        self.interval = interval
        self.running = True

    def run(self):
        with mss() as sct:
            while self.running:
                sct.shot(mon=-1, output=str(time.time()) + ".png")  # temp
                img = Image.open(sct.shot(mon=-1))
                text = ocr_image(img)
                if text.strip():
                    vec = embed_image(img)
                    table.add([{
                        "timestamp": time.time(),
                        "type": "screen",
                        "content": text[:1000],
                        "embedding": vec
                    }])
                time.sleep(self.interval)

    def stop(self):
        self.running = False
