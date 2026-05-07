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
from pydap.tests.datasets import SimpleArray, SimpleGroup


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
        self.assertEqual(dataset["byte"].dtype, np.dtype("u1"))
        self.assertEqual(dataset["byte"].shape, (5,))
        self.assertEqual(dataset["string"].dtype, np.dtype("|S128"))
        self.assertEqual(dataset["string"].shape, (2,))


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
