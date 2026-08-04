"""Test pydap xml API to generate dmr responses."""

import pytest
from lxml import etree

from pydap.responses.xml import build_dmr_tree, build_dmr_element, _group_element, _basetype_element, _sequence_element, _group_element, DAP4_NS
from pydap.tests.datasets import SimpleGroup, rain, SimpleSequence


# the following should work but currently fails
def test_build_dmr_tree():
    """Test that the xml API can generate a dom tree from a dataset."""
    domtree = build_dmr_tree(SimpleGroup)
    assert domtree.tag == "{" + DAP4_NS["dap"] +"}" + "Dataset"


@pytest.mark.parametrize(
    "pydapobject, expected_type",
    [
        (SimpleGroup["SimpleGroup"], _group_element),
        (SimpleGroup["time"], _basetype_element),
        (SimpleGroup["SimpleGroup/Temperature"], _basetype_element),
        (SimpleSequence['cast'], _sequence_element),
    ]
)
def test_registered_object(pydapobject, expected_type):
    """Test that the correct element type is returned for a given pydap object."""
    assert build_dmr_element.dispatch(type(pydapobject)) == expected_type


