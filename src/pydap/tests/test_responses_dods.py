"""Test the DODS response."""

import copy

import numpy as np
from webtest import TestApp
from webob.headers import ResponseHeaders

from pydap.lib import START_OF_SEQUENCE, END_OF_SEQUENCE, __version__
from pydap.handlers.lib import BaseHandler
from pydap.tests.datasets import (
    VerySimpleSequence, SimpleSequence, SimpleGrid,
    SimpleArray, NestedSequence)
from pydap.responses.dods import dods, DODSResponse
import unittest


class TestDODSResponse(unittest.TestCase):

    """Test the DODS response."""

    def setUp(self):
        """Create a simple WSGI app."""
        app = TestApp(BaseHandler(VerySimpleSequence))
        self.res = app.get('/.dods')

    def test_dispatcher(self):
        """Test that the dispatcher works on any object."""
        with self.assertRaises(StopIteration):
            dods(None)

    def test_status(self):
        """Test the status code."""
        self.assertEqual(self.res.status, "200 OK")

    def test_content_type(self):
        """Test the content type."""
        self.assertEqual(self.res.content_type, "application/octet-stream")

    def test_charset(self):
        """Test the charset."""
        self.assertEqual(self.res.charset, None)

    def test_headers(self):
        """Test the headers in the response."""
        self.assertEqual(
            self.res.headers,
            ResponseHeaders([
                ('XDODS-Server', 'pydap/' + __version__),
                ('Content-description', 'dods_data'),
                ('Content-type', 'application/octet-stream'),
                ('Access-Control-Allow-Origin', '*'),
                ('Access-Control-Allow-Headers',
                    'Origin, X-Requested-With, Content-Type'),
                ('Content-Length', '238')
            ]))

    def test_body(self):
        """Test response body."""
        dds, xdrdata = self.res.body.split(b'\nData:\n', 1)
        dds = dds.decode('ascii')
        self.assertEqual(dds, """Dataset {
    Sequence {
        Byte byte;
        Int32 int;
        Float32 float;
    } sequence;
} VerySimpleSequence;""")

        self.assertEqual(
            xdrdata,
            START_OF_SEQUENCE +
            b"\x00" b"\x00\x00\x00\x01" b"A \x00\x00" +
            START_OF_SEQUENCE +
            b"\x01" b"\x00\x00\x00\x02" b"A\xa0\x00\x00" +
            START_OF_SEQUENCE +
            b"\x02" b"\x00\x00\x00\x03" b"A\xf0\x00\x00" +
            START_OF_SEQUENCE +
            b"\x03" b"\x00\x00\x00\x04" b"B \x00\x00" +
            START_OF_SEQUENCE +
            b"\x04" b"\x00\x00\x00\x05" b"BH\x00\x00" +
            START_OF_SEQUENCE +
            b"\x05" b"\x00\x00\x00\x06" b"Bp\x00\x00" +
            START_OF_SEQUENCE +
            b"\x06" b"\x00\x00\x00\x07" b"B\x8c\x00\x00" +
            START_OF_SEQUENCE +
            b"\x07" b"\x00\x00\x00\x08" b"B\xa0\x00\x00" +
            END_OF_SEQUENCE)


class TestDODSResponseGrid(unittest.TestCase):

    """Test the DODS response with a grid."""

    def setUp(self):
        """Create a simple WSGI app."""
        app = TestApp(BaseHandler(SimpleGrid))
        self.res = app.get('/.dods')

    def test_body(self):
        """Test the response body."""
        dds, xdrdata = self.res.body.split(b'\nData:\n', 1)
        dds = dds.decode('ascii')
        self.assertEqual(dds, """Dataset {
    Grid {
        Array:
            Int32 SimpleGrid[y = 2][x = 3];
        Maps:
            Int32 x[x = 3];
            Int32 y[y = 2];
    } SimpleGrid;
    Int32 x[x = 3];
    Int32 y[y = 2];
} SimpleGrid;""")

        self.assertEqual(
            xdrdata,
            b"\x00\x00\x00\x06"  # length
            b"\x00\x00\x00\x06"  # length, again
            b"\x00\x00\x00\x00"
            b"\x00\x00\x00\x01"
            b"\x00\x00\x00\x02"
            b"\x00\x00\x00\x03"
            b"\x00\x00\x00\x04"
            b"\x00\x00\x00\x05"

            b"\x00\x00\x00\x03"
            b"\x00\x00\x00\x03"
            b"\x00\x00\x00\x00"
            b"\x00\x00\x00\x01"
            b"\x00\x00\x00\x02"

            b"\x00\x00\x00\x02"
            b"\x00\x00\x00\x02"
            b"\x00\x00\x00\x00"
            b"\x00\x00\x00\x01"

            b"\x00\x00\x00\x03"
            b"\x00\x00\x00\x03"
            b"\x00\x00\x00\x00"
            b"\x00\x00\x00\x01"
            b"\x00\x00\x00\x02"

            b"\x00\x00\x00\x02"
            b"\x00\x00\x00\x02"
            b"\x00\x00\x00\x00"
            b"\x00\x00\x00\x01")


class TestDODSResponseSequence(unittest.TestCase):

    """Test the DODS response with a sequence that has a string."""

    def setUp(self):
        """Create a simple WSGI app."""
        app = TestApp(BaseHandler(SimpleSequence))
        self.res = app.get('/.dods?cast.id,cast.lon')

    def test_body(self):
        """Test response body."""
        dds, xdrdata = self.res.body.split(b'\nData:\n', 1)
        dds = dds.decode('ascii')
        self.assertEqual(dds, """Dataset {
    Sequence {
        String id;
        Int32 lon;
    } cast;
} SimpleSequence;""")

        self.assertEqual(
            xdrdata,
            START_OF_SEQUENCE +
            b"\x00\x00\x00\x01"   # length of the string (=1)
            b"1\x00\x00\x00"      # string zero-paddded to 4 bytes
            b"\x00\x00\x00d" +  # lon
            START_OF_SEQUENCE +
            b"\x00\x00\x00\x01"
            b"2\x00\x00\x00"
            b"\x00\x00\x00\xc8" +
            END_OF_SEQUENCE)


class TestDODSResponseArray(unittest.TestCase):

    """Test the DODS response with arrays of bytes and strings."""

    def setUp(self):
        """Create a simple WSGI app."""
        self.app = TestApp(BaseHandler(SimpleArray))

    def test_body(self):
        """Test response body."""
        res = self.app.get("/.dods")
        dds, xdrdata = res.body.split(b'\nData:\n', 1)
        dds = dds.decode('ascii')
        self.assertEqual(dds, """Dataset {
    Byte byte[byte = 5];
    String string[string = 2];
    Int16 short;
} SimpleArray;""")

        self.assertEqual(
            xdrdata,
            b"\x00\x00\x00\x05"   # length of the byte array
            b"\x00\x00\x00\x05"   # length, again
            b"\x00"
            b"\x01"
            b"\x02"
            b"\x03"
            b"\x04"
            b"\x00\x00\x00"       # zero-padding to 4 bytes

            b"\x00\x00\x00\x02"   # length of the array, only once (string)
            b"\x00\x00\x00\x03"   # length of the first string
            b"one\x00"            # string padded to 4 bytes
            b"\x00\x00\x00\x03"
            b"two\x00"

            b"\x00\x00\x00\x01")  # shorts are encoded in 4 bytes

    def test_calculate_size_short(self):
        """Test that size is calculated correctly with shorts."""
        res = self.app.get("/.dods?short")
        self.assertEqual(res.headers["content-length"], "52")


class TestDODSResponseArrayterator(unittest.TestCase):

    """Test the DODS response when encountering an Arrayterator.

    In several cases the DODS response will work on an Arrayterator, which is
    a wrapper over arrays that allows iteration over them in blocks, instead of
    reading everything into memory.

    """

    def test_grid(self):
        """Test a grid."""
        modified = copy.copy(SimpleGrid)
        modified.SimpleGrid.SimpleGrid.data = np.lib.arrayterator.Arrayterator(
            modified.SimpleGrid.SimpleGrid.data, 2)

        app = TestApp(BaseHandler(modified))
        res = app.get("/.dods?SimpleGrid.SimpleGrid")
        header_string = b"""Dataset {
    Structure {
        Int32 SimpleGrid[y = 2][x = 3];
    } SimpleGrid;
} SimpleGrid;
Data:
"""
        self.assertEqual(res.body, (header_string +
                                    b"\x00\x00\x00\x06"
                                    b"\x00\x00\x00\x06"
                                    b"\x00\x00\x00\x00"
                                    b"\x00\x00\x00\x01"
                                    b"\x00\x00\x00\x02"
                                    b"\x00\x00\x00\x03"
                                    b"\x00\x00\x00\x04"
                                    b"\x00\x00\x00\x05"))


class TestDODSResponseNestedSequence(unittest.TestCase):

    """Test the DODS response with nested sequences."""

    def test_iteration(self):
        """Test direct iteration over data."""
        response = DODSResponse(NestedSequence)
        output = b"".join(response)
        self.assertEqual(
            output, b"""Dataset {
    Sequence {
        Int32 lat;
        Int32 lon;
        Int32 elev;
        Sequence {
            Int32 time;
            Int32 slp;
            Int32 wind;
        } time_series;
    } location;
} NestedSequence;
Data:
""" +
            START_OF_SEQUENCE +
            b"\x00\x00\x00\x01"
            b"\x00\x00\x00\x01"
            b"\x00\x00\x00\x01" +
            START_OF_SEQUENCE +
                    b"\x00\x00\x00\n"
                    b"\x00\x00\x00\x0b"
                    b"\x00\x00\x00\x0c" +
            START_OF_SEQUENCE +
                    b"\x00\x00\x00\x15"
                    b"\x00\x00\x00\x16"
                    b"\x00\x00\x00\x17" +
            END_OF_SEQUENCE +
            START_OF_SEQUENCE +
                    b"\x00\x00\x00\x02"
                    b"\x00\x00\x00\x04"
                    b"\x00\x00\x00\x04" +
            START_OF_SEQUENCE +
                    b"\x00\x00\x00\x0f"
                    b"\x00\x00\x00\x10"
                    b"\x00\x00\x00\x11" +
            END_OF_SEQUENCE +
            START_OF_SEQUENCE +
                    b"\x00\x00\x00\x03"
                    b"\x00\x00\x00\x06"
                    b"\x00\x00\x00\t" +
            START_OF_SEQUENCE +
                    b"\x00\x00\x00\x04"
                    b"\x00\x00\x00\x08"
                    b"\x00\x00\x00\x10" +
                    START_OF_SEQUENCE +
                    b"\x00\x00\x00\x1f"
                    b"\x00\x00\x00 "
                    b"\x00\x00\x00!" +
                    START_OF_SEQUENCE +
                    b"\x00\x00\x00)"
                    b"\x00\x00\x00*"
                    b"\x00\x00\x00+" +
                    START_OF_SEQUENCE +
                    b"\x00\x00\x003"
                    b"\x00\x00\x004"
                    b"\x00\x00\x005" +
                    START_OF_SEQUENCE +
                    b"\x00\x00\x00="
                    b"\x00\x00\x00>"
                    b"\x00\x00\x00?" +
                    END_OF_SEQUENCE +
            END_OF_SEQUENCE)

    def test_body(self):
        """Test response body."""
        app = TestApp(BaseHandler(NestedSequence))
        res = app.get("/.dods")
        dds, xdrdata = res.body.split(b'\nData:\n', 1)
        dds = dds.decode('ascii')
        self.assertEqual(dds, """Dataset {
    Sequence {
        Int32 lat;
        Int32 lon;
        Int32 elev;
        Sequence {
            Int32 time;
            Int32 slp;
            Int32 wind;
        } time_series;
    } location;
} NestedSequence;""")

        self.assertEqual(
            xdrdata,
            START_OF_SEQUENCE +
            b"\x00\x00\x00\x01"
            b"\x00\x00\x00\x01"
            b"\x00\x00\x00\x01" +
            START_OF_SEQUENCE +
            b"\x00\x00\x00\n"
            b"\x00\x00\x00\x0b"
            b"\x00\x00\x00\x0c" +
            START_OF_SEQUENCE +
            b"\x00\x00\x00\x15"
            b"\x00\x00\x00\x16"
            b"\x00\x00\x00\x17" +
            END_OF_SEQUENCE +
            START_OF_SEQUENCE +
            b"\x00\x00\x00\x02"
            b"\x00\x00\x00\x04"
            b"\x00\x00\x00\x04" +
            START_OF_SEQUENCE +
            b"\x00\x00\x00\x0f"
            b"\x00\x00\x00\x10"
            b"\x00\x00\x00\x11" +
            END_OF_SEQUENCE +
            START_OF_SEQUENCE +
            b"\x00\x00\x00\x03"
            b"\x00\x00\x00\x06"
            b"\x00\x00\x00\t" +
            START_OF_SEQUENCE +
            b"\x00\x00\x00\x04"
            b"\x00\x00\x00\x08"
            b"\x00\x00\x00\x10" +
            START_OF_SEQUENCE +
            b"\x00\x00\x00\x1f"
            b"\x00\x00\x00 "
            b"\x00\x00\x00!" +
            START_OF_SEQUENCE +
            b"\x00\x00\x00)"
            b"\x00\x00\x00*"
            b"\x00\x00\x00+" +
            START_OF_SEQUENCE +
            b"\x00\x00\x003"
            b"\x00\x00\x004"
            b"\x00\x00\x005" +
            START_OF_SEQUENCE +
            b"\x00\x00\x00="
            b"\x00\x00\x00>"
            b"\x00\x00\x00?" +
            END_OF_SEQUENCE +
            END_OF_SEQUENCE)
