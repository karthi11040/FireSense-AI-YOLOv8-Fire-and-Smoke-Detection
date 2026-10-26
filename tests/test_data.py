import unittest
from pipeline import parse_label, unique_records


class DatasetTests(unittest.TestCase):
    def test_valid_and_negative_labels(self):
        self.assertEqual(parse_label(''), [])
        self.assertEqual(parse_label('1 0.5 0.5 0.2 0.4'), [[1, .5, .5, .2, .4]])

    def test_rejects_bad_annotations(self):
        for row in ['2 .5 .5 .1 .1', '0 nan .5 .1 .1', '0 .5 .5 0 .1',
                    '0 .5 .5 2 .1', '0 .5 .5 .2', '0 .99 .5 .2 .1']:
            with self.subTest(row=row), self.assertRaises(ValueError):
                parse_label(row)

    def test_test_set_wins_duplicate_conflict(self):
        rows = [dict(split='train', hash='a'), dict(split='test', hash='a'),
                dict(split='val', hash='b'), dict(split='train', hash='c')]
        kept, removed = unique_records(rows)
        self.assertEqual({(r['split'], r['hash']) for r in kept},
                         {('test', 'a'), ('val', 'b'), ('train', 'c')})
        self.assertEqual(len(removed), 1)


if __name__ == '__main__':
    unittest.main()
