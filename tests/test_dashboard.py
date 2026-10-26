import io
import unittest
from PIL import Image
from dashboard import decode_frame, allowed_request


class DashboardTests(unittest.TestCase):
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
