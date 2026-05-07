"""Test the DMR response with DAP4 protocol."""

import os
import unittest
from xml.etree import ElementTree as ET

import numpy as np
import pytest
from webob.headers import ResponseHeaders
from webtest import TestApp as App

from pydap.handlers.lib import BaseHandler
from pydap.lib import __version__
from pydap.model import BaseType, DatasetType
from pydap.parsers.dmr import dmr_to_dataset
from pydap.responses.dmr import DMRResponse, dmr
from pydap.tests.datasets import DSUnDims, SimpleArray, SimpleGroup


def load_dmr_file(file_path):
    abs_path = os.path.join(os.path.dirname(__file__), file_path)
    with open(abs_path, "r") as dmr_file:
        text = dmr_file.read()
    return text


class TestDMRResponseGroup(unittest.TestCase):
    """Test DMR response from groups."""

    def setUp(self):
        """Create a simple WSGI app."""
        app = App(BaseHandler(SimpleGroup))
        self.res = app.get("/.dmr")

    def test_status(self):
        """Test the status code."""
        self.assertEqual(self.res.status, "200 OK")

    def test_dispatcher(self):
        """Test the single dispatcher."""
        with self.assertRaises(StopIteration):
            dmr(None)

    def test_content_type(self):
        """Test the content type."""
        self.assertEqual(self.res.content_type, "text/plain")

    def test_charset(self):
        """Test the charset."""
        self.assertEqual(self.res.charset, "ascii")

    def test_headers(self):
        """Test the headers from the response."""
        self.assertEqual(
            self.res.headers,
            ResponseHeaders(
                [
                    ("OPeNDAP-Server", "pydap/" + __version__),
                    ("Content-description", "dmr"),
                    ("Content-type", "text/plain; charset=ascii"),
                    ("Access-Control-Allow-Origin", "*"),
                    (
                        "Access-Control-Allow-Headers",
                        "Origin, X-Requested-With, Content-Type",
                    ),
                    ("Content-Length", "2302"),
                ]
            ),
        )

    def test_body(self):
        """Test the generated DMR response"""
        dmr_text = load_dmr_file("data/dmrs/SimpleGroup.dmr")
        self.assertEqual(self.res.text, dmr_text)

    def test_body_parses_back_to_dataset(self):
        """Generated grouped DMR can be parsed back."""
        dataset = dmr_to_dataset(self.res.text)
        self.assertEqual(dataset["/SimpleGroup/Temperature"].dtype, np.dtype("f4"))
        self.assertEqual(
            dataset["/SimpleGroup/Temperature"].dims,
            SimpleGroup["/SimpleGroup/Temperature"].dims,
        )


class TestDMRResponseArray(unittest.TestCase):
    """Test DMR response for simple arrays."""

    def setUp(self):
        app = App(BaseHandler(SimpleArray))
        self.res = app.get("/.dmr")

    def test_body(self):
        dmr_text = load_dmr_file("data/dmrs/SimpleArray.dmr")
        self.assertEqual(self.res.text, dmr_text)

    def test_body_parses_back_to_dataset(self):
        dataset = dmr_to_dataset(self.res.text)
        self.assertEqual(dataset.dimensions, {"phony_dim_0": 5, "phony_dim_1": 2})
        self.assertEqual(dataset["byte"].dtype, np.dtype("u1"))
        self.assertEqual(dataset["byte"].shape, (5,))
        self.assertEqual(dataset["byte"].dims, ["/phony_dim_0"])
        self.assertEqual(dataset["string"].dtype, np.dtype("|S128"))
        self.assertEqual(dataset["string"].shape, (2,))
        self.assertEqual(dataset["string"].dims, ["/phony_dim_1"])

    def test_array_dimensions_are_named(self):
        self.assertNotIn("<Dim size=", self.res.text)
        self.assertIn('<Dimension name="phony_dim_0" size="5"/>', self.res.text)
        self.assertIn('<Dim name="/phony_dim_0"/>', self.res.text)


def test_dmr_names_missing_dimensions_in_group_scope():
    body = b"".join(DMRResponse(DSUnDims)).decode("ascii")

    root = ET.fromstring(body)
    groups = {
        child.attrib["name"]: child
        for child in root
        if child.tag.rsplit("}", 1)[-1] == "Group"
    }

    assert "<Dim size=" not in body
    assert all(child.tag.rsplit("}", 1)[-1] != "Dimension" for child in root)

    for group_name, var_name in [
        ("Group1", "Temperature"),
        ("Group2", "Salinity"),
    ]:
        group = groups[group_name]
        dimensions = [
            child for child in group if child.tag.rsplit("}", 1)[-1] == "Dimension"
        ]
        assert [dim.attrib["name"] for dim in dimensions] == [
            "phony_dim_0",
            "phony_dim_1",
            "phony_dim_2",
        ]
        assert [dim.attrib["size"] for dim in dimensions] == ["1", "4", "4"]

        variable = next(
            child for child in group if child.attrib.get("name") == var_name
        )
        dims = [child for child in variable if child.tag.rsplit("}", 1)[-1] == "Dim"]
        assert [dim.attrib["name"] for dim in dims] == [
            f"/{group_name}/phony_dim_0",
            f"/{group_name}/phony_dim_1",
            f"/{group_name}/phony_dim_2",
        ]

    assert "/Group1/phony_dim_0" in body
    assert "/Group2/phony_dim_0" in body


def test_dmr_escapes_xml_names_and_attribute_values():
    dataset = DatasetType('quoted "dataset"')
    dataset['quoted"name'] = BaseType(
        'quoted"name',
        data=np.array([1], dtype="i4"),
        attributes={"summary": 'A & B < C > D "quoted"'},
    )

    body = b"".join(DMRResponse(dataset)).decode("ascii")

    ET.fromstring(body)
    assert 'name="quoted%20&quot;dataset&quot;"' in body
    assert 'name="quoted&quot;name"' in body
    assert 'A &amp; B &lt; C &gt; D "quoted"' in body


def test_dmr_preserves_dots_in_dataset_name():
    dataset = DatasetType("example file.nc4.h5")

    body = b"".join(DMRResponse(dataset)).decode("ascii")

    ET.fromstring(body)
    assert 'name="example%20file.nc4.h5"' in body
    assert "%2E" not in body
    assert "%2e" not in body


def test_dmr_generates_attribute_forms_from_dap4_schema_examples():
    dataset = DatasetType(
        "AttributesFile.nc",
        description=(
            "DMR for testing Maps, Dims at root level "
            "(no Groups, Sequences or Structures)."
        ),
        offset1=np.int16(1),
        offsets=np.array([1, 2, 3], dtype=np.int64),
        _ChunkSizes=np.array([1, 964], dtype=np.uint32),
        FF_GLOBAL={"Server": "DODS FreeFrom based on FFND release 4.2.3"},
        iso_19139_dataset_xml=(
            "<?xml version=`1.0` encoding=`UTF-8` standalone=`no` ?> "
            "Text here inside an xml document"
        ),
    )
    dataset["var"] = BaseType(
        "var",
        data=np.array([1], dtype="i4"),
        attributes={
            "scale_factor": np.float32(36.0),
            "value_attribute_equivalent": np.array([5, 9674774], dtype=np.uint32),
        },
    )
    dataset.createGroup(
        "TestGroup",
        fileName=["File_001.h5", "File_002.h5"],
        identifier="L2Data",
        resolution=np.float32(36.0),
    )

    body = b"".join(DMRResponse(dataset)).decode("ascii")

    ET.fromstring(body)
    assert '<Attribute name="description" type="String">' in body
    assert "<Value>DMR for testing Maps, Dims at root level" in body
    assert '<Attribute name="offset1" type="Int16">' in body
    assert '<Attribute name="offsets" type="Int64">' in body
    assert body.count("<Value>1</Value>") >= 2
    assert "<Value>2</Value>" in body
    assert "<Value>3</Value>" in body
    assert '<Attribute name="_ChunkSizes" type="UInt32">' in body
    assert "<Value>964</Value>" in body
    assert '<Attribute name="FF_GLOBAL" type="Container">' in body
    assert '<Attribute name="Server" type="String">' in body
    assert '<Attribute name="iso_19139_dataset_xml" type="String">' in body
    assert "&lt;?xml version=`1.0` encoding=`UTF-8` standalone=`no` ?&gt;" in body
    assert '<Attribute name="scale_factor" type="Float32">' in body
    assert '<Attribute name="value_attribute_equivalent" type="UInt32">' in body
    assert "<Value>9674774</Value>" in body
    assert '<Group name="TestGroup">' in body
    assert '<Attribute name="fileName" type="String">' in body
    assert "<Value>File_001.h5</Value>" in body
    assert "<Value>File_002.h5</Value>" in body
    assert '<Attribute name="resolution" type="Float32">' in body


@pytest.mark.parametrize(
    "dtype, value, expected_type",
    [
        ("?", True, "UInt8"),
        ("i1", 1, "Int8"),
        ("u1", 1, "UInt8"),
        ("i2", 1, "Int16"),
        ("u2", 1, "UInt16"),
        ("i4", 1, "Int32"),
        ("u4", 1, "UInt32"),
        ("i8", 1, "Int64"),
        ("u8", 1, "UInt64"),
        ("f4", 1.0, "Float32"),
        ("f8", 1.0, "Float64"),
        ("S1", b"x", "String"),
        ("U1", "x", "String"),
    ],
)
def test_dmr_uses_explicit_dap4_type_map(dtype, value, expected_type):
    dataset = DatasetType("types")
    dataset["value"] = BaseType("value", data=np.array([value], dtype=dtype))

    body = b"".join(DMRResponse(dataset)).decode("ascii")

    assert '<{type} name="value">'.format(type=expected_type) in body


def test_dmr_emits_nested_groups_after_sibling_variables():
    dataset = dmr_to_dataset(load_dmr_file("data/dmrs/Nested_Group.dmr"))

    body = b"".join(DMRResponse(dataset)).decode("ascii")

    ET.fromstring(body)
    assert body.index('<Float64 name="root_variable">') < body.index(
        '<Group name="Group1">'
    )
    assert body.index('<Float64 name="group_1_var">') < body.index(
        '<Group name="subgroup1">'
    )
    assert '<Float64 name="subgroup1_var">' in body
    assert '<Attribute name="path"' not in body
    assert '<Attribute name="Maps"' not in body
