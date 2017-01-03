"""Test basic handler functions."""

import copy
from six import text_type

from webtest import TestApp, AppError
import numpy as np

from pydap.model import BaseType, StructureType, SequenceType
from pydap.lib import walk
from pydap.exceptions import ConstraintExpressionError
from pydap.handlers.lib import (
    load_handlers, get_handler, BaseHandler, ExtensionNotSupportedError,
    apply_selection, apply_projection, ConstraintExpression,
    IterData)
from pydap.parsers import parse_projection
from pydap.tests.datasets import (
    SimpleArray, SimpleSequence, SimpleGrid, VerySimpleSequence,
    NestedSequence, SimpleStructure)
import unittest


class TestHandlersLib(unittest.TestCase):

    """Test handler loading."""

    def test_load_handlers(self):
        """Test that handlers can be loaded correctly.

        We use a mock working set, since by default no handlers are installed
        with Pydap.

        """
        handlers = load_handlers(MockWorkingSet())
        self.assertTrue(MockHandler in handlers)

    def test_get_handler(self):
        """Test that we can load a specific handler."""
        handlers = load_handlers(MockWorkingSet())
        handler = get_handler("file.foo", handlers)
        self.assertIsInstance(handler, MockHandler)

    def test_no_handler_available(self):
        """Test exception raised when file not supported."""
        with self.assertRaises(ExtensionNotSupportedError):
            get_handler("file.bar")


class TestBaseHandler(unittest.TestCase):

    """Test the base handler as a WSGI app."""

    def setUp(self):
        """Create a basic WSGI app."""
        self.app = TestApp(MockHandler(SimpleArray))

    def test_unconstrained_das(self):
        """DAS responses are always unconstrained."""
        res = self.app.get("/.dds")
        self.assertEqual(res.text, """Dataset {
    Byte byte[byte = 5];
    String string[string = 2];
    Int16 short;
} SimpleArray;
""")

        res = self.app.get("/.dds?byte")
        self.assertEqual(res.text, """Dataset {
    Byte byte[byte = 5];
} SimpleArray;
""")

        res = self.app.get("/.das")
        das = res.text
        self.assertEqual(das, """Attributes {
    byte {
    }
    string {
    }
    short {
    }
}
""")

        # check that DAS is unmodifed with constraint expression
        res = self.app.get("/.das?byte")
        self.assertEqual(res.text, das)

    def test_exception(self):
        """
        Test exception handling.

        By default Pydap will capture all exceptions and return a formatted
        error response.

        """
        with self.assertRaises(AppError):
            self.app.get("/.foo")

    def test_exception_non_captured(self):
        """Test exception handling when not captured."""
        app = TestApp(MockHandler(SimpleArray), extra_environ={
            "x-wsgiorg.throw_errors": True})
        with self.assertRaises(KeyError):
            app.get("/.foo")

    def test_missing_dataset(self):
        """Test exception when dataset is not set."""
        app = TestApp(MockHandler(), extra_environ={
            "x-wsgiorg.throw_errors": True})
        with self.assertRaises(NotImplementedError):
            app.get("/.dds")


class TestApplySelection(unittest.TestCase):

    """Test function that applies selections to the dataset."""

    def setUp(self):
        """Build our own sequence.

        Pydap uses lightweight copies of objects that share data. This breaks
        unit tests since the same objects are reused for tests.

        """
        # make a dataset with its own data
        self.dataset = copy.copy(SimpleSequence)
        self.dataset.cast.data = SimpleSequence.cast.data.copy()

    def test_no_selection(self):
        """Test no selection in the query string."""
        dataset = apply_selection("", self.dataset)
        np.testing.assert_array_equal(
            dataset.cast.data, self.dataset.cast.data)

    def test_simple_selection(self):
        """Test a simple selection applied to the dataset."""
        dataset = apply_selection(["cast.lon=100"], self.dataset)
        np.testing.assert_array_equal(
            dataset.cast.data,
            self.dataset.cast.data[self.dataset.cast.data["lon"] == 100])

    def test_multiple_selections(self):
        """Test multiple selections applied to dataset."""
        dataset = apply_selection(
            ["cast.lon=100", "cast.lat>0"], self.dataset)
        np.testing.assert_array_equal(
            dataset.cast.data,
            self.dataset.cast.data[
                self.dataset.cast.data["lon"] == 100
            ][
                self.dataset.cast.data["lat"] > 0
            ])


class TestApplyProjectionGrid(unittest.TestCase):

    """Test applying projections on a dataset with a grid."""

    def setUp(self):
        """Build dataset with no shared data."""
        self.dataset = copy.copy(SimpleGrid)
        for var in walk(self.dataset, BaseType):
            var.data = var.data.copy()

    def test_no_projection(self):
        """Test no projections."""
        dataset = apply_projection("", self.dataset)
        self.assertEqual(list(dataset.children()), [])

    def test_simple_projection(self):
        """Test simple projections."""
        dataset = apply_projection(parse_projection("x"), self.dataset)
        self.assertEqual(dataset.keys(), ["x"])

    def test_simple_projection_with_index(self):
        """Test simple projections."""
        dataset = apply_projection(parse_projection("x[1]"), self.dataset)
        np.testing.assert_array_equal(
            dataset.x.data, [1])

    def test_array(self):
        """Test that the grid degenerates into a structure."""
        dataset = apply_projection(
            parse_projection("SimpleGrid.SimpleGrid"), self.dataset)
        self.assertIsInstance(dataset.SimpleGrid, StructureType)

    def test_array_slice(self):
        """Test slices applied to a grid."""
        dataset = apply_projection(
            parse_projection("SimpleGrid[1]"), self.dataset)
        np.testing.assert_array_equal(
            dataset.SimpleGrid.x.data, self.dataset.SimpleGrid[1].x.data)
        np.testing.assert_array_equal(
            dataset.SimpleGrid.y.data, self.dataset.SimpleGrid[1].y.data)
        np.testing.assert_array_equal(
            dataset.SimpleGrid.SimpleGrid.data,
            self.dataset.SimpleGrid[1:2].SimpleGrid.data)


class TestApplyProjectionSequence(unittest.TestCase):

    """Test applying projections on a dataset with a sequence."""

    def setUp(self):
        """Build dataset with no shared data."""
        self.dataset = copy.copy(VerySimpleSequence)
        self.dataset.sequence.data = VerySimpleSequence.sequence.data.copy()

    def test_sequence_projection(self):
        """Test projection slicing on sequences."""
        dataset = apply_projection(
            parse_projection("sequence[2]"), self.dataset)
        np.testing.assert_array_equal(
            dataset.sequence.data, VerySimpleSequence.sequence.data[2])


class TestInvalidProjection(unittest.TestCase):

    """Test applying a projection to a structure object."""

    def test_structure_projection(self):
        """Test projection slicing on a structure."""
        with self.assertRaises(ConstraintExpressionError):
            apply_projection(parse_projection("types[0]"), SimpleStructure)


class TestConstraintExpression(unittest.TestCase):

    """Test the constraint expression object."""

    def test_str(self):
        """Test string representation."""
        ce = ConstraintExpression("a>1")
        self.assertEqual(str(ce), "a>1")

    def test_unicode(self):
        """Test unicode representation."""
        ce = ConstraintExpression("a>1")
        self.assertEqual(text_type(ce), "a>1")

    def test_and(self):
        """Test CE addition."""
        ce1 = ConstraintExpression("a>1")
        ce2 = ConstraintExpression("b>0")
        ce3 = ce1 & ce2
        self.assertEqual(str(ce3), "a>1&b>0")

    def test_or(self):
        """Expressions cannot be ORed."""
        ce1 = ConstraintExpression("a>1")
        ce2 = ConstraintExpression("b>0")
        with self.assertRaises(ConstraintExpressionError):
            ce1 | ce2


class TestIterData(unittest.TestCase):
    """
    Test the ``IterData`` class, used to store flat/nested sequence data.

    A flat ``IterData`` should behave like a Numpy structured array, except
    all operations are stored to be lazily evaluated when the object is
    iterated over.

    """

    def setUp(self):
        """Create a flat IterData."""
        template = SequenceType("a")
        template["b"] = BaseType("b")
        template["c"] = BaseType("c")
        template["d"] = BaseType("d")
        self.data = IterData([(1, 2, 3), (4, 5, 6)], template)

        self.array = np.array(np.rec.fromrecords([
            (1, 2, 3),
            (4, 5, 6),
        ], names=["b", "c", "d"]))

    def assertIteratorEqual(self, it1, it2):
        self.assertEqual(list(it1), list(it2))

    def test_repr(self):
        """Test the object representation."""
        self.assertEqual(
            repr(self.data),
            "<IterData to stream [(1, 2, 3), (4, 5, 6)]>")

    def test_dtype(self):
        """Test the ``dtype`` property."""
        self.assertEqual(self.data["b"].dtype, self.array["b"].dtype)

    def test_iteration(self):
        """Test iteration over data."""
        self.assertIteratorEqual(map(tuple, self.data), map(tuple, self.array))
        self.assertIteratorEqual(self.data["b"], self.array["b"])

    def test_filter(self):
        """Test filtering the object."""
        self.assertIteratorEqual(
            map(tuple, self.data[self.data["b"] == 1]),
            map(tuple, self.array[self.array["b"] == 1]))
        self.assertIteratorEqual(
            map(tuple, self.data[self.data["b"] != 1]),
            map(tuple, self.array[self.array["b"] != 1]))
        self.assertIteratorEqual(
            map(tuple, self.data[self.data["b"] >= 1]),
            map(tuple, self.array[self.array["b"] >= 1]))
        self.assertIteratorEqual(
            map(tuple, self.data[self.data["b"] <= 1]),
            map(tuple, self.array[self.array["b"] <= 1]))
        self.assertIteratorEqual(
            map(tuple, self.data[self.data["b"] > 1]),
            map(tuple, self.array[self.array["b"] > 1]))
        self.assertIteratorEqual(
            map(tuple, self.data[self.data["b"] < 1]),
            map(tuple, self.array[self.array["b"] < 1]))

    def test_slice(self):
        """Test slicing the object."""
        self.assertIteratorEqual(map(tuple, self.data[1:]),
                                 map(tuple, self.array[1:]))

    def test_integer_slice(self):
        """Test slicing with an integer.

        Note that the behavior here is different from Numpy arrays, since the
        data access to ``IterData`` is through iteration it has no direct index
        access.

        """
        self.assertIteratorEqual(self.data[0:1], self.array[0:1].tolist())
        self.assertIteratorEqual(self.data[0], self.array[0:1].tolist())

    def test_invalid_child(self):
        """Test accessing a non-existing child."""
        with self.assertRaises(KeyError):
            self.data["e"]

    def test_invalid_key(self):
        """Test accessing using an invalid key."""
        with self.assertRaises(KeyError):
            self.data[(1, 2)]

    def test_selecting_children(self):
        """Test that we can select children."""
        self.assertIteratorEqual(
            map(tuple, self.data[["d", "b"]]),
            map(tuple, self.array[["d", "b"]]))

    def test_invalid_selection(self):
        """Test invalid selections.

        In theory this should never happen, since ``ConstraintExpression``
        object are constructly directly from existing children.

        """
        with self.assertRaises(ConstraintExpressionError):
            self.data[ConstraintExpression("a.e<1")]
        with self.assertRaises(ConstraintExpressionError):
            self.data[ConstraintExpression("a.d<foo")]

    def test_intercomparison_selection(self):
        """Test comparing children in the selection."""
        self.assertIteratorEqual(
            map(tuple, self.data[self.data["b"] == self.data["c"]]),
            map(tuple, self.array[self.array["b"] == self.array["c"]]))
        self.assertIteratorEqual(
            map(tuple, self.data[self.data["b"] != self.data["c"]]),
            map(tuple, self.array[self.array["b"] != self.array["c"]]))
        self.assertIteratorEqual(
            map(tuple, self.data[self.data["b"] >= self.data["c"]]),
            map(tuple, self.array[self.array["b"] >= self.array["c"]]))
        self.assertIteratorEqual(
            map(tuple, self.data[self.data["b"] <= self.data["c"]]),
            map(tuple, self.array[self.array["b"] <= self.array["c"]]))
        self.assertIteratorEqual(
            map(tuple, self.data[self.data["b"] > self.data["c"]]),
            map(tuple, self.array[self.array["b"] > self.array["c"]]))
        self.assertIteratorEqual(
            map(tuple, self.data[self.data["b"] < self.data["c"]]),
            map(tuple, self.array[self.array["b"] < self.array["c"]]))

    def test_selection_not_in_projection(self):
        """Test selection with variables that are not in the projection."""
        self.data[["d", "b"]]
        filtered = self.data[["d", "b"]][self.data["c"] > 3]
        self.assertEqual(filtered, self.array[["d", "b"]][self.array["c"] > 3])


class TestRegexp(unittest.TestCase):

    """Test regular expression match."""

    def test_regexp(self):
        sequence = SequenceType("sequence")
        sequence["name"] = BaseType("name")
        sequence.data = IterData([
            ("John", "Paul", "George", "Ringo"),
        ], sequence)

        filtered = sequence[ConstraintExpression('sequence.name=~"J.*"')]
        self.assertEqual(list(filtered), [("John",)])


class TestNestedIterData(unittest.TestCase):

    """Test ``IterData`` with nested data."""

    def setUp(self):
        """Load data from test dataset."""
        self.data = NestedSequence.location.data

    def test_iteration(self):
        """Test basic iteration."""
        self.assertEqual(list(self.data),
                         [(1, 1, 1, [(10, 11, 12), (21, 22, 23)]),
                          (2, 4, 4, [(15, 16, 17)]),
                          (3, 6, 9, []),
                          (4, 8, 16, [(31, 32, 33), (41, 42, 43),
                                      (51, 52, 53), (61, 62, 63)])])

    def test_children_data(self):
        """Test getting data from a simple child."""
        self.assertEqual(list(self.data["lat"]), [1, 2, 3, 4])

    def test_sequence_children_data(self):
        """Test getting data from a sequence child."""
        self.assertEqual(list(self.data["time_series"]),
                         [[(10, 11, 12), (21, 22, 23)],
                          [(15, 16, 17)],
                          [],
                          [(31, 32, 33), (41, 42, 43),
                           (51, 52, 53), (61, 62, 63)]])

    def test_deep_children_data(self):
        """Test getting data from a sequence child."""
        self.assertEqual(list(self.data["time_series"]["time"]),
                         [[10, 21], [15], [], [31, 41, 51, 61]])

    def test_selecting_children(self):
        """Test that we can select children."""
        self.assertEqual(list(self.data[["time_series", "elev"]]),
                         [([(10, 11, 12), (21, 22, 23)], 1),
                          ([(15, 16, 17)], 4),
                          ([], 9),
                          ([(31, 32, 33), (41, 42, 43),
                            (51, 52, 53), (61, 62, 63)], 16)])

    def test_slice(self):
        """Test slicing the object."""
        self.assertEqual(list(self.data[1::2]),
                         [(2, 4, 4, [(15, 16, 17)]),
                          (4, 8, 16, [(31, 32, 33), (41, 42, 43),
                                      (51, 52, 53), (61, 62, 63)])])

    def test_children_data_from_slice(self):
        """Test getting children data from a sliced sequence."""
        self.assertEqual(list(self.data[1::2]["lat"]), [2, 4])

    def test_sequence_children_data_from_slice(self):
        """Test getting children data from a sliced sequence."""
        self.assertEqual(list(self.data[1::2]["time_series"]),
                         [[(15, 16, 17)], [(31, 32, 33), (41, 42, 43),
                                           (51, 52, 53), (61, 62, 63)]])

    def test_deep_slice(self):
        """Test slicing the inner sequence."""
        self.assertEqual(list(self.data["time_series"][::2]),
                         [[(10, 11, 12), (21, 22, 23)], []])

    def test_integer_slice(self):
        """Test slicing with an integer."""
        self.assertEqual(list(self.data["time_series"][1]), [[(15, 16, 17)]])

    def test_filter_data(self):
        """Test filtering the data."""
        self.assertEqual(list(self.data[self.data["lat"] > 2]),
                         [(3, 6, 9, []), (4, 8, 16,
                                          [(31, 32, 33), (41, 42, 43),
                                           (51, 52, 53), (61, 62, 63)])])

    def test_deep_filter(self):
        """Test deep filtering the data."""
        self.assertEqual(list(self.data[self.data["time_series"]["slp"] > 11]),
                         [(1, 1, 1, [(21, 22, 23)]),
                          (2, 4, 4, [(15, 16, 17)]),
                          (3, 6, 9, []),
                          (4, 8, 16, [(31, 32, 33), (41, 42, 43),
                                      (51, 52, 53), (61, 62, 63)])])


class MockWorkingSet(object):

    """A fake working set for testing handlers."""

    def iter_entry_points(self, group):
        """Return a mock entry point."""
        yield MockEntryPoint(MockHandler)


class MockHandler(BaseHandler):

    """A fake handler for testing."""

    extensions = "^.*\.foo$"

    def __init__(self, dataset=None):
        BaseHandler.__init__(self, dataset)
        self.additional_headers = [
            ("X-debug", "True")
        ]


class MockEntryPoint(object):

    """A fake entry point for testing."""

    def __init__(self, handler):
        self.handler = handler

    def load(self):
        """Return the wrapped handler."""
        return self.handler
