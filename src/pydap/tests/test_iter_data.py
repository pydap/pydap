"""Test IterData, which makes iterables behave like Numpy structured arrays."""

import numpy as np
from pydap.handlers.lib import IterData
from pydap.model import DatasetType, SequenceType, BaseType

import unittest


class TestSimpleIterData(unittest.TestCase):

    """Compare IterData object with corresponding Numpy array."""

    def setUp(self):
        self.simple_array = np.array([
            (0, 1, 10.),
            (1, 2, 20.),
            (2, 3, 30.),
            (3, 4, 40.),
            (4, 5, 50.),
            (5, 6, 60.),
            (6, 7, 70.),
            (7, 8, 80.),
        ], dtype=[('byte', 'b'), ('int', 'i4'), ('float', 'f4')])
        # add sequence and children for each column
        name = 'nameless'
        self.dataset = DatasetType(name)
        seq = self.dataset['sequence'] = SequenceType('sequence')
        for var in self.simple_array.dtype.names:
            seq[var] = BaseType(var)

        self.simple_object = IterData([(0, 1, 10.),
                                       (1, 2, 20.),
                                       (2, 3, 30.),
                                       (3, 4, 40.),
                                       (4, 5, 50.),
                                       (5, 6, 60.),
                                       (6, 7, 70.),
                                       (7, 8, 80.)],
                                      seq)

    def test_iter(self):
        self.assertEqual([tuple(row)
                          for row in self.simple_array],
                         [(0, 1, 10.),
                          (1, 2, 20.),
                          (2, 3, 30.),
                          (3, 4, 40.),
                          (4, 5, 50.),
                          (5, 6, 60.),
                          (6, 7, 70.),
                          (7, 8, 80.)])
        self.assertEqual(
            list(self.simple_array["byte"]), [0, 1, 2, 3, 4, 5, 6, 7])

        self.assertEqual([tuple(row) for row in self.simple_object],
                         [(0, 1, 10.),
                          (1, 2, 20.),
                          (2, 3, 30.),
                          (3, 4, 40.),
                          (4, 5, 50.),
                          (5, 6, 60.),
                          (6, 7, 70.),
                          (7, 8, 80.)])
        self.assertEqual(
            list(self.simple_object["byte"]), [0, 1, 2, 3, 4, 5, 6, 7])

    def test_dtype(self):
        self.assertEqual(
            self.simple_array.dtype,
            np.dtype([('byte', 'i1'), ('int', '<i4'), ('float', '<f4')]))
        self.assertEqual(self.simple_array["int"].dtype, "<i4")

        self.assertEqual(
            self.simple_object.dtype,
            np.dtype([('byte', '<i8'), ('int', '<i8'), ('float', '<f8')]))
        self.assertEqual(self.simple_object["int"].dtype, "<i8")

    def test_selection(self):
        selection = self.simple_array[self.simple_array["byte"] > 3]
        self.assertEqual([tuple(row) for row in selection],
                         [(4, 5, 50.),
                          (5, 6, 60.),
                          (6, 7, 70.),
                          (7, 8, 80.)])

        selection = self.simple_object[self.simple_object["byte"] > 3]
        self.assertEqual([tuple(row) for row in selection],
                         [(4, 5, 50.),
                          (5, 6, 60.),
                          (6, 7, 70.),
                          (7, 8, 80.)])

    def test_projection(self):
        projection = self.simple_array[1::2]
        self.assertEqual([tuple(row) for row in projection],
                         [(1, 2, 20.),
                          (3, 4, 40.),
                          (5, 6, 60.),
                          (7, 8, 80.)])
        self.assertEqual(
            list(self.simple_array["byte"][1::2]), [1, 3, 5, 7])
        self.assertEqual(
            list(self.simple_array[1::2]["byte"]), [1, 3, 5, 7])

        projection = self.simple_object[1::2]
        self.assertEqual([tuple(row) for row in projection],
                         [(1, 2, 20.),
                          (3, 4, 40.),
                          (5, 6, 60.),
                          (7, 8, 80.)])
        self.assertEqual(
            list(self.simple_object["byte"][1::2]), [1, 3, 5, 7])
        self.assertEqual(
            list(self.simple_object[1::2]["byte"]), [1, 3, 5, 7])

    def test_combined(self):
        filtered = self.simple_array[self.simple_array["byte"] > 1]
        filtered = filtered[filtered["byte"] < 6]
        filtered = filtered[::2]
        self.assertEqual([tuple(row) for row in filtered],
                         [(2, 3, 30.),
                          (4, 5, 50.)])

        filtered = self.simple_object[self.simple_object["byte"] > 1]
        filtered = filtered[filtered["byte"] < 6]
        filtered = filtered[::2]
        self.assertEqual([tuple(row) for row in filtered],
                         [(2, 3, 30.),
                          (4, 5, 50.)])


class TestNestedIterData(unittest.TestCase):

    def setUp(self):
        self.shallow_data = [(1, 1, 1), (2, 4, 4),
                             (3, 6, 9), (4, 8, 16)]
        self.deep_data = [[(10, 11, 12), (21, 22, 23)],
                          [(15, 16, 17)],
                          [],
                          [(31, 32, 33), (41, 42, 43),
                           (51, 52, 53), (61, 62, 63)]]
        self.nested_data = [x + (self.deep_data[x_id],)
                            for x_id, x
                            in enumerate(self.shallow_data)]

        self.dtype = np.dtype([('a', '<i8'), ('b', '<i8'),
                               ('c', '<i8'),
                               ('d', np.dtype([('e', '<i8'),
                                               ('f', '<i8'),
                                               ('g', '<i8')]))])
        name = 'nameless'
        self.dataset = DatasetType(name)
        seq = self.dataset['nested'] = SequenceType('nested')
        for var in ['a', 'b', 'c']:
            seq[var] = BaseType(var)
        seq['d'] = SequenceType('d')
        for var in ['e', 'f', 'g']:
            seq['d'][var] = BaseType(var)

        self.nested_object = IterData(self.nested_data, seq)

    def test_iter(self):
        self.assertEqual([tuple(row) for row in self.nested_object],
                         self.nested_data)

    def test_iter_child(self):
        self.assertEqual(
            list(self.nested_object["a"]),
            [row[0] for row in self.nested_data])

    def test_iter_nested_sequence(self):
        self.assertEqual(list(self.nested_object["d"]),
                         [row[3] for row in self.nested_data])

    def test_iter_nested_deep_child(self):
        self.assertEqual(list(self.nested_object['d']['e']),
                         [[col[0] for col in row[3]]
                          for row in self.nested_data])

    def test_dtype(self):
        self.assertEqual(
            self.nested_object.dtype,
            self.dtype)

    def test_selection(self):
        selection = self.nested_object[self.nested_object["a"] > 2]
        self.assertEqual([tuple(row) for row in selection],
                         [tuple(row) for row in self.nested_data
                          if row[0] > 2])

    def test_projection(self):
        projection = self.nested_data[1::2]
        self.assertEqual([tuple(row) for row in projection],
                         [tuple(row) for row_id, row
                          in enumerate(self.nested_data)
                          if row_id in range(1, len(self.nested_data), 2)])

        projection = self.nested_object[1::2]
        self.assertEqual([tuple(row) for row in projection],
                         [tuple(row) for row_id, row
                          in enumerate(self.nested_data)
                          if row_id in range(1, len(self.nested_data), 2)])

    def test_combined(self):
        filtered = [tuple(row) for row in self.nested_data
                    if row[0] > 2]
        filtered = [tuple(row) for row in filtered
                    if row[0] < 4]
        filtered = filtered[::2]
        self.assertEqual([tuple(row) for row in filtered],
                         [(3, 6, 9, [])])

        filtered = self.nested_object[self.nested_object["a"] > 2]
        filtered = filtered[filtered["a"] < 4]
        filtered = filtered[::2]
        self.assertEqual([tuple(row) for row in filtered],
                         [(3, 6, 9, [])])
