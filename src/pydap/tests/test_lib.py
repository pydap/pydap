import unittest

import numpy as np

from pydap.model import *
from pydap.exceptions import ConstraintExpressionError
from pydap.lib import (quote, encode, fix_slice, combine_slices, hyperslab,
        walk, fix_shorthand, get_var)


class TestQuote(unittest.TestCase):
    """
    According to the DAP 2 specification a variable name MUST contain only 
    upper or lower case letters, numbers, or characters from the set

        _ ! ~ * ' - "

    All other characters must be escaped. This includes the period, which is    
    normally not quoted by `urllib.quote`.

    """
    def test_quoting(self):
        self.assertEqual(quote("White space"), "White%20space")

    def test_quoting_period(self):
        self.assertEqual(quote("Period."), "Period%2E")


class TestEncode(unittest.TestCase):
    """
    According to the DAP 2 specification, numbers must be encoded using the C
    notation "%.6g". Other objects are encoded as escaped strings.

    """
    def test_integer(self):
        self.assertEqual(encode(1), "1")

    def test_float(self):
        self.assertEqual(encode(np.pi), "3.14159")

    def test_string(self):
        self.assertEqual(encode("test"), '"test"')

    def test_unicode(self):
        self.assertEqual(encode(u"test"), '"test"')

    def test_obj(self):
        self.assertEqual(encode({}), '"{}"')


class TestFixSlice(unittest.TestCase):
    def test_not_tuple(self):
        x = np.arange(10)

        slice1 = 0
        slice2 = fix_slice(slice1, x.shape)

        # `fix_slice` will convert to a tuple
        self.assertEqual(slice2, (0,))

        # assert that the slice is equivalent to the original
        np.testing.assert_array_equal(x[slice1], x[slice2])

    def test_ellipsis(self):
        x = np.arange(6).reshape(2, 3, 1)

        slice1 = Ellipsis, 0
        slice2 = fix_slice(slice1, x.shape)

        # an Ellipsis is expanded to slice(None)
        self.assertEqual(slice2, 
                ((slice(None, None, 1), slice(None, None, 1), 0)))
        np.testing.assert_array_equal(x[slice1], x[slice2])

    def test_negative_int(self):
        x = np.arange(10)

        slice1 = -5
        slice2 = fix_slice(slice1, x.shape)

        self.assertEqual(slice2, (5,))
        np.testing.assert_array_equal(x[slice1], x[slice2])

    def test_negative_start(self):
        x = np.arange(10)

        slice1 = slice(-8, 8)
        slice2 = fix_slice(slice1, x.shape)

        self.assertEqual(slice2, (slice(2, 8, 1),))
        np.testing.assert_array_equal(x[slice1], x[slice2])

    def test_negative_stop(self):
        x = np.arange(10)

        slice1 = slice(2, -2)
        slice2 = fix_slice(slice1, x.shape)

        self.assertEqual(slice2, (slice(2, 8, 1),))
        np.testing.assert_array_equal(x[slice1], x[slice2])


class TestCombineSlices(unittest.TestCase):
    def test_integer(self):
        x = np.arange(10)
        slice1 = (0,)
        slice2 = (1,)
        combined = combine_slices(slice1, slice2)
        self.assertEqual(combined, (slice(1, 1, 1),))

    def test_stops_none(self):
        x = np.arange(10)
        slice1 = (slice(0, None),)
        slice2 = (slice(5, None),)
        combined = combine_slices(slice1, slice2)
        self.assertEqual(combined, (slice(5, None, 1),))
        np.testing.assert_array_equal(x[combined], x[slice1][slice2])

    def test_first_stop_none(self):
        x = np.arange(10)
        slice1 = (slice(5, None),)
        slice2 = (slice(0, 8),)
        combined = combine_slices(slice1, slice2)
        self.assertEqual(combined, (slice(5, 13, 1),))
        np.testing.assert_array_equal(x[combined], x[slice1][slice2])

    def test_second_stop_none(self):
        x = np.arange(10)
        slice1 = (slice(0, 8),)
        slice2 = (slice(5, None),)
        combined = combine_slices(slice1, slice2)
        self.assertEqual(combined, (slice(5, 8, 1),))
        np.testing.assert_array_equal(x[combined], x[slice1][slice2])

    def test_all_values(self):
        x = np.arange(20)
        slice1 = (slice(0, 8),)
        slice2 = (slice(5, 10),)
        combined = combine_slices(slice1, slice2)
        self.assertEqual(combined, (slice(5, 8, 1),))
        np.testing.assert_array_equal(x[combined], x[slice1][slice2])


class TestHyperslab(unittest.TestCase):
    def test_no_tuple(self):
        slice_ = slice(0)
        self.assertEqual(hyperslab(slice_), "[0:1:9223372036854775806]")

    def test_remove(self):
        slice_ = (slice(0), slice(None))
        self.assertEqual(hyperslab(slice_), "[0:1:9223372036854775806]")

    def test_ndimensional(self):
        slice_ = (slice(1, 10, 1), slice(2, 10, 2))
        self.assertEqual(hyperslab(slice_), "[1:1:9][2:2:9]")


class TestWalk(unittest.TestCase):
    def setUp(self):
        self.dataset = DatasetType("a")
        self.dataset["b"] = BaseType("b")
        self.dataset["c"] = StructureType("c")

    def test_walk(self):
        self.assertEqual(list(walk(self.dataset)),
                [self.dataset, self.dataset.b, self.dataset.c])

    def test_walk_type(self):
        self.assertEqual(list(walk(self.dataset, BaseType)), [self.dataset.b])


class TestFixShorthand(unittest.TestCase):
    def test_fix_projection(self):
        dataset = DatasetType("a")
        dataset["b"] = StructureType("b")
        dataset["b"]["c"] = BaseType("c")

        projection = [[("c", ())]]
        self.assertEqual(fix_shorthand(projection, dataset),
                [[('b', ()), ('c', ())]])

    def test_conflict(self):
        dataset = DatasetType("a")
        dataset["b"] = StructureType("b")
        dataset["b"]["c"] = BaseType("c")
        dataset["d"] = StructureType("d")
        dataset["d"]["c"] = BaseType("c")

        projection = [[("c", ())]]
        with self.assertRaises(ConstraintExpressionError):
            fix_shorthand(projection, dataset)


class TestGetVar(unittest.TestCase):
    def test_get_var(self):
        dataset = DatasetType("a")
        dataset["b"] = StructureType("b")
        dataset["b"]["c"] = BaseType("c")

        self.assertEqual(get_var(dataset, 'b.c'), dataset['b']['c'])
