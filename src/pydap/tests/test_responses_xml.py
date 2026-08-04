"""Test pydap xml API to generate dmr responses."""

import pytest
from lxml import etree

from pydap.responses.xml import build_dmr_tree, build_dmr_element, _group_element, _basetype_element, _sequence_element, _group_element 
from pydap.tests.datasets import SimpleGroup, rain, SimpleSequence


# the following should work but currently fails
def test_build_dmr_tree():
    """Test that the xml API can generate a dom tree from a dataset."""
    with pytest.raises(TypeError):
        xml_tree = build_dmr_tree(SimpleGroup)
        # test that it can be parsed by lxml and that it is the
        # root element of the tree/dataset
        root = etree.fromstring(xml_tree)
        assert root.tag == "example dataset"
        assert isinstance(root, etree._Element)


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


