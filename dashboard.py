"""Local FireSense dashboard. Run: .venv/Scripts/python.exe dashboard.py"""
import argparse
import io
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import time
from urllib.parse import parse_qs, urlsplit
from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parent
MAX_FRAME = 3 * 1024 * 1024


def allowed_request(host, origin, port):
    return host in {f'localhost:{port}', f'127.0.0.1:{port}'} and (
        origin is None or origin == f'http://{host}')


def decode_frame(data):
    if not data or len(data) > MAX_FRAME:
        raise ValueError('Frame must be a JPEG or PNG smaller than 3 MB.')
    try:
        image = Image.open(io.BytesIO(data))
        if image.format not in {'JPEG', 'PNG'} or image.width * image.height > 8_000_000:
            raise ValueError('Use a JPEG/PNG frame no larger than 8 megapixels.')
        return image.convert('RGB')
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError('The image could not be decoded.') from exc


class Detector:
    def __init__(self, device):
        self.state, self.error, self.device = 'loading', '', device
        self.lock = threading.Lock()
        threading.Thread(target=self.load, daemon=True).start()

    def load(self):
        try:
            import torch
            from ultralytics import YOLO
            import numpy as np
            torch.set_num_threads(2)
            self.device = ('0' if torch.cuda.is_available() else 'cpu') if self.device == 'auto' else self.device
            weights = ROOT / 'models/yolov8n_best.pt'
            if not weights.is_file():
                raise FileNotFoundError('models/yolov8n_best.pt is missing. Restore the trained weights first.')
            self.model = YOLO(str(weights))
            self.model.predict(np.zeros((256, 416, 3), dtype=np.uint8),
                               imgsz=416, device=self.device, verbose=False)
            self.state = 'ready'
        except Exception as exc:
            logging.exception('Detector initialization failed')
            self.error = 'Detector could not load. Check weights or restart with --device cpu.'
            self.state = 'error'

    def predict(self, image, confidence):
        if not self.lock.acquire(blocking=False):
            raise BlockingIOError('Detector is busy. Please retry.')
        try:
            start = time.perf_counter()
            result = self.model.predict(image, imgsz=416, conf=confidence, iou=.7,
                                        device=self.device, verbose=False)[0]
            return dict(detections=[dict(label=result.names[int(cls)], confidence=float(score), box=box)
                for cls, score, box in zip(result.boxes.cls.tolist(), result.boxes.conf.tolist(),
                                           result.boxes.xyxyn.tolist())],
                elapsedMs=round((time.perf_counter()-start)*1000, 1))
        finally:
            self.lock.release()


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def reply(self, status, data, kind='application/json'):
        if kind == 'application/json':
            data = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob: data:; media-src 'self' blob:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.send_header('Permissions-Policy', 'camera=(self), microphone=()')
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def trusted(self):
        if not allowed_request(self.headers.get('Host'), self.headers.get('Origin'), self.server.server_port):
            self.reply(403, dict(error='Only same-origin localhost requests are allowed.'))
            return False
        return True

    def do_GET(self):
        if not self.trusted():
            return
        path = urlsplit(self.path).path
        if path == '/api/status':
            detector = self.server.detector
            self.reply(200, dict(state=detector.state, error=detector.error, device=detector.device,
                                 model='YOLOv8 nano', testMap50=82.02))
            return
        files = {'/': ('index.html', 'text/html; charset=utf-8'),
                 '/favicon.svg': ('favicon.svg', 'image/svg+xml'),
                 '/style.css': ('style.css', 'text/css'), '/app.js': ('app.js', 'text/javascript'),
                 '/simulation.mjs': ('simulation.mjs', 'text/javascript'),
                 '/scene.mjs': ('scene.mjs', 'text/javascript'),
                 '/sample-video.webm': ('sample-video.webm', 'video/webm'),
                 '/sample.jpg': ('sample.jpg', 'image/jpeg')}
        if path not in files:
            self.reply(404, dict(error='Not found.'))
            return
        name, kind = files[path]
        try:
            self.reply(200, (ROOT / 'web' / name).read_bytes(), kind)
        except OSError:
            self.reply(404, dict(error='The requested asset is unavailable.'))

    def do_POST(self):
        if not self.trusted():
            return
        if urlsplit(self.path).path != '/api/detections':
            self.reply(404, dict(error='Not found.'))
            return
        if self.headers.get('Content-Type', '').split(';')[0] not in {'image/jpeg', 'image/png'}:
            self.reply(415, dict(error='Send a JPEG or PNG frame.'))
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= MAX_FRAME:
                self.reply(413, dict(error='Frame size must be between 1 byte and 3 MB.'))
                return
            confidence = float(parse_qs(urlsplit(self.path).query).get('confidence', ['.25'])[0])
            if not .05 <= confidence <= .95:
                raise ValueError('Confidence must be between 0.05 and 0.95.')
            image = decode_frame(self.rfile.read(size))
            if self.server.detector.state != 'ready':
                self.reply(503, dict(error=self.server.detector.error or 'Detector is still loading.'))
                return
            self.reply(200, self.server.detector.predict(image, confidence))
        except (ValueError, OverflowError) as exc:
            self.reply(400, dict(error=str(exc)))
        except BlockingIOError as exc:
            self.reply(429, dict(error=str(exc)))
        except TimeoutError:
            self.reply(408, dict(error='The frame transfer timed out.'))
        except Exception:
            logging.exception('Frame inference failed')
            self.reply(500, dict(error='Inference failed. Stop monitoring and retry, or restart with --device cpu.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--device', choices=['auto', 'cpu', '0'], default='auto')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('Port must be between 1 and 65535.')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    server.detector = Detector(args.device)
    print(f'FireSense AI dashboard: http://localhost:{args.port} (model loading in background)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
