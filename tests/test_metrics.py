import unittest
from evaluate import match_predictions


class MatchingTests(unittest.TestCase):
    def test_duplicate_and_wrong_class_are_false_positives(self):
        gt = [[0, 0, 0, 10, 10], [1, 20, 20, 30, 30]]
        pred = [[0, .9, 0, 0, 10, 10], [0, .8, 0, 0, 10, 10],
                [0, .7, 20, 20, 30, 30]]
        self.assertEqual(match_predictions(gt, pred), ([1, 0], [2, 0], [0, 1]))

    def test_empty_images_and_missed_objects(self):
        self.assertEqual(match_predictions([], []), ([0, 0], [0, 0], [0, 0]))
        self.assertEqual(match_predictions([[1, 0, 0, 2, 2]], []),
                         ([0, 0], [0, 0], [0, 1]))
