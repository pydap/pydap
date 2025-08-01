"""Test the DAP handler, which forms the core of the client."""

import os
import unittest

import numpy as np
import pytest
from requests.utils import urlparse
from webob.response import Response

import pydap.model
from pydap.handlers.dap import (
    UNPACKDAP4DATA,
    BaseProxyDap2,
    DAPHandler,
    SequenceProxy,
    decode_utf8_string_array,
    dmr_to_dataset,
    find_pattern_in_string_iter,
    walk,
)
from pydap.handlers.lib import BaseHandler, ConstraintExpression
from pydap.model import BaseType, DatasetType, GridType, StructureType
from pydap.tests.datasets import (
    SimpleArray,
    SimpleGrid,
    SimpleGroup,
    SimpleSequence,
    VerySimpleSequence,
)

from ..net import create_session

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch


class TestDapHandler(unittest.TestCase):
    """Test that the handler creates the correct dataset from a URL."""

    def setUp(self):
        """Create WSGI apps"""
        self.app1 = BaseHandler(SimpleGrid)
        self.app2 = BaseHandler(SimpleSequence)
        self.app3 = BaseHandler(SimpleGrid, gzip=True)
        self.app4 = BaseHandler(SimpleGroup)

    def test_grid(self):
        """Test that dataset has the correct data proxies for grids."""
        dataset = DAPHandler("http://localhost:8001/", self.app1).dataset

        self.assertEqual(list(dataset.keys()), ["SimpleGrid", "x", "y"])
        self.assertEqual(list(dataset.SimpleGrid.keys()), ["SimpleGrid", "x", "y"])

        # test one of the axis
        self.assertIsInstance(dataset.SimpleGrid.x.data, BaseProxyDap2)
        self.assertEqual(dataset.SimpleGrid.x.data.baseurl, "http://localhost:8001/")
        self.assertEqual(dataset.SimpleGrid.x.data.id, "SimpleGrid.x")
        self.assertEqual(dataset.SimpleGrid.x.data.dtype, np.dtype(">i4"))
        self.assertEqual(dataset.SimpleGrid.x.data.shape, (3,))
        self.assertEqual(dataset.SimpleGrid.x.data.slice, (slice(None),))

        # test the grid
        self.assertIsInstance(dataset.SimpleGrid.SimpleGrid.data, BaseProxyDap2)
        self.assertEqual(
            dataset.SimpleGrid.SimpleGrid.data.baseurl, "http://localhost:8001/"
        )
        self.assertEqual(dataset.SimpleGrid.SimpleGrid.data.id, "SimpleGrid.SimpleGrid")
        self.assertEqual(dataset.SimpleGrid.SimpleGrid.data.dtype, np.dtype(">i4"))
        self.assertEqual(dataset.SimpleGrid.SimpleGrid.data.shape, (2, 3))
        self.assertEqual(
            dataset.SimpleGrid.SimpleGrid.data.slice, (slice(None), slice(None))
        )
        self.assertEqual(
            repr(dataset.SimpleGrid[:]),
            "<GridType with array 'SimpleGrid' and maps 'x', 'y'>",
        )

    def test_grid_gzip(self):
        """Test that dataset has the correct data proxies for grids."""
        dataset = DAPHandler("http://localhost:8001/", self.app3).dataset

        self.assertEqual(list(dataset.keys()), ["SimpleGrid", "x", "y"])
        self.assertEqual(list(dataset.SimpleGrid.keys()), ["SimpleGrid", "x", "y"])

        # test one of the axis
        self.assertIsInstance(dataset.SimpleGrid.x.data, BaseProxyDap2)
        self.assertEqual(dataset.SimpleGrid.x.data.baseurl, "http://localhost:8001/")
        self.assertEqual(dataset.SimpleGrid.x.data.id, "SimpleGrid.x")
        self.assertEqual(dataset.SimpleGrid.x.data.dtype, np.dtype(">i4"))
        self.assertEqual(dataset.SimpleGrid.x.data.shape, (3,))
        self.assertEqual(dataset.SimpleGrid.x.data.slice, (slice(None),))

        # test the grid
        self.assertIsInstance(dataset.SimpleGrid.SimpleGrid.data, BaseProxyDap2)
        self.assertEqual(
            dataset.SimpleGrid.SimpleGrid.data.baseurl, "http://localhost:8001/"
        )
        self.assertEqual(dataset.SimpleGrid.SimpleGrid.data.id, "SimpleGrid.SimpleGrid")
        self.assertEqual(dataset.SimpleGrid.SimpleGrid.data.dtype, np.dtype(">i4"))
        self.assertEqual(dataset.SimpleGrid.SimpleGrid.data.shape, (2, 3))
        self.assertEqual(
            dataset.SimpleGrid.SimpleGrid.data.slice, (slice(None), slice(None))
        )
        self.assertEqual(
            repr(dataset.SimpleGrid[:]),
            "<GridType with array 'SimpleGrid' and maps 'x', 'y'>",
        )

    def test_grid_erddap(self):
        """Test that dataset has the correct data proxies for grids
        with the ERDDAP behavior."""
        with patch(
            "pydap.handlers.lib.degenerate_grid_to_structure", side_effect=(lambda x: x)
        ) as mock_degenerate:
            dataset = DAPHandler("http://localhost:8001/", self.app1).dataset
            self.assertEqual(
                repr(dataset.SimpleGrid[:]),
                "<GridType with array 'SimpleGrid' and maps 'x', 'y'>",
            )
            assert mock_degenerate.called

    def test_grid_output_grid_false(self):
        """Test that dataset has the correct data proxies for grids with
        option output_grid set to False."""
        dataset = DAPHandler(
            "http://localhost:8001/", self.app1, output_grid=False
        ).dataset

        self.assertEqual(list(dataset.keys()), ["SimpleGrid", "x", "y"])
        self.assertEqual(list(dataset.SimpleGrid.keys()), ["SimpleGrid", "x", "y"])

        # test one of the axis
        self.assertIsInstance(dataset.SimpleGrid.x.data, BaseProxyDap2)
        self.assertEqual(dataset.SimpleGrid.x.data.baseurl, "http://localhost:8001/")
        self.assertEqual(dataset.SimpleGrid.x.data.id, "SimpleGrid.x")
        self.assertEqual(dataset.SimpleGrid.x.data.dtype, np.dtype(">i4"))
        self.assertEqual(dataset.SimpleGrid.x.data.shape, (3,))
        self.assertEqual(dataset.SimpleGrid.x.data.slice, (slice(None),))

        # test the grid
        self.assertIsInstance(dataset.SimpleGrid.SimpleGrid.data, BaseProxyDap2)
        self.assertEqual(
            dataset.SimpleGrid.SimpleGrid.data.baseurl, "http://localhost:8001/"
        )
        self.assertEqual(dataset.SimpleGrid.SimpleGrid.data.id, "SimpleGrid.SimpleGrid")
        self.assertEqual(dataset.SimpleGrid.SimpleGrid.data.dtype, np.dtype(">i4"))
        self.assertEqual(dataset.SimpleGrid.SimpleGrid.data.shape, (2, 3))
        self.assertEqual(
            dataset.SimpleGrid.SimpleGrid.data.slice, (slice(None), slice(None))
        )
        np.testing.assert_array_equal(dataset.SimpleGrid[:], [[0, 1, 2], [3, 4, 5]])

    def test_grid_erddap_output_grid_false(self):
        """Test that dataset has the correct data proxies for grids with
        option output_grid set to False and with the ERDDAP behavior."""
        with patch(
            "pydap.handlers.lib.degenerate_grid_to_structure", side_effect=(lambda x: x)
        ) as mock_degenerate:
            dataset = DAPHandler(
                "http://localhost:8001/", self.app1, output_grid=False
            ).dataset
            np.testing.assert_array_equal(dataset.SimpleGrid[:], [[0, 1, 2], [3, 4, 5]])
            assert mock_degenerate.called

    def test_grid_with_projection(self):
        """Test that a sliced proxy can be created for grids."""
        dataset = DAPHandler("http://localhost:8001/?SimpleGrid[0]", self.app1).dataset

        self.assertEqual(dataset.SimpleGrid.x.data.shape, (1,))
        self.assertEqual(dataset.SimpleGrid.x.data.slice, (slice(0, 1, 1),))
        self.assertEqual(dataset.SimpleGrid.y.data.shape, (2,))
        self.assertEqual(dataset.SimpleGrid.y.data.slice, (slice(0, 3, 1),))
        self.assertEqual(dataset.SimpleGrid.SimpleGrid.data.shape, (1, 3))
        self.assertEqual(
            dataset.SimpleGrid.SimpleGrid.data.slice, (slice(0, 1, 1), slice(0, 3, 1))
        )

    def test_base_type_with_projection(self):
        """Test that a sliced proxy can be created for a base type."""
        dataset = DAPHandler("http://localhost:8001/?x[1:1:2]", self.app1).dataset

        self.assertEqual(dataset.x.data.shape, (2,))
        self.assertEqual(dataset.x.data.slice, (slice(1, 3, 1),))

    def test_grid_array_with_projection(self):
        """Test that a grid array can be properly pre sliced."""
        dataset = DAPHandler(
            "http://localhost:8001/?SimpleGrid.SimpleGrid[0]", self.app1
        ).dataset

        # object should be a structure, not a grid
        self.assertEqual(list(dataset.keys()), ["SimpleGrid"])
        self.assertNotIsInstance(dataset.SimpleGrid, GridType)
        self.assertIsInstance(dataset.SimpleGrid, StructureType)

        self.assertEqual(dataset.SimpleGrid.SimpleGrid.data.shape, (1, 3))
        self.assertEqual(
            dataset.SimpleGrid.SimpleGrid.data.slice, (slice(0, 1, 1), slice(0, 3, 1))
        )

    def test_grid_map_with_projection(self):
        """Test that a grid map can be properly pre sliced."""
        dataset = DAPHandler(
            "http://localhost:8001/?SimpleGrid.x[0]", self.app1
        ).dataset

        self.assertEqual(dataset.SimpleGrid.x.data.shape, (1,))
        self.assertEqual(dataset.SimpleGrid.x.data.slice, (slice(0, 1, 1),))

    def test_sequence(self):
        """Test that dataset has the correct data proxies for sequences."""
        dataset = DAPHandler("http://localhost:8001/", self.app2).dataset

        self.assertEqual(list(dataset.keys()), ["cast"])
        self.assertEqual(
            list(dataset.cast.keys()),
            [
                "id",
                "lon",
                "lat",
                "depth",
                "time",
                "temperature",
                "salinity",
                "pressure",
            ],
        )

        # check the sequence
        self.assertIsInstance(dataset.cast.data, SequenceProxy)
        self.assertEqual(dataset.cast.data.baseurl, "http://localhost:8001/")
        self.assertEqual(dataset.cast.data.id, "cast")
        self.assertEqual(dataset.cast.data.shape, ())
        self.assertEqual(dataset.cast.data.selection, [])
        self.assertEqual(dataset.cast.data.slice, (slice(None),))

        # check a child
        self.assertIsInstance(dataset.cast.lon.data, SequenceProxy)
        self.assertEqual(dataset.cast.lon.data.baseurl, "http://localhost:8001/")
        self.assertEqual(dataset.cast.lon.data.id, "cast.lon")
        self.assertEqual(dataset.cast.lon.data.shape, ())
        self.assertEqual(dataset.cast.lon.data.dtype, np.dtype(">i4"))
        self.assertEqual(dataset.cast.lon.data.selection, [])
        self.assertEqual(dataset.cast.lon.data.slice, (slice(None),))

    def test_sequence_with_projection(self):
        """Test projections applied to sequences."""
        dataset = DAPHandler("http://localhost:8001/?cast[1]", self.app2).dataset

        self.assertEqual(dataset.cast.data.slice, (slice(1, 2, 1),))
        self.assertEqual(
            [tuple(row) for row in dataset.cast.iterdata()],
            [("2", 200, 10, 500, 1, 15, 35, 100)],
        )

    def test_custom_timeout_BaseProxyDap2(self):
        dataset = DAPHandler("http://localhost:8001/", self.app1, timeout=300).dataset

        for var in walk(dataset, pydap.model.BaseType):
            assert var.data.timeout == 300

    def test_custom_timeout_SequenceProxy(self):
        dataset = DAPHandler("http://localhost:8001/", self.app2, timeout=300).dataset
        for var in walk(dataset, pydap.model.SequenceType):
            assert var.data.timeout == 300

    def test_custom_timeout_BaseProxyDap4(self):

        dataset = DAPHandler(
            "http://localhost:8001/", self.app4, timeout=300, protocol="dap4"
        ).dataset

        for var in walk(dataset, pydap.model.BaseType):
            assert var.data.timeout == 300


class TestBaseProxy(unittest.TestCase):
    """Test `BaseProxy` objects."""

    def setUp(self):
        """Create a WSGI app"""
        self.app = BaseHandler(SimpleArray)

        self.data = BaseProxyDap2(
            "http://localhost:8001/", "byte", np.dtype("B"), (5,), application=self.app
        )

    def test_repr(self):
        """Test the object representation."""
        self.assertEqual(
            repr(self.data),
            "BaseProxy('http://localhost:8001/', 'byte', "
            "dtype('uint8'), (5,), "
            "(slice(None, None, None),))",
        )

    def test_getitem(self):
        """Test the ``__getitem__`` method."""
        np.testing.assert_array_equal(self.data[:], np.arange(5))

    def test_getitem_out_of_bound(self):
        """
        Test the ``__getitem__`` method with out of bounds
        slices.
        The same result as numpy is expected.
        """
        np.testing.assert_array_equal(self.data[:10], np.arange(5)[:10])

    def test_inexact_division(self):
        """Test data retrieval when step > 1 and division inexact."""
        np.testing.assert_array_equal(self.data[0:3:2], np.arange(5)[0:3:2])

    def test_len(self):
        """Test length method."""
        self.assertEqual(len(self.data), 5)

    def test_iteration(self):
        """Test iteration."""
        self.assertEqual(list(iter(self.data)), list(range(5)))

    def test_comparisons(self):
        """Test all the comparisons."""
        np.testing.assert_array_equal(self.data == 2, np.arange(5) == 2)
        np.testing.assert_array_equal(self.data != 2, np.arange(5) != 2)
        np.testing.assert_array_equal(self.data >= 2, np.arange(5) >= 2)
        np.testing.assert_array_equal(self.data <= 2, np.arange(5) <= 2)
        np.testing.assert_array_equal(self.data > 2, np.arange(5) > 2)
        np.testing.assert_array_equal(self.data < 2, np.arange(5) < 2)


test_url = "http://test.opendap.org/opendap/data/nc/coads_climatology.nc"


@pytest.mark.parametrize(
    "url, app, expect",
    [
        ("dap2://test.opendap.org/opendap/data/nc/coads_climatology.nc", None, "dap2"),
        ("dap4://test.opendap.org/opendap/data/nc/coads_climatology.nc", None, "dap4"),
        (test_url, None, "warn"),
        (
            test_url + "?dap4.ce=/TIME",
            None,
            "dap4",
        ),
        ("a://test.opendap.org/opendap/data/nc/coads_climatology.nc", None, "error"),
        (" ", BaseHandler(SimpleGrid), "dap2"),
    ],
)
def test_protocols(url, app, expect):
    if app:
        assert DAPHandler(url=url, application=app).protocol == expect
    else:
        if expect == "error":
            with pytest.raises(TypeError):
                DAPHandler(url=url)
        elif expect == "warn":
            with pytest.warns(UserWarning):
                DAPHandler(url=url)
        else:
            assert DAPHandler(url=url).protocol == expect
    if urlparse(url).scheme in ["dap2", "dap4"]:
        assert DAPHandler(url=url).protocol == expect
        assert isinstance(DAPHandler(url=url).dataset, DatasetType)
    with pytest.raises(TypeError):
        # only protocol='dap2' or `dap4` is supported
        DAPHandler(url=url, application=app, protocol="errdap")


class TestBaseProxyShort(unittest.TestCase):
    """Test `BaseProxy` objects with short dtype."""

    def setUp(self):
        """Create a WSGI app with array data"""
        self.app = BaseHandler(SimpleArray)

        self.data = BaseProxyDap2(
            "http://localhost:8001/", "short", np.dtype(">h"), (), application=self.app
        )

    def test_getitem(self):
        """Test the ``__getitem__`` method."""
        np.testing.assert_array_equal(self.data[:], np.array(1))
        assert self.data[:].dtype.char == "h"


class TestBaseProxyString(unittest.TestCase):
    """Test a ``BaseProxy`` with string data."""

    def setUp(self):
        """Create a WSGI app with array data"""
        dataset = DatasetType("test")
        dataset["s"] = BaseType("s", np.array(["one", "two", "three"]))
        self.app = BaseHandler(dataset)

        self.data = BaseProxyDap2(
            "http://localhost:8001/", "s", np.dtype("|S5"), (3,), application=self.app
        )

    def test_getitem(self):
        """Test the ``__getitem__`` method."""
        np.testing.assert_array_equal(
            self.data[:], np.array(["one", "two", "three"], dtype="S")
        )


class TestSequenceProxy(unittest.TestCase):
    """Test that a ``SequenceProxy`` behaves like a Numpy structured array."""

    def setUp(self):
        """Create a WSGI app"""
        self.app = BaseHandler(VerySimpleSequence)
        self.local = VerySimpleSequence.sequence.data

        dataset = DAPHandler("http://localhost:8001/", self.app).dataset
        self.remote = dataset.sequence.data

    def test_repr(self):
        """Test the object representation."""
        self.assertEqual(
            repr(self.remote),
            "SequenceProxy('http://localhost:8001/', "
            "<SequenceType with children 'byte', 'int', 'float'>, [], "
            "(slice(None, None, None),))",
        )

    def test_attributes(self):
        """Test attributes of the remote sequence."""
        self.assertEqual(self.remote.baseurl, "http://localhost:8001/")
        self.assertEqual(self.remote.id, "sequence")
        self.assertEqual(list(self.remote.template.keys()), ["byte", "int", "float"])
        self.assertEqual(self.remote.selection, [])
        self.assertEqual(self.remote.slice, (slice(None),))

    def test_getitem(self):
        """Test modifications to the proxy object."""
        child = self.remote["int"]
        self.assertEqual(child.id, "sequence.int")
        self.assertEqual(child.template.dtype, np.dtype(">i4"))
        self.assertEqual(child.template.shape, ())

        print(self.remote)
        child = self.remote[["float", "int"]]
        print(child)
        self.assertEqual(child.id, "sequence.float,sequence.int")
        self.assertEqual(list(child.template.keys()), ["float", "int"])

        child = self.remote[0]
        self.assertEqual(child.slice, (slice(0, 1, 1),))

        child = self.remote[0:2]
        self.assertEqual(child.slice, (slice(0, 2, 1),))

    def test_url(self):
        """Test URL generation."""
        self.assertEqual(self.remote.url, "http://localhost:8001/.dods?sequence")
        self.assertEqual(
            self.remote["int"].url, "http://localhost:8001/.dods?sequence.int"
        )
        self.assertEqual(
            self.remote[["float", "int"]].url,
            "http://localhost:8001/.dods?sequence.float,sequence.int",
        )

    def test_iter(self):
        """Test iteration."""
        self.assertEqual(
            [tuple(row) for row in self.local],
            [
                (0, 1, 10.0),
                (1, 2, 20.0),
                (2, 3, 30.0),
                (3, 4, 40.0),
                (4, 5, 50.0),
                (5, 6, 60.0),
                (6, 7, 70.0),
                (7, 8, 80.0),
            ],
        )

        self.assertEqual(
            [tuple(row) for row in self.remote],
            [
                (0, 1, 10.0),
                (1, 2, 20.0),
                (2, 3, 30.0),
                (3, 4, 40.0),
                (4, 5, 50.0),
                (5, 6, 60.0),
                (6, 7, 70.0),
                (7, 8, 80.0),
            ],
        )

    def test_iter_child(self):
        """Test iteration over a child."""
        child = self.local["byte"]
        self.assertEqual(list(child), [0, 1, 2, 3, 4, 5, 6, 7])

        child = self.remote["byte"]
        self.assertEqual(list(child), [0, 1, 2, 3, 4, 5, 6, 7])

    def test_iter_find_pattern(self):
        pattern = b"Data:\n"
        # Check in a simple iteration:
        string_iter = iter([b"blahblah ", b"Data:\n", b"blahblahblah"])
        last_chunk = find_pattern_in_string_iter(pattern, string_iter)
        assert last_chunk == b""
        assert next(string_iter) == b"blahblahblah"

        # Check in a more complex iteration:
        string_iter = iter([b"blahblah Da", b"ta:\nblahb", b"lahblah"])
        last_chunk = find_pattern_in_string_iter(pattern, string_iter)
        assert last_chunk == b"blahb"
        assert next(string_iter) == b"lahblah"

        # Check for a character by character iteration:
        string_iter = iter(
            [
                b"b",
                b"l",
                b"a",
                b"h",
                b"b",
                b"l",
                b"a",
                b"h",
                b" ",
                b"D",
                b"a",
                b"t",
                b"a",
                b":",
                b"\n",
                b"b",
                b"l",
                b"a",
            ]
        )
        last_chunk = find_pattern_in_string_iter(pattern, string_iter)
        assert last_chunk == b""
        assert next(string_iter) == b"b"

    def test_comparisons(self):
        """Test lazy comparisons on the object."""
        filtered = self.remote[self.remote["byte"] == 4]
        self.assertEqual(filtered.selection, ["sequence.byte=4"])

        filtered = self.remote[self.remote["byte"] != 4]
        self.assertEqual(filtered.selection, ["sequence.byte!=4"])

        filtered = self.remote[self.remote["byte"] >= 4]
        self.assertEqual(filtered.selection, ["sequence.byte>=4"])

        filtered = self.remote[self.remote["byte"] <= 4]
        self.assertEqual(filtered.selection, ["sequence.byte<=4"])


class TestSequenceWithString(unittest.TestCase):

    def setUp(self):
        """Create a WSGI app"""
        self.app = BaseHandler(SimpleSequence)
        self.local = SimpleSequence.cast.data

        dataset = DAPHandler("http://localhost:8001/", self.app).dataset
        self.remote = dataset.cast.data

    def test_iter(self):
        """Test iteration."""
        self.assertEqual(
            [tuple(row) for row in self.local],
            [("1", 100, -10, 0, -1, 21, 35, 0), ("2", 200, 10, 500, 1, 15, 35, 100)],
        )

        self.assertEqual(
            [tuple(row) for row in self.remote],
            [("1", 100, -10, 0, -1, 21, 35, 0), ("2", 200, 10, 500, 1, 15, 35, 100)],
        )

    def test_projection(self):
        """Test if we can select only a few variables."""
        filtered = self.local[["salinity", "depth"]]
        self.assertEqual([tuple(row) for row in filtered], [(35, 0), (35, 500)])

        filtered = self.remote[["salinity", "depth"]]
        self.assertEqual([tuple(row) for row in filtered], [(35, 0), (35, 500)])

    def test_iter_child(self):
        """Test iteration over a child."""
        child = self.local["salinity"]
        self.assertEqual(list(child), [35, 35])

        child = self.remote["salinity"]
        self.assertEqual(list(child), [35, 35])

    def test_filtering(self):
        """Test filtering of data."""
        filtered = self.local[self.local["lon"] > 100]
        self.assertEqual(
            [tuple(row) for row in filtered], [("2", 200, 10, 500, 1, 15, 35, 100)]
        )

        filtered = self.remote[self.remote["lon"] > 100]
        self.assertEqual(
            [tuple(row) for row in filtered], [("2", 200, 10, 500, 1, 15, 35, 100)]
        )

        # filtering works because we store comparisons as lazy objects
        self.assertIsInstance(self.remote["lon"] > 100, ConstraintExpression)
        self.assertEqual(filtered.selection, ["cast.lon>100"])


class TestStringBaseType(unittest.TestCase):
    """Regression test for string base type."""

    def setUp(self):
        """Create a WSGI app with array data"""
        dataset = DatasetType("test")
        data = np.array("This is a test", dtype="S")
        dataset["s"] = BaseType("s", data)
        self.app = BaseHandler(dataset)

        self.data = BaseProxyDap2(
            "http://localhost:8001/", "s", np.dtype("|S14"), (), application=self.app
        )

    def test_getitem(self):
        """Test the ``__getitem__`` method."""
        np.testing.assert_array_equal(self.data[:], "This is a test")


class TestArrayStringBaseType(unittest.TestCase):
    """Regression test for an array of unicode base type."""

    def setUp(self):
        """Create a WSGI app with array data"""
        dataset = DatasetType("test")
        self.original_data = np.array([["This ", "is "], ["a ", "test"]], dtype="|S4")
        dataset["s"] = BaseType("s", self.original_data)
        self.app = BaseHandler(dataset)

        self.data = DAPHandler("http://localhost:8001/", self.app).dataset.s

    def test_getitem(self):
        """Test the ``__getitem__`` method."""
        np.testing.assert_array_equal(self.data[:].data, self.original_data)


class TestUnpackDap4Data(unittest.TestCase):
    """
    Tests some properties of the class UNPACKDAP4DATA.
    """

    def setUp(self):
        file_path = "data/daps/coads_climatology.nc.dap"
        abs_path = os.path.join(os.path.dirname(__file__), file_path)
        with open(abs_path, "rb") as f:
            self.unpacker = UNPACKDAP4DATA(f)

    def testEndian(self):
        """test the endianness of the first chunk encoded within the dap file"""
        endian = self.unpacker.endianness
        self.assertEqual(endian, "<")

    def testDMR(self):
        ds = dmr_to_dataset(self.unpacker.dmr)
        self.assertEqual(
            ds.variables(),
            {"SST": {"dtype": np.dtype(">f4"), "shape": (1, 4, 4), "dims": []}},
        )

    def testResponse(self):
        self.assertIsInstance(self.unpacker.r, Response)


buffer1 = bytearray(
    b"\x04\x00\x00\x00\x00\x00\x00\x00"
    + b"This"
    + b"\x02\x00\x00\x00\x00\x00\x00\x00"
    + b"is"
    + b"\x01\x00\x00\x00\x00\x00\x00\x00"
    + b"a"
    + b"\x04\x00\x00\x00\x00\x00\x00\x00"
    + b"Test"
)

buffer2 = bytearray(b"\x16\x00\x00\x00\x00\x00\x00\x00" + b"This is a string")


@pytest.mark.parametrize(
    "data, expected",
    [
        (buffer1, ["This", "is", "a", "Test"]),
        (buffer2, ["This is a string"]),
    ],
)
def test_decode_utf8_string_array(data, expected):
    result = decode_utf8_string_array(data)
    assert result == expected


def test_dap_handler_string_array():
    """Tests that the DAPHandler can handle a string array."""
    url = "dap4://test.opendap.org/opendap/data/nc/bears.nc"
    pyds = DAPHandler(url).dataset

    # this is what the data should be.
    actual_data = np.array(
        [[b"ind", b"ist", b"ing"], [b"uis", b"hab", b"le"]], dtype="|S3"
    )

    assert (
        repr(pyds["bears"][:]) == "<BaseType with data array(shape=(2, 3), dtype=|S3)>"
    )
    np.testing.assert_equal(pyds["bears"][:].data, actual_data)


@pytest.mark.parametrize("checksum", [True, False])
def test_checksum(checksum):
    """Test that the checksum if applied correctly, when requests"""
    url = "dap4://test.opendap.org/opendap/dap4/SimpleGroup.nc4.h5"
    session = create_session()
    pyds = DAPHandler(url, session=session, checksum=checksum).dataset
    Y = pyds["SimpleGroup/Y"][:]
    if not checksum:
        assert not hasattr(Y, "_DAP4_Checksum_CRC32")
    else:
        import zlib

        for var in walk(pyds, BaseType):
            assert hasattr(var[:], "_DAP4_Checksum_CRC32")
            buffer = bytearray(var[:].data)
            checksum = zlib.crc32(buffer)
            assert var[:].attributes["_DAP4_Checksum_CRC32"] == checksum
