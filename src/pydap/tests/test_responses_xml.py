"""Test pydap xml API to generate dmr responses."""

import numpy as np
import pytest

from pydap.model import DatasetType, GroupType
from pydap.parsers.dmr import dmr_to_dataset
from pydap.responses.xml import (
    DAP4_NS,
    _attribute_items,
    _basetype_element,
    _build_dimensions,
    _children_by_declaration_order,
    _dimensions,
    _dtype_to_dap4,
    _group_element,
    _is_group,
    _new_child,
    _new_root,
    _qual_name,
    _sequence_element,
    build_dmr_element,
    build_dmr_tree,
    dmr_tree_to_string,
    _attribute_items,
    _dimensions,
    _children_by_declaration_order, _is_group,
)
from pydap.tests.datasets import DSUnDims, SimpleGroup, SimpleSequence


# the following should work but currently fails
def test_build_dmr_tree():
    """Test that the xml API can generate a dom tree from a dataset."""
    domtree = build_dmr_tree(SimpleGroup)
    assert domtree.tag == "{" + DAP4_NS["dap"] + "}" + "Dataset"
    assert len(domtree.findall("dap:Group", DAP4_NS)) == 1
    assert len(domtree.findall("dap:Dimension", DAP4_NS)) == 2
    assert len(domtree.findall("dap:Float32", DAP4_NS)) == 2
    assert len(domtree.findall("dap:Attribute", DAP4_NS)) == 1


@pytest.mark.parametrize(
    "pydapobject, expected_type",
    [
        (SimpleGroup["SimpleGroup"], _group_element),
        (SimpleGroup["time"], _basetype_element),
        (SimpleGroup["SimpleGroup/Temperature"], _basetype_element),
        (SimpleSequence["cast"], _sequence_element),
    ],
)
def test_registered_object(pydapobject, expected_type):
    """Test that the correct element type is returned for a given pydap object."""
    assert build_dmr_element.dispatch(type(pydapobject)) == expected_type


def test_new_root():
    """Test that the new root element is created with the correct namespace."""
    el = _new_root("Dataset")
    assert el.tag == "{" + DAP4_NS["dap"] + "}" + "Dataset"


def test_build_dmr_element_group():
    """Test that the xml API can generate a dmr element from a group."""
    group = SimpleGroup["SimpleGroup"]
    root = _new_root("Dataset")
    element = build_dmr_element(group, parent=root)
    assert element.tag == "{" + DAP4_NS["dap"] + "}" + "Group"
    assert element.get("name") == group.name
    assert [el.get("name") for el in element.findall("dap:Float32", DAP4_NS)] == [
        "Temperature",
        "Salinity",
    ]
    assert [el.get("name") for el in element.findall("dap:Int16", DAP4_NS)] == [
        "Y",
        "X",
    ]
    assert [el.get("name") for el in element.findall("dap:Dimension", DAP4_NS)] == [
        "Y",
        "X",
    ]
    assert len(element.findall("dap:Attribute", DAP4_NS)) == 1


def test_build_dmr_element_basetype():
    """Test that the xml API can generate a dmr element from a basetype."""
    basetype = SimpleGroup["time"]
    root = _new_root("Dataset")
    element = build_dmr_element(basetype, parent=root)
    assert element.tag == "{" + DAP4_NS["dap"] + "}" + "Float32"
    assert element.get("name") == "time"
    assert len(element.findall("dap:Dim", DAP4_NS)) == 1
    assert element.findall("dap:Dim", DAP4_NS)[0].get("name") == "/time"


def test_build_dmr_element_sequence():
    """Test that the xml API can generate a dmr element from a sequence."""
    sequence = SimpleSequence["cast"]
    root = _new_root("Dataset")
    element = build_dmr_element(sequence, parent=root)
    assert element.tag == "{" + DAP4_NS["dap"] + "}" + "Sequence"
    assert element.get("name") == "cast"
    assert element.findall("dap:String", DAP4_NS)[0].get("name") == "id"
    assert [el.get("name") for el in element.findall("dap:Int64", DAP4_NS)] == [
        "lon",
        "lat",
        "depth",
        "time",
        "temperature",
        "salinity",
        "pressure",
    ]


def test_roundtrip_dataset_xml_dataset():
    """Test that a dataset can be converted to xml and back to a dataset."""
    domtree = build_dmr_tree(SimpleGroup)
    dmr = dmr_tree_to_string(domtree)
    dataset = dmr_to_dataset(dmr)

    assert dataset.variables() == SimpleGroup.variables()
    assert SimpleGroup["SimpleGroup"].variables() == dataset["SimpleGroup"].variables()


def test_qual_name():
    """Tests that the DAP4 namespace is added to the tag of an element."""
    assert _qual_name("Dataset") == "{" + DAP4_NS["dap"] + "}" + "Dataset"


def test_roundtrip_dataset_xml_dataset_with_unnamed_dimensions():
    """Test that a dataset with unnamed dimensions can be converted to xml
    and back to a dataset."""
    domtree = build_dmr_tree(DSUnDims)
    dmr = dmr_tree_to_string(domtree)
    dataset = dmr_to_dataset(dmr)

    assert list(dataset["Group1"].variables()) == list(DSUnDims["Group1"].variables())
    assert list(DSUnDims["Group2"].variables()) == list(dataset["Group2"].variables())

    assert dataset["Group1"].dimensions == {
        "phony_dim_0": 1,
        "phony_dim_1": 4,
        "phony_dim_2": 4,
    }
    assert dataset["Group2"].dimensions == {
        "phony_dim_0": 1,
        "phony_dim_1": 4,
        "phony_dim_2": 4,
    }

    assert dataset["Group1/Temperature"].dims == [
        "/Group1/phony_dim_0",
        "/Group1/phony_dim_1",
        "/Group1/phony_dim_2",
    ]
    assert dataset["Group2/Salinity"].dims == [
        "/Group2/phony_dim_0",
        "/Group2/phony_dim_1",
        "/Group2/phony_dim_2",
    ]


@pytest.mark.parametrize(
    "dimensions",
    [
        ({"a": 1, "b": 2, "c": 3}),
        ({"a": 10, "b": 100}),
    ],
)
def test_build_dimensions(dimensions):
    """Test that the xml API generates correctly dmr dimensions"""
    root = _new_root("Dataset")
    _build_dimensions(root, dimensions)
    assert (
        dict(
            (el.get("name"), int(el.get("size")))
            for el in root.findall("dap:Dimension", DAP4_NS)
        )
        == dimensions
    )


@pytest.mark.parametrize(
    "arr, expected_type",
    [
        (np.array([1], dtype=np.int8), "Int8"),
        (np.array([1], dtype=np.uint8), "UInt8"),
        (np.array([1], dtype=np.int16), "Int16"),
        (np.array([1], dtype=np.uint16), "UInt16"),
        (np.array([1], dtype=np.int32), "Int32"),
        (np.array([1], dtype=np.uint32), "UInt32"),
        (np.array([1], dtype=np.int64), "Int64"),
        (np.array([1], dtype=np.uint64), "UInt64"),
        (np.array([1.0], dtype=np.float32), "Float32"),
        (np.array([1.0], dtype=np.float64), "Float64"),
        (np.array([b"Hello"], dtype="S5"), "String"),
        (np.array(["Hello"], dtype="<U5"), "String"),
    ],
)
def test_dtype_to_dap4(arr, expected_type):
    """Test that the correct DAP4 type is returned for a given numpy array."""
    assert _dtype_to_dap4(arr.dtype) == expected_type


@pytest.mark.parametrize(
    "DAP4_type, attr_name",
    [
        ("Group", "test_group"),
        ("Float32", "Temperature"),
        ("Int16", "Index"),
        ("Sequence", "test_sequence"),
        ("String", "test_string"),
        (
            "boolean",
            "test_does_not_fail",
        ),  # <---not valid DAP4 type, but should not fail
    ],
)
def test_new_child(DAP4_type, attr_name):
    """Test that the new child element is created with the correct namespace.
    This function does not discriminate between different DAP4 types, i.e. it
    does not check that the correct element type is returned for a given DAP4 type.
    Also - it does not check that a DAP4 type is valid.
    """
    parent = _new_root("Dataset")
    el = _new_child(parent, DAP4_type, name=attr_name)
    assert el.tag == "{" + DAP4_NS["dap"] + "}" + DAP4_type
    assert el.get("name") == attr_name


def test_children_by_declaration_order_flat():
    """Test that the children of a group are returned in the order they were
    declared."""
    group = SimpleGroup["SimpleGroup"]
    children = _children_by_declaration_order(group)[0]
    assert [child.name for child in children] == [
        "Temperature",
        "Salinity",
        "Y",
        "X",
    ]


def test_children_by_declaration_order_nested_groups():
    """Test that the children of a group with nested groups are
    returned, and assert how deep into a nested hierarchy the function goes.
    """
    ds = DatasetType("test_root")
    ds.createGroup("A")
    ds.createGroup("A/B")
    ds.createGroup("A/B/C")
    ds.createVariable("A/B/C/var1", dims=["x"])
    ds.createGroup("D")
    children = _children_by_declaration_order(ds)
    flattened_children = [
        x for item in children for x in (item if isinstance(item, list) else [item])
    ]
    assert [child.name for child in flattened_children] == ["A", "D"]


def test_attribute_items():
    group = SimpleGroup["SimpleGroup"]
    root = _new_root("Dataset")
    element = build_dmr_element(group, parent=root)
    dataset_attrs = {}
    for item in element.findall("dap:Attribute", DAP4_NS):
        attr_name = item.get("name")
        attr_value = [value.text for value in item.findall("dap:Value", DAP4_NS)]
        dataset_attrs[attr_name] = attr_value[0]

    attr = dict(_attribute_items(dataset_attrs))
    assert attr == {"Description": "Test group with numerical data"}


def test_dimensions():
    group = SimpleGroup["SimpleGroup"]
    root = _new_root("Dataset")
    element = build_dmr_element(group, parent=root)
    group_dims = {}
    for dims in element.findall("dap:Dimension", DAP4_NS):
        dim_name = dims.get("name")
        print("name: " + dim_name)
        dim_value = int(dims.get("size"))
        print("value: " + str(dim_value))
        group_dims[dim_name] = dim_value

    dimension_attrs = {
        "dimensions": group_dims,
        "Description": "Test group with numerical data",
    }
    print("attr: " + str(dimension_attrs))

    result = _dimensions(dimension_attrs)
    assert result == {"Y": 4, "X": 4}


def test_is_group():
    group = SimpleGroup["SimpleGroup"]
    root = _new_root("Dataset")
    element = build_dmr_element(group, parent=root)

    simple_group = GroupType(name=element.get("name"))
    assert _is_group(simple_group) is True
