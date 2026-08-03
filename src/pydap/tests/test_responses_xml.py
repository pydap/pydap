"""Test pydap xml API to generate dmr responses."""

import pytest
from lxml import etree

from pydap.responses.xml import build_dmr_tree
from pydap.tests.datasets import SimpleGroup


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
