"""Test IterData, which makes iterables behave like Numpy structured arrays."""

import numpy as np
from pydap.handlers.lib import IterData

import unittest


@unittest.skip("This test is not fully implemented")
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

        self.simple_object = IterData(("simple", ("byte", "int", "float")),
                                      [(0, 1, 10.),
                                       (1, 2, 20.),
                                       (2, 3, 30.),
                                       (3, 4, 40.),
                                       (4, 5, 50.),
                                       (5, 6, 60.),
                                       (6, 7, 70.),
                                       (7, 8, 80.)])

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


@unittest.skip("This test is not fully implemented")
class TestNestedIterData(unittest.TestCase):

    def setUp(self):
        self.nested_object = IterData(("nested", ("a", "b", "c",
                                                  ("d", ("e", "f", "g")))),
                                      [(1, 1, 1, [(10, 11, 12), (21, 22, 23)]),
                                       (2, 4, 4, [(15, 16, 17)]),
                                       (3, 6, 9, []),
                                       (4, 8, 16,
                                        [(31, 32, 33), (41, 42, 43),
                                         (51, 52, 53), (61, 62, 63)])])

    def test_iter(self):
        self.assertEqual([tuple(row) for row in self.nested_object],
                         [(1, 1, 1, [(10, 11, 12), (21, 22, 23)]),
                          (2, 4, 4, [(15, 16, 17)]),
                          (3, 6, 9, []),
                          (4, 8, 16, [(31, 32, 33), (41, 42, 43),
                                      (51, 52, 53), (61, 62, 63)])])

    def test_iter_child(self):
        self.assertEqual(
            list(self.nested_object["a"]), [1, 2, 3, 4])

    def test_iter_nested_sequence(self):
        self.assertEqual(list(self.nested_object["d"]),
                         [[(10, 11, 12), (21, 22, 23)],
                          [(15, 16, 17)],
                          [],
                          [(31, 32, 33), (41, 42, 43),
                           (51, 52, 53), (61, 62, 63)]])

    def test_iter_nested_deep_child(self):
        print(self.nested_object["d"]["e"].cols)
        self.assertEqual(list(self.nested_object["d"]["e"]),
                         [[(10, 11, 12), (21, 22, 23)],
                          [(15, 16, 17)],
                          [],
                          [(31, 32, 33), (41, 42, 43),
                           (51, 52, 53), (61, 62, 63)]])
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
