"""Test pydap xml API to generate dmr responses."""

import pytest

from pydap.parsers.dmr import dmr_to_dataset
from pydap.responses.xml import (
    DAP4_NS,
    _basetype_element,
    _group_element,
    _new_root,
    _sequence_element,
    build_dmr_element,
    build_dmr_tree,
    dmr_tree_to_string,
)
from pydap.tests.datasets import SimpleGroup, SimpleSequence


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


def test_roundtrip_dataset_xml_dataset():
    """Test that a dataset can be converted to xml and back to a dataset."""
    domtree = build_dmr_tree(SimpleGroup)
    dmr = dmr_tree_to_string(domtree)
    dataset = dmr_to_dataset(dmr)

    assert dataset.variables() == SimpleGroup.variables()
    assert SimpleGroup["SimpleGroup"].variables() == dataset["SimpleGroup"].variables()
