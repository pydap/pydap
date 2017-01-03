"""Test the data model."""

import copy
import numpy as np
from pydap.model import (DatasetType, BaseType,
                         SequenceType, StructureType,
                         GridType, DapType)

import unittest


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
        var = DapType("var", foo="bar")
        self.assertEqual(
            repr(var),
            "DapType('var', {'foo': 'bar'})")

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

    """Test the base Pydap type."""

    def test_no_data(self):
        """Test empty data and dimensions attributes."""
        var = BaseType("var")
        self.assertIsNone(var.data)
        self.assertEqual(var.dimensions, ())

    def test_data_and_dimensions(self):
        """Test data and dimensions assignment."""
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

    def test_copy(self):
        """Test lightweight ``__copy__`` method."""
        original = BaseType("var", np.array(1))
        clone = copy.copy(original)

        # note that clones share the same data:
        self.assertIsNot(original, clone)
        self.assertIs(original.data, clone.data)

        # test attributes
        self.assertEqual(original.id, clone.id)
        self.assertEqual(original.name, clone.name)
        self.assertEqual(original.dimensions, clone.dimensions)
        self.assertEqual(original.attributes, clone.attributes)

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
        self.assertEqual(list(var), list(range(10)))

    def test_iter_protocol(self):
        """Test that the object behaves like an iterable."""
        var = BaseType("var", np.arange(10))
        self.assertEqual(list(iter(var)), list(range(10)))


class TestStructureType(unittest.TestCase):

    """Test Pydap structures."""

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
        var["one"] = BaseType("one")

        self.assertEqual(var.keys(), ['one'])

        del var["one"]
        self.assertEqual(var.keys(), [])

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

    def test_copy(self):
        """Test lightweight clone of a structure."""
        original = StructureType("var", value=42, one="1")
        original["one"] = BaseType("one")
        original["two"] = BaseType("two")
        original.data = [10, 20]

        clone = copy.copy(original)

        # note that clones share the same data:
        self.assertIsNot(original, clone)
        self.assertIsNot(original["one"], clone["one"])
        self.assertIs(original["one"].data, clone["one"].data)
        self.assertIsNot(original["two"], clone["two"])
        self.assertIs(original["two"].data, clone["two"].data)

        # test attributes
        self.assertEqual(original.id, clone.id)
        self.assertEqual(original.name, clone.name)


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

    """Test Pydap sequences."""

    def setUp(self):
        """Create a standard sequence from the DAP spec."""
        example = SequenceType("example")
        example["index"] = BaseType("index")
        example["temperature"] = BaseType("temperature")
        example["site"] = BaseType("site")
        example.data = np.rec.fromrecords([
            (10, 15.2, "Diamond_St"),
            (11, 13.1, 'Blacktail_Loop'),
            (12, 13.3, 'Platinum_St'),
            (13, 12.1, 'Kodiak_Trail')], names=example.keys())

        self.example = example

    def test_data(self):
        """Test data assignment in sequences."""
        np.testing.assert_array_equal(
            self.example["index"].data, np.array([10, 11, 12, 13]))

    def test_len(self):
        """Test that length is read from the data attribute."""
        self.assertEqual(len(self.example.data), 4)

    def test_iter_(self):
        """Test that iteration happens over the data attribute."""
        for a, b in zip(iter(self.example), iter(self.example.data)):
            self.assertEqual(a[0], b[0])
            self.assertAlmostEqual(a[1], b[1])
            self.assertEqual(a[2], b[2])

    def test_getitem(self):
        """Test item retrieval.

        The ``__getitem__`` method is overloaded for sequences, and behavior
        will depend on the type of the key. It can either return a child or a
        new sequence.

        """
        # a string should return the corresponding child
        self.assertIsInstance(self.example["index"], BaseType)

        # a tuple should reorder the children
        self.assertEqual(
            self.example.keys(), ["index", "temperature", "site"])
        modified = self.example["site", "temperature"]
        self.assertEqual(modified.keys(), ["site", "temperature"])

        # the return sequence is a new one
        self.assertIsNot(self.example, modified)
        self.assertIsNot(self.example["site"], modified["site"])

        # and the data is not shared
        self.assertIsNot(self.example["site"].data, modified["site"].data)

        # it is also possible to slice the data, returning a new sequence
        subset = self.example[self.example["index"] > 11]
        self.assertIsNot(self.example, subset)
        np.testing.assert_array_equal(
            subset.data,
            self.example.data[self.example.data["index"] > 11])

    def test_copy(self):
        """Test the lightweight ``__copy__`` method."""
        clone = copy.copy(self.example)
        self.assertIsNot(self.example, clone)
        self.assertIs(self.example.data, clone.data)


class TestGridType(unittest.TestCase):

    """Test Pydap grids."""

    def setUp(self):
        """Create a simple grid."""
        example = GridType("example")
        example["a"] = BaseType("a", data=np.arange(30*50).reshape(30, 50))
        example["x"] = BaseType("x", data=np.arange(30))
        example["y"] = BaseType("y", data=np.arange(50))

        self.example = example

    def test_repr(self):
        """Test ``__repr__`` of grids."""
        self.assertEqual(
            repr(self.example), "<GridType with array 'a' and maps 'x', 'y'>")

    def test_getitem(self):
        """Test item retrieval.

        As with sequences, this might return a child or a new grid, depending
        on the key type.

        """
        # a string should return the corresponding child
        self.assertIsInstance(self.example["a"], BaseType)

        # otherwise it should return a new grid with a subset of the data
        subset = self.example[20:22, 40:43]
        self.assertEqual(subset["a"].shape, (2, 3))
        self.assertEqual(subset["x"].shape, (2,))
        self.assertEqual(subset["y"].shape, (3,))

        self.assertIsNot(self.example, subset)

    def test_geitem_not_tuple(self):
        """Test that method works with non-tuple slices."""
        subset = self.example[20:22]
        self.assertEqual(subset["a"].shape, (2, 50))
        self.assertEqual(subset["x"].shape, (2,))
        self.assertEqual(subset["y"].shape, (50,))

    def test_array(self):
        """Test ``array`` property."""
        self.assertIs(self.example.array, self.example["a"])

    def test_maps(self):
        """Test ``maps`` property."""
        self.assertEqual(
            list(self.example.maps.items()),
            [("x", self.example["x"]), ("y", self.example["y"])])

    def test_dimensions(self):
        """Test ``dimensions`` property."""
        self.assertEqual(self.example.dimensions, ("x", "y"))
