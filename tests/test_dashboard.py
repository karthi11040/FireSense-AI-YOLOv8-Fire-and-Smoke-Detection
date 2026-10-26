import io
import unittest
import json
from pathlib import Path
import tempfile
from PIL import Image
from dashboard import decode_frame, allowed_request, deployment_profile


class DashboardTests(unittest.TestCase):
    def test_deployment_keeps_original_default_and_rejects_unknown_weights(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'selection.json'
            self.assertEqual(deployment_profile(path)['weights'], 'models/yolov8n_best.pt')
            path.write_text(json.dumps(dict(weights='../unknown.pt', imgsz=416)))
            with self.assertRaises(ValueError):
                deployment_profile(path)
            path.write_text(json.dumps(dict(weights='models/yolov8n_refined.pt',
                imgsz=416, model='YOLOv8 nano (refined)', testMap50=82.62)))
            self.assertEqual(deployment_profile(path)['testMap50'], 82.62)
            path.write_text(json.dumps(dict(weights='models/yolov8n_domain.pt',
                imgsz=416, model='YOLOv8 nano (domain adapted)', testMap50=None)))
            self.assertEqual(deployment_profile(path)['weights'], 'models/yolov8n_domain.pt')

    def test_accepts_image_and_rejects_invalid_input(self):
        out = io.BytesIO()
        Image.new('RGB', (64, 32)).save(out, format='JPEG')
        self.assertEqual(decode_frame(out.getvalue()).size, (64, 32))
        with self.assertRaises(ValueError):
            decode_frame(b'not an image')
        with self.assertRaises(ValueError):
            decode_frame(b'x' * (3 * 1024 * 1024 + 1))

    def test_blocks_foreign_hosts_and_origins(self):
        self.assertTrue(allowed_request('localhost:8765', 'http://localhost:8765', 8765))
        self.assertTrue(allowed_request('127.0.0.1:8765', None, 8765))
        self.assertFalse(allowed_request('evil.example:8765', None, 8765))
        self.assertFalse(allowed_request('localhost:8765', 'https://evil.example', 8765))
