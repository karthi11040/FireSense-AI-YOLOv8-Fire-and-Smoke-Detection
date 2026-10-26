import unittest
import tempfile
from pathlib import Path
from scripts.adapt_detector import crop_labels, candidate_path


class CropTests(unittest.TestCase):
    def test_rerun_preserves_existing_deployed_checkpoint(self):
        with tempfile.TemporaryDirectory() as folder:
            models=Path(folder)
            existing=models/'yolov8n_domain.pt';existing.write_bytes(b'original')
            target=candidate_path(models,'run2')
            self.assertNotEqual(target,existing)
            target.write_bytes(b'candidate')
            self.assertEqual(existing.read_bytes(),b'original')
            with self.assertRaises(FileExistsError):
                candidate_path(models,'run2')

    def test_crop_preserves_class_and_remaps_coordinates(self):
        labels = [[0, .5, .5, .2, .4], [1, .05, .05, .02, .02]]
        result = crop_labels(labels, (20, 10, 80, 90), (100, 100))
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], 0)
        for actual, expected in zip(result[0][1:], [.5, .5, 1/3, .5]):
            self.assertAlmostEqual(actual, expected)

    def test_partial_box_is_clipped_inside_crop(self):
        result = crop_labels([[1, .5, .5, .8, .8]], (0, 0, 50, 100), (100,100))
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0][1], .6)
        self.assertAlmostEqual(result[0][3], .8)
