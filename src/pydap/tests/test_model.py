"""Test the data model."""

import copy
import numpy as np
from pydap.model import (DatasetType, BaseType,
                         SequenceType, StructureType,
                         GridType, DapType)
import pytest
import warnings

warnings.simplefilter('always')


# Test the super class for Pydap types.
def test_DapType_quote():
    """Test that names are properly quoted."""
    var = DapType("foo.bar[0]")
    assert (var.name == "foo%2Ebar%5B0%5D")


def test_DapType_attributes():
    """Test attribute assignment.

    Note that ``**kwargs`` have precedence.

    """
    attributes = {"foo": "bar", "value": 43}
    var = DapType("var", attributes=attributes, value=42)
    assert (var.attributes == {"foo": "bar", "value": 42})


def test_DapType_id():
    """Test id assignment."""
    var = DapType("var")
    assert (var._id == "var")
    assert (var.id == "var")


def test_DapType_repr():
    """Test the ``__repr__`` method."""
    var = DapType("var", foo="bar")
    assert (
        repr(var) ==
        "DapType('var', {'foo': 'bar'})")


def test_DapType_id_property():
    """Test id set/get property."""
    var = DapType("var")
    var.id = "new"
    assert (var.id == "new")
    assert (var._id == "new")


def test_DapType_getattr():
    """Test lazy attribute retrieval."""
    var = DapType("var", foo="bar", value=42)

    assert (var.attributes["foo"] == "bar")
    assert (var.foo == "bar")

    with pytest.raises(AttributeError):
        var.baz

    with pytest.raises(KeyError):
        var.attributes['baz']


def test_DapType_children():
    """Test children method."""
    var = DapType("var")
    assert (var.children() == ())


# Test the base Pydap type.
def test_BaseType_no_data():
    """Test empty data and dimensions attributes."""
    var = BaseType("var")
    assert var.data is None
    assert (var.dimensions == ())


def test_BaseType_data_and_dimensions():
    """Test data and dimensions assignment."""
    var = BaseType("var", [42], ('x',))
    assert (var.data == [42])
    assert (var.dimensions == ('x',))


def test_BaseType_repr():
    """Test ``__repr__`` method."""
    var = BaseType("var", 42, foo="bar")
    assert (repr(var) == "<BaseType with data array(42)>")


def test_BaseType_dtype():
    """Test ``dtype`` property."""
    var = BaseType("var", np.array(1, np.int32))
    assert (var.dtype == np.int32)


def test_BaseType_shape():
    """Test ``shape`` property."""
    var = BaseType("var", np.arange(16).reshape(2, 2, 2, 2))
    assert (var.shape == (2, 2, 2, 2))


def test_BaseType_size():
    """Test ``size`` property."""
    var = BaseType("var", np.arange(16).reshape(2, 2, 2, 2))
    assert (var.size == 16)


def test_BaseType_ndim():
    """Test ``ndim`` property."""
    var = BaseType("var", np.arange(16).reshape(2, 2, 2, 2))
    assert (var.ndim == 4)


def test_BaseType_copy():
    """Test lightweight ``__copy__`` method."""
    original = BaseType("var", np.array(1))
    clone = copy.copy(original)

    # note that clones share the same data:
    assert original is not clone
    assert original.data is clone.data

    # test attributes
    assert (original.id == clone.id)
    assert (original.name == clone.name)
    assert (original.dimensions == clone.dimensions)
    assert (original.attributes == clone.attributes)


def test_BaseType_comparisons():
    """Test that comparisons are applied to data."""
    var = BaseType("var", np.array(1))
    assert (var == 1)
    assert (var != 2)
    assert (var >= 0)
    assert (var <= 2)
    assert (var > 0)
    assert (var < 2)


def test_BaseType_sequence_protocol():
    """Test that the object behaves like a sequence."""
    var = BaseType("var", np.arange(10))
    assert (var[-5] == 5)
    assert (len(var) == 10)
    assert (list(var) == list(range(10)))


def test_BaseType_iter_protocol():
    """Test that the object behaves like an iterable."""
    var = BaseType("var", np.arange(10))
    assert (list(iter(var)) == list(range(10)))


def test_BaseType_array():
    """Test array conversion."""
    var = BaseType("var", np.arange(16).reshape(2, 2, 2, 2))
    np.testing.assert_array_equal(np.array(var),
                                  np.arange(16).reshape(2, 2, 2, 2))


# Test Pydap structures.
def test_StructureType_init():
    """Test attributes used for dict-like behavior."""
    var = StructureType("var")
    assert (var._visible_keys == [])
    assert (var._dict == {})


def test_StructureType_instance():
    """Test that it is a Mapping and DapType."""
    var = StructureType("var")
    from collections import Mapping
    assert isinstance(var, Mapping)
    assert isinstance(var, DapType)


def test_StructureType_repr():
    """Test ``__repr__`` method."""
    var = StructureType("var")
    assert (repr(var) == "<StructureType with children >")

    var["one"] = BaseType("one")
    var["two"] = BaseType("two")
    assert (
        repr(var) == "<StructureType with children 'one', 'two'>")


def test_StructureType_len():
    """Test ``__len__`` method."""
    var = StructureType("var")
    var["one"] = BaseType("one")
    var["two"] = BaseType("two")
    assert (len(var) == 2)


def test_StructureType_contains():
    """Test container behavior."""
    var = StructureType("var")
    var["one"] = BaseType("one")
    assert "one" in var


def test_StructureType_lazy_attribute():
    """Test lazy attribute, returning first child."""
    var = StructureType("var", value=42, one="1")
    var["one"] = BaseType("one")
    assert (var.value == 42)
    assert (var.one is var["one"])


def test_StructureType_children():
    """Test children iteration, should return all children."""
    var = StructureType("var", value=42, one="1")
    var["one"] = BaseType("one")
    var["two"] = BaseType("two")
    assert (list(var.children()) == [var["one"], var["two"]])


def test_StructureType_setitem():
    """Test item assignment.

    Assignment requires the key and the name of the variable to be
    identical. It also takes care of reordering children that are
    reinserted.

    """
    var = StructureType("var")
    var["foo.bar"] = BaseType("foo.bar")
    assert (list(var.keys()) == ['foo%2Ebar'])

    with pytest.raises(KeyError):
        var["bar"] = BaseType("baz")

    # test reordering
    var["bar"] = BaseType("bar")
    var["foo.bar"] = BaseType("foo.bar")
    assert (list(var.keys()) == ['bar', 'foo%2Ebar'])


def test_StructureType_getitem():
    """Test item retrieval."""
    var = StructureType("var")
    child = BaseType("child")
    var["child"] = child
    assert var["child"] is child
    with pytest.raises(KeyError):
        var["unloved child"]
    with pytest.raises(KeyError):
        var[:]

    assert var["parent.child"] is child
    assert var["grandparent.parent.child"] is child


def test_StructureType_getitem_tuple():
    """Test multiple item retrieval."""
    var = StructureType("var")
    for name in ['child1', 'child2', 'child3']:
        child = BaseType(name)
        var[name] = child
        assert var[name] is child
    assert list(var['child1', 'child3'].keys()) == ['child1', 'child3']
    assert (list(var['child1', 'child3']._all_keys()) ==
            ['child1', 'child2', 'child3'])
    with pytest.raises(KeyError):
        var['unloved child']


def test_StructureType_delitem():
    """Test item deletion."""
    var = StructureType("var")
    var["one"] = BaseType("one")
    var["two"] = BaseType("two")
    var["three"] = BaseType("three")

    assert (list(var.keys()) == ['one', 'two', 'three'])

    del var["one"]
    assert (list(var.keys()) == ['two', 'three'])

    # Make sure that one can safely delete
    # a non visible child:
    subset = var[("two",)]
    assert list(subset.keys()) == ['two']
    assert isinstance(subset, StructureType)
    subset.__delitem__("three")

    # Cannot delete an inexistent child:
    with pytest.raises(KeyError):
        del var["inexistent"]


def test_StructureType_get_data():
    """Test that structure collects data from children."""
    var = StructureType("var", value=42, one="1")
    var["one"] = BaseType("one", 1)
    var["two"] = BaseType("two", 2)
    assert (var.data == [1, 2])


def test_StructureType_set_data():
    """Test that data is propagated to children."""
    var = StructureType("var", value=42, one="1")
    var["one"] = BaseType("one")
    var["two"] = BaseType("two")
    var.data = [10, 20]
    assert (var["one"].data == 10)
    assert (var["two"].data == 20)


def test_StructureType_copy():
    """Test lightweight clone of a structure."""
    original = StructureType("var", value=42, one="1")
    original["one"] = BaseType("one")
    original["two"] = BaseType("two")
    original.data = [10, 20]

    clone = copy.copy(original)

    # note that clones share the same data:
    assert original is not clone
    assert original["one"] is not clone["one"]
    assert original["one"].data is clone["one"].data
    assert original["two"] is not clone["two"]
    assert original["two"].data is clone["two"].data

    # test attributes
    assert (original.id == clone.id)
    assert (original.name == clone.name)


# Test a Pydap structure.
def test_DatasetType_setitem():
    """Test item assignment."""
    dataset = DatasetType("dataset")
    dataset["one"] = BaseType("one")
    assert dataset["one"].id == "one"


def test_DatasetType_id():
    """Test that the dataset id is not propagated."""
    dataset = DatasetType("dataset")
    child = BaseType("child")
    child.id = "error"
    dataset["child"] = child
    assert (child.id == "child")


@pytest.fixture
def sequence_example():
    """Create a standard sequence from the DAP spec."""
    example = SequenceType("example")
    example["index"] = BaseType("index")
    example["temperature"] = BaseType("temperature")
    example["site"] = BaseType("site")
    example.data = np.rec.fromrecords([
        (10, 15.2, "Diamond_St"),
        (11, 13.1, 'Blacktail_Loop'),
        (12, 13.3, 'Platinum_St'),
        (13, 12.1, 'Kodiak_Trail')], names=list(example.keys()))
    return example


def test_SequenceType_data(sequence_example):
    """Test data assignment in sequences."""
    np.testing.assert_array_equal(
        sequence_example["index"].data, np.array([10, 11, 12, 13]))


def test_SequenceType_len(sequence_example, recwarn):
    """Test that length is read from the data attribute."""
    assert len(list(sequence_example.keys())) == 3
    assert len(sequence_example) == 4
    assert len(recwarn) == 1
    assert recwarn.pop(PendingDeprecationWarning)


def test_SequenceType_iterdata(sequence_example):
    """Test that data iteration happens over data."""
    for a, b in zip(sequence_example.iterdata(), sequence_example.data):
        for sub_a, sub_b in zip(a, b):
            assert sub_a == sub_b


def test_SequenceType_iter(sequence_example):
    """Test that iteration happens ove data."""
    # Remove in pydap 3.4
    for a, b in zip(iter(sequence_example), sequence_example.data):
        for sub_a, sub_b in zip(a, b):
            assert sub_a == sub_b


def test_SequenceType_iter_deprecation(sequence_example, recwarn):
    """Test that direct iteration over data attribute is deprecated."""
    # Remove in pydap 3.4
    iter(sequence_example)
    assert len(recwarn) == 1
    assert recwarn.pop(PendingDeprecationWarning)


def test_SequenceType_items(sequence_example):
    """Test that iteration happens over the child names."""
    assert list(sequence_example.items()) == [(key, sequence_example[key])
                                              for key in ['index',
                                                          'temperature',
                                                          'site']]


def test_SequenceType_values(sequence_example):
    """Test that iteration happens over the child names."""
    assert list(sequence_example.values()) == [sequence_example[key]
                                               for key in ['index',
                                                           'temperature',
                                                           'site']]


def test_SequenceType_getitem(sequence_example):
    """Test item retrieval.

    The ``__getitem__`` method is overloaded for sequences, and behavior
    will depend on the type of the key. It can either return a child or a
    new sequence.

    """
    # a string should return the corresponding child
    assert isinstance(sequence_example["index"], BaseType)

    # a tuple should reorder the children
    assert list(sequence_example.keys()) == ["index", "temperature", "site"]
    modified = sequence_example["site", "temperature"]
    assert isinstance(modified, SequenceType)
    assert list(modified.keys()) == ["site", "temperature"]

    # the return sequence is a new one
    assert sequence_example is not modified
    assert sequence_example["site"] is not modified["site"]
    assert isinstance(sequence_example["site"], BaseType)

    # and the data is not shared
    assert sequence_example["site"].data is not modified["site"].data

    subset = sequence_example["site"][::2]
    assert sequence_example is not subset
    assert isinstance(subset, BaseType)

    # it is also possible to slice the data, returning a new sequence
    subset = sequence_example[sequence_example["index"] > 11]
    assert sequence_example is not subset
    assert isinstance(subset, SequenceType)
    np.testing.assert_array_equal(
        subset.data,
        sequence_example.data[sequence_example.data["index"] > 11])


def test_SequenceType_copy(sequence_example):
    """Test the lightweight ``__copy__`` method."""
    clone = copy.copy(sequence_example)
    assert sequence_example is not clone
    assert (sequence_example.data == clone.data).all()


# Test Pydap grids.
@pytest.fixture()
def gridtype_example():
    """Create a simple grid."""
    example = GridType("example")
    example["a"] = BaseType("a", data=np.arange(30*50).reshape(30, 50))
    example["x"] = BaseType("x", data=np.arange(30))
    example["y"] = BaseType("y", data=np.arange(50))
    return example


def test_GridType_repr(gridtype_example):
    """Test ``__repr__`` of grids."""
    assert (
        repr(gridtype_example) ==
        "<GridType with array 'a' and maps 'x', 'y'>")


def test_GridType_dtype(gridtype_example):
    """Test ``dtype`` of grids."""
    assert (gridtype_example.dtype == np.dtype('l'))


def test_GridType_shape(gridtype_example):
    """Test ``shape`` of grids."""
    assert (gridtype_example.shape == (30, 50))


def test_GridType_size(gridtype_example):
    """Test ``size`` of grids."""
    assert (gridtype_example.size == 30 * 50)


def test_GridType_ndim(gridtype_example):
    """Test ``ndim`` of grids."""
    assert (gridtype_example.ndim == 2)


def test_GridType_len(gridtype_example):
    """Test ``__len__`` of grids."""
    assert (len(gridtype_example) == 3)


def test_GridType_getitem(gridtype_example):
    """Test item retrieval.

    As with sequences, this might return a child or a new grid, depending
    on the key type.

    """
    # a string should return the corresponding child
    assert isinstance(gridtype_example["a"], BaseType)

    # otherwise it should return a new grid with a subset of the data
    subset = gridtype_example[20:22, 40:43]
    assert (subset["a"].shape == (2, 3))
    assert (subset["x"].shape == (2,))
    assert (subset["y"].shape == (3,))

    assert gridtype_example is not subset

    # pick more than one child:
    np.testing.assert_equal(subset["a", "x"]["a"].data,
                            subset["a"].data)
    np.testing.assert_equal(subset["a", "x"]["x"].data,
                            subset["x"].data)


def test_GridType_getitem_not_tuple(gridtype_example):
    """Test that method works with non-tuple slices."""
    subset = gridtype_example[20:22]
    assert (subset["a"].shape == (2, 50))
    assert (subset["x"].shape == (2,))
    assert (subset["y"].shape == (50,))


def test_GridType_array(gridtype_example):
    """Test ``array`` property."""
    assert gridtype_example.array is gridtype_example["a"]


def test_GridType_array2(gridtype_example):
    """Test __array__ method."""
    np.testing.assert_array_equal(np.array(gridtype_example),
                                  gridtype_example["a"].data)


def test_GridType_maps(gridtype_example):
    """Test ``maps`` property."""
    assert (
        list(gridtype_example.maps.items()) ==
        [("x", gridtype_example["x"]), ("y", gridtype_example["y"])])


def test_GridType_dimensions(gridtype_example):
    """Test ``dimensions`` property."""
    assert (gridtype_example.dimensions == ("x", "y"))
