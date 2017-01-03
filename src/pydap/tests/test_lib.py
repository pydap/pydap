"""Test the basic DAP functions."""

import numpy as np
from six import MAXSIZE
from pydap.model import (DatasetType, BaseType,
                         StructureType)
from pydap.exceptions import ConstraintExpressionError
from pydap.lib import (quote, encode, fix_slice, combine_slices, hyperslab,
                       walk, fix_shorthand, get_var)
import unittest


class TestQuote(unittest.TestCase):

    """Test quoting.

    According to the DAP 2 specification a variable name MUST contain only
    upper or lower case letters, numbers, or characters from the set

        _ ! ~ * ' - "

    All other characters must be escaped. This includes the period, which is
    normally not quoted by ``urllib.quote``.

    """

    def test_quoting(self):
        """Test a simple quoting."""
        self.assertEqual(quote("White space"), "White%20space")

    def test_quoting_period(self):
        """Test if period is also quoted."""
        self.assertEqual(quote("Period."), "Period%2E")


class TestEncode(unittest.TestCase):

    """Test encoding.

    According to the DAP 2 specification, numbers must be encoded using the C
    notation "%.6g". Other objects are encoded as escaped strings.

    """

    def test_integer(self):
        """Test integer encoding."""
        self.assertEqual(encode(1), "1")

    def test_float(self):
        """Test floating encoding."""
        self.assertEqual(encode(np.pi), "3.14159")

    def test_string(self):
        """Test string encoding."""
        self.assertEqual(encode("test"), '"test"')

    def test_string_with_quotation(self):
        """Test encoding a string with a quotation mark."""
        self.assertEqual(encode('this is a "test"'), '"this is a \"test\""')

    def test_unicode(self):
        """Unicode objects are encoded just like strings."""
        self.assertEqual(encode(u"test"), '"test"')

    def test_obj(self):
        """Other objects are encoded according to their ``repr``."""
        self.assertEqual(encode({}), '"{}"')


class TestFixSlice(unittest.TestCase):

    """Test the ``fix_slice`` function."""

    def test_not_tuple(self):
        """Non tuples should be converted and handled correctly."""
        x = np.arange(10)

        slice1 = 0
        slice2 = fix_slice(slice1, x.shape)

        # ``fix_slice`` will convert to a tuple
        self.assertEqual(slice2, (0,))

        # assert that the slice is equivalent to the original
        np.testing.assert_array_equal(x[slice1], x[slice2])

    def test_ellipsis(self):
        """Expand Ellipsis to occupy the missing dimensions."""
        x = np.arange(6).reshape(2, 3, 1)

        slice1 = Ellipsis, 0
        slice2 = fix_slice(slice1, x.shape)

        # an Ellipsis is expanded to slice(None)
        self.assertEqual(
            slice2,
            ((slice(0, 2, 1), slice(0, 3, 1), 0)))
        np.testing.assert_array_equal(x[slice1], x[slice2])

    def test_negative_int(self):
        """Negative values are converted to positive."""
        x = np.arange(10)

        slice1 = -5
        slice2 = fix_slice(slice1, x.shape)

        self.assertEqual(slice2, (5,))
        np.testing.assert_array_equal(x[slice1], x[slice2])

    def test_negative_start(self):
        """Test for slices with a negative start."""
        x = np.arange(10)

        slice1 = slice(-8, 8)
        slice2 = fix_slice(slice1, x.shape)

        self.assertEqual(slice2, (slice(2, 8, 1),))
        np.testing.assert_array_equal(x[slice1], x[slice2])

    def test_negative_stop(self):
        """Test for slices with a negative stop."""
        x = np.arange(10)

        slice1 = slice(2, -2)
        slice2 = fix_slice(slice1, x.shape)

        self.assertEqual(slice2, (slice(2, 8, 1),))
        np.testing.assert_array_equal(x[slice1], x[slice2])


class TestCombineSlices(unittest.TestCase):

    """Test the ``combine_slices`` function."""

    def test_not_tuple(self):
        """The function fails when one of the slices is not a tuple."""
        slice1 = 0
        slice2 = (0,)
        with self.assertRaises(TypeError):
            combine_slices(slice1, slice2)
        with self.assertRaises(TypeError):
            combine_slices(slice2, slice1)

    def test_integer(self):
        """Test slices that are just integers."""
        slice1 = (0,)
        slice2 = (1,)
        combined = combine_slices(slice1, slice2)
        self.assertEqual(combined, (slice(1, 1, 1),))

    def test_stops_none(self):
        """Test when both of the slices have ``None`` for stop."""
        x = np.arange(10)
        slice1 = (slice(0, None),)
        slice2 = (slice(5, None),)
        combined = combine_slices(slice1, slice2)
        self.assertEqual(combined, (slice(5, None, 1),))
        np.testing.assert_array_equal(x[combined], x[slice1][slice2])

    def test_first_stop_none(self):
        """Test when the first slice has ``None`` for stop."""
        x = np.arange(10)
        slice1 = (slice(5, None),)
        slice2 = (slice(0, 8),)
        combined = combine_slices(slice1, slice2)
        self.assertEqual(combined, (slice(5, 13, 1),))
        np.testing.assert_array_equal(x[combined], x[slice1][slice2])

    def test_second_stop_none(self):
        """Test when the second slice has ``None`` for stop."""
        x = np.arange(10)
        slice1 = (slice(0, 8),)
        slice2 = (slice(5, None),)
        combined = combine_slices(slice1, slice2)
        self.assertEqual(combined, (slice(5, 8, 1),))
        np.testing.assert_array_equal(x[combined], x[slice1][slice2])

    def test_all_values(self):
        """Test when start and stop are all integers."""
        x = np.arange(20)
        slice1 = (slice(0, 8),)
        slice2 = (slice(5, 6),)
        combined = combine_slices(slice1, slice2)
        self.assertEqual(combined, (slice(5, 6, 1),))
        np.testing.assert_array_equal(x[combined], x[slice1][slice2])


class TestHyperslab(unittest.TestCase):

    """Test hyperslab generation from Python slices."""

    def test_no_tuple(self):
        """Test that slices that are not tuples work."""
        slice_ = slice(0)
        self.assertEqual(hyperslab(slice_), "[0:1:%d]" % (MAXSIZE-1))

    def test_remove(self):
        """Test that excess slices are removed."""
        slice_ = (slice(0), slice(None))
        self.assertEqual(hyperslab(slice_), "[0:1:%d]" % (MAXSIZE-1))

    def test_ndimensional(self):
        """Test n-dimensions slices."""
        slice_ = (slice(1, 10, 1), slice(2, 10, 2))
        self.assertEqual(hyperslab(slice_), "[1:1:9][2:2:9]")


class TestWalk(unittest.TestCase):

    """Test the ``walk`` function to iterate over a dataset."""

    def setUp(self):
        """Create a basic dataset."""
        self.dataset = DatasetType("a")
        self.dataset["b"] = BaseType("b")
        self.dataset["c"] = StructureType("c")

    def test_walk(self):
        """Test that all variables are yielded."""
        self.assertEqual(
            list(walk(self.dataset)),
            [self.dataset, self.dataset.b, self.dataset.c])

    def test_walk_type(self):
        """Test the filtering of variables yielded."""
        self.assertEqual(list(walk(self.dataset, BaseType)), [self.dataset.b])


class TestFixShorthand(unittest.TestCase):

    """Test the ``fix_shorthand`` function."""

    def test_fix_projection(self):
        """Test a dataset that can use the shorthand notation."""
        dataset = DatasetType("a")
        dataset["b"] = StructureType("b")
        dataset["b"]["c"] = BaseType("c")

        projection = [[("c", ())]]
        self.assertEqual(
            fix_shorthand(projection, dataset),
            [[('b', ()), ('c', ())]])

    def test_conflict(self):
        """Test a dataset with conflicting short names."""
        dataset = DatasetType("a")
        dataset["b"] = StructureType("b")
        dataset["b"]["c"] = BaseType("c")
        dataset["d"] = StructureType("d")
        dataset["d"]["c"] = BaseType("c")

        projection = [[("c", ())]]
        with self.assertRaises(ConstraintExpressionError):
            fix_shorthand(projection, dataset)


class TestGetVar(unittest.TestCase):

    """Test the ``get_var`` function."""

    def test_get_var(self):
        """Test that the id is returned properly."""
        dataset = DatasetType("a")
        dataset["b"] = StructureType("b")
        dataset["b"]["c"] = BaseType("c")

        self.assertEqual(get_var(dataset, 'b.c'), dataset['b']['c'])
