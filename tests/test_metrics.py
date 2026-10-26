import unittest
from evaluate import match_predictions, fixed_predictions


class MatchingTests(unittest.TestCase):
    def test_export_category_mapping_and_fixed_threshold(self):
        rows = [dict(image_id='test_1', category_id=2, score=.25, bbox=[10,20,3,4]),
                dict(image_id='test_1', category_id=1, score=.249, bbox=[1,2,3,4])]
        self.assertEqual(fixed_predictions(rows)['test_1'], [[1,.25,10,20,13,24]])
        with self.assertRaises(ValueError):
            fixed_predictions([dict(image_id='x',category_id=0,score=.9,bbox=[0,0,1,1])])

    def test_duplicate_and_wrong_class_are_false_positives(self):
        gt = [[0, 0, 0, 10, 10], [1, 20, 20, 30, 30]]
        pred = [[0, .9, 0, 0, 10, 10], [0, .8, 0, 0, 10, 10],
                [0, .7, 20, 20, 30, 30]]
        self.assertEqual(match_predictions(gt, pred), ([1, 0], [2, 0], [0, 1]))

    def test_empty_images_and_missed_objects(self):
        self.assertEqual(match_predictions([], []), ([0, 0], [0, 0], [0, 0]))
        self.assertEqual(match_predictions([[1, 0, 0, 2, 2]], []),
                         ([0, 0], [0, 0], [0, 1]))
