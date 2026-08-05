"""Test pydap xml API to generate dmr responses."""

import pytest

from pydap.parsers.dmr import dmr_to_dataset
from pydap.responses.xml import (
    DAP4_NS,
    _basetype_element,
    _group_element,
    _new_root,
    _qual_name,
    _sequence_element,
    build_dmr_element,
    build_dmr_tree,
    dmr_tree_to_string,
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
