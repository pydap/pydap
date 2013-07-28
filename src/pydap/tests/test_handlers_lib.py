"""Test basic handler functions."""

import sys
import copy
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

from pkg_resources import EntryPoint
from webtest import TestApp, AppError
import numpy as np

from pydap.model import BaseType, StructureType
from pydap.lib import walk
from pydap.exceptions import ConstraintExpressionError
from pydap.handlers.lib import (
    load_handlers, get_handler, BaseHandler, ExtensionNotSupportedError,
    apply_selection, apply_projection, parse_selection, ConstraintExpression)
from pydap.parsers import parse_projection
from pydap.tests.datasets import (
    SimpleArray, SimpleSequence, SimpleGrid, VerySimpleSequence)


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
        self.assertEqual(res.body, """Dataset {
    Byte byte[byte = 5];
    String string[string = 2];
    Int16 short;
} SimpleArray;
""")
        
        res = self.app.get("/.dds?byte")
        self.assertEqual(res.body, """Dataset {
    Byte byte[byte = 5];
} SimpleArray;
""")

        res = self.app.get("/.das")
        das = res.body
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
        self.assertEqual(res.body, das)

    def test_exception(self):
        """Test exception handling.
        
        By default Pydap will capture all exceptions and return a formatted
        error response.

        """
        with self.assertRaises(AppError):
            res = self.app.get("/.foo")

    def test_exception_non_captured(self):
        """Test exception handling when not captured."""
        app = TestApp(MockHandler(SimpleArray), extra_environ={
            "x-wsgiorg.throw_errors": True})
        with self.assertRaises(KeyError):
            res = app.get("/.foo")

    def test_missing_dataset(self):
        """Test exception when dataset is not set."""
        app = TestApp(MockHandler(), extra_environ={
            "x-wsgiorg.throw_errors": True})
        with self.assertRaises(NotImplementedError):
            res = app.get("/.dds")


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

    def test_simple_projection(self):
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


class TestConstraintExpression(unittest.TestCase):

    """Test the constraint expression object."""

    def test_str(self):
        """Test string representation."""
        ce = ConstraintExpression("a>1")
        self.assertEqual(str(ce), "a>1")

    def test_unicode(self):
        """Test unicode representation."""
        ce = ConstraintExpression("a>1")
        self.assertEqual(unicode(ce), u"a>1")

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
