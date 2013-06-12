"""Test the data model."""

import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

import numpy as np

from pydap.model import DapType
from pydap.model import *


class TestDapType(unittest.TestCase):

    """Test the super class for Pydap types."""

    def test_quote(self):
        """Test that names are properly quoted."""
        var = DapType("foo.bar[0]")
        self.assertEqual(var.name, "foo%2Ebar%5B0%5D")

    def test_attributes(self):
        """Test attribute assignment.
        
        Note that ``**kwargs`` have precedence.

        """
        attributes = {"foo": "bar", "value": 43}
        var = DapType("var", attributes=attributes, value=42)
        self.assertEqual(var.attributes, {"foo": "bar", "value": 42})

    def test_id(self):
        """Test id assignment."""
        var = DapType("var")
        self.assertEqual(var._id, "var")
        self.assertEqual(var.id, "var")

    def test_repr(self):
        """Test the ``__repr__`` method."""
        var = DapType("var", foo="bar", value=42)
        self.assertEqual(repr(var),
                "DapType('var', {'foo': 'bar', 'value': 42})")

    def test_id_property(self):
        """Test id set/get property."""
        var = DapType("var")
        var.id = "new"
        self.assertEqual(var.id, "new")
        self.assertEqual(var._id, "new")

    def test_getattr(self):
        """Test lazy attribute retrieval."""
        var = DapType("var", foo="bar", value=42)

        self.assertEqual(var.attributes["foo"], "bar")
        self.assertEqual(var.foo, "bar")

        with self.assertRaises(AttributeError):
            var.baz

        with self.assertRaises(KeyError):
            var.attributes['baz']

    def test_children(self):
        """Test children method."""
        var = DapType("var")
        self.assertEqual(var.children(), ())


class TestBaseType(unittest.TestCase):

    """Test the base Pydap type, which is analogous to a Numpy array."""

    def test_no_data(self):
        """Test empty data and dimensions attributes."""
        var = BaseType("var")
        self.assertIsNone(var.data)
        self.assertEqual(var.dimensions, ())

    def test_data_and_dimensions(self):
        """Test data and dimsensions assignment."""
        var = BaseType("var", [42], ('x',))
        self.assertEqual(var.data, [42])
        self.assertEqual(var.dimensions, ('x',))

    def test_repr(self):
        """Test ``__repr__`` method."""
        var = BaseType("var", 42, foo="bar")
        self.assertEqual(repr(var), "<BaseType with data 42>")

    def test_dtype(self):
        """Test ``dtype`` property."""
        var = BaseType("var", np.array(1, np.int32))
        self.assertEqual(var.dtype, np.int32)

    def test_shape(self):
        """Test ``shape`` property."""
        var = BaseType("var", np.arange(16).reshape(2, 2, 2, 2))
        self.assertEqual(var.shape, (2, 2, 2, 2))

    def test_clone(self):
        """Test lightweight ``clone`` method."""
        original = BaseType("var", np.array(1))
        copy = original.clone()

        # note that clones share the same data:
        self.assertIsNot(original, copy)
        self.assertIs(original.data, copy.data)

        # test attributes
        self.assertEqual(original.id, copy.id)
        self.assertEqual(original.name, copy.name)
        self.assertEqual(original.dimensions, copy.dimensions)
        self.assertEqual(original.attributes, copy.attributes)

    def test_comparisons(self):
        """Test that comparisons are applied to data."""
        var = BaseType("var", np.array(1))
        self.assertTrue(var == 1)
        self.assertTrue(var != 2)
        self.assertTrue(var >= 0)
        self.assertTrue(var <= 2)
        self.assertTrue(var > 0)
        self.assertTrue(var < 2)

    def test_sequence_protocol(self):
        """Test that the object behaves like a sequence."""
        var = BaseType("var", np.arange(10))
        self.assertEqual(var[-5], 5)
        self.assertEqual(len(var), 10)
        self.assertEqual(list(var), range(10))

    def test_iter_protocol(self):
        """Test that the object behaves like an iterable."""
        var = BaseType("var", np.arange(10))
        self.assertEqual(list(iter(var)), range(10))


class TestStructureType(unittest.TestCase):

    """Test Pydap structures, which are dict-like objcets."""

    def test_init(self):
        """Test attributes used for dict-like behavior."""
        var = StructureType("var")
        self.assertEqual(var._keys, [])
        self.assertEqual(var._dict, {})

    def test_repr(self):
        """Test ``__repr__`` method."""
        var = StructureType("var")
        self.assertEqual(repr(var), "<StructureType with children >")

        var["one"] = BaseType("one")
        var["two"] = BaseType("two")
        self.assertEqual(
                repr(var), "<StructureType with children 'one', 'two'>")

    def test_contains(self):
        """Test container behavior."""
        var = StructureType("var")
        var["one"] = BaseType("one")
        self.assertIn("one", var)

    def test_lazy_attribute(self):
        """Test lazy attribute, returning first child."""
        var = StructureType("var", value=42, one="1")
        var["one"] = BaseType("one")
        self.assertEqual(var.value, 42)
        self.assertIs(var.one, var["one"])

    def test_iter(self):
        """Test iteration, should return all children."""
        var = StructureType("var", value=42, one="1")
        var["one"] = BaseType("one")
        var["two"] = BaseType("two")
        self.assertEqual(list(iter(var)), [var["one"], var["two"]])

    def test_setitem(self):
        """Test item assignment.

        Assignment requires the key and the name of the variable to be
        identical. It also takes care of reordering children that are
        reinserted.

        """
        var = StructureType("var")
        var["foo.bar"] = BaseType("foo.bar")
        self.assertEqual(var.keys(), ['foo%2Ebar'])

        with self.assertRaises(KeyError):
            var["bar"] = BaseType("baz")

        # test reordering
        var["bar"] = BaseType("bar")
        var["foo.bar"] = BaseType("foo.bar")
        self.assertEqual(var.keys(), ['bar', 'foo%2Ebar'])

    def test_getitem(self):
        """Test item retrieval."""
        var = StructureType("var")
        child = BaseType("child")
        var["child"] = child
        self.assertIs(var["child"], child)

    def test_delitem(self):
        """Test item deletion."""
        var = StructureType("var")
        child = var["one"] = BaseType("one")

        self.assertEqual(var.keys(), ['one'])

        del var["one"]
        self.assertEqual(var.keys(), [])
        self.assertNotIn(child, var)

    def test_get_data(self):
        """Test that structure collects data from children."""
        var = StructureType("var", value=42, one="1")
        var["one"] = BaseType("one", 1)
        var["two"] = BaseType("two", 2)
        self.assertEqual(var.data, [1, 2])

    def test_set_data(self):
        """Test that data is propagated to children."""
        var = StructureType("var", value=42, one="1")
        var["one"] = BaseType("one")
        var["two"] = BaseType("two")
        var.data = [10, 20]
        self.assertEqual(var["one"].data, 10)
        self.assertEqual(var["two"].data, 20)

    def test_clone(self):
        """Test lightweight clone of a structure."""
        original = StructureType("var", value=42, one="1")
        original["one"] = BaseType("one")
        original["two"] = BaseType("two")
        original.data = [10, 20]

        copy = original.clone()

        # note that clones share the same data:
        self.assertIsNot(original, copy)
        self.assertIsNot(original["one"], copy["one"])
        self.assertIs(original["one"].data, copy["one"].data)
        self.assertIsNot(original["two"], copy["two"])
        self.assertIs(original["two"].data, copy["two"].data)

        # test attributes
        self.assertEqual(original.id, copy.id)
        self.assertEqual(original.name, copy.name)


class TestDatasetType(unittest.TestCase):

    """Test a Pydap structure."""

    def test_setitem(self):
        """Test item assignment."""
        dataset = DatasetType("dataset")
        dataset["one"] = BaseType("one")
        self.assertEqual(dataset["one"].id, "one")

    def test_id(self):
        """Test that the dataset id is not propagated."""
        dataset = DatasetType("dataset")
        child = BaseType("child")
        child.id = "error"
        dataset["child"] = child
        self.assertEqual(child.id, "child")


class TestSequenceType(unittest.TestCase):
    pass
