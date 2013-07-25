"""Test the DODS response."""

import sys
import copy
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

import numpy as np
from webtest import TestApp
from webob.headers import ResponseHeaders

from pydap.handlers.lib import BaseHandler
from pydap.tests.datasets import (
    VerySimpleSequence, SimpleSequence, SimpleGrid,
    SimpleArray, NestedSequence)
from pydap.responses.dods import dods


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
                ('XDODS-Server', 'pydap/3.2'),
                ('Content-description', 'dods_data'),
                ('Content-type', 'application/octet-stream'),
                ('Access-Control-Allow-Origin', '*'),
                ('Access-Control-Allow-Headers',
                    'Origin, X-Requested-With, Content-Type'),
                ('Content-Length', '238')
            ]))

    def test_body(self):
        """Test response body."""
        dds, xdrdata = self.res.body.split('\nData:\n', 1)
        self.assertEqual(dds, """Dataset {
    Sequence {
        Byte byte;
        Int32 int;
        Float32 float;
    } sequence;
} VerySimpleSequence;""")

        output = xdrdata.replace('\x5a\x00\x00\x00', '<start of sequence>')
        output = output.replace('\xa5\x00\x00\x00', '<end of sequence>')
        self.assertEqual(
            output,
            "<start of sequence>"
            "\x00" "\x00\x00\x00\x01" "A \x00\x00"
            "<start of sequence>"
            "\x01" "\x00\x00\x00\x02" "A\xa0\x00\x00"
            "<start of sequence>"
            "\x02" "\x00\x00\x00\x03" "A\xf0\x00\x00"
            "<start of sequence>"
            "\x03" "\x00\x00\x00\x04" "B \x00\x00"
            "<start of sequence>"
            "\x04" "\x00\x00\x00\x05" "BH\x00\x00"
            "<start of sequence>"
            "\x05" "\x00\x00\x00\x06" "Bp\x00\x00"
            "<start of sequence>"
            "\x06" "\x00\x00\x00\x07" "B\x8c\x00\x00"
            "<start of sequence>"
            "\x07" "\x00\x00\x00\x08" "B\xa0\x00\x00"
            "<end of sequence>")


class TestDODSResponseGrid(unittest.TestCase):

    """Test the DODS response with a grid."""

    def setUp(self):
        """Create a simple WSGI app."""
        app = TestApp(BaseHandler(SimpleGrid))
        self.res = app.get('/.dods')

    def test_body(self):
        """Test the response body."""
        dds, xdrdata = self.res.body.split('\nData:\n', 1)
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
            "\x00\x00\x00\x06"  # length
            "\x00\x00\x00\x06"  # length, again
            "\x00\x00\x00\x00"
            "\x00\x00\x00\x01"
            "\x00\x00\x00\x02"
            "\x00\x00\x00\x03"
            "\x00\x00\x00\x04"
            "\x00\x00\x00\x05"

            "\x00\x00\x00\x03"
            "\x00\x00\x00\x03"
            "\x00\x00\x00\x00"
            "\x00\x00\x00\x01"
            "\x00\x00\x00\x02"

            "\x00\x00\x00\x02"
            "\x00\x00\x00\x02"
            "\x00\x00\x00\x00"
            "\x00\x00\x00\x01"

            "\x00\x00\x00\x03"
            "\x00\x00\x00\x03"
            "\x00\x00\x00\x00"
            "\x00\x00\x00\x01"
            "\x00\x00\x00\x02"

            "\x00\x00\x00\x02"
            "\x00\x00\x00\x02"
            "\x00\x00\x00\x00"
            "\x00\x00\x00\x01""")


class TestDODSResponseSequence(unittest.TestCase):

    """Test the DODS response with a sequence that has a string."""

    def setUp(self):
        """Create a simple WSGI app."""
        app = TestApp(BaseHandler(SimpleSequence))
        self.res = app.get('/.dods?cast.id,cast.lon')

    def test_body(self):
        """Test response body."""
        dds, xdrdata = self.res.body.split('\nData:\n', 1)
        self.assertEqual(dds, """Dataset {
    Sequence {
        String id;
        Int32 lon;
    } cast;
} SimpleSequence;""")

        output = xdrdata.replace('\x5a\x00\x00\x00', '<start of sequence>')
        output = output.replace('\xa5\x00\x00\x00', '<end of sequence>')
        self.assertEqual(
            output,
            "<start of sequence>"
            "\x00\x00\x00\x01"   # length of the string (=1)
            "1\x00\x00\x00"      # string zero-paddded to 4 bytes
            "\x00\x00\x00d"  # lon
            "<start of sequence>"
            "\x00\x00\x00\x01"
            "2\x00\x00\x00"
            "\x00\x00\x00\xc8"
            "<end of sequence>")


class TestDODSResponseArray(unittest.TestCase):

    """Test the DODS response with arrays of bytes and strings."""

    def setUp(self):
        """Create a simple WSGI app."""
        self.app = TestApp(BaseHandler(SimpleArray))

    def test_body(self):
        """Test response body."""
        res = self.app.get("/.dods")
        dds, xdrdata = res.body.split('\nData:\n', 1)
        self.assertEqual(dds, """Dataset {
    Byte byte[byte = 5];
    String string[string = 2];
    Int16 short;
} SimpleArray;""")

        self.assertEqual(
            xdrdata,
            "\x00\x00\x00\x05"   # length of the byte array
            "\x00\x00\x00\x05"   # length, again
            "\x00"
            "\x01"
            "\x02"
            "\x03"
            "\x04"
            "\x00\x00\x00"       # zero-padding to 4 bytes

            "\x00\x00\x00\x02"   # length of the array, only once (string)
            "\x00\x00\x00\x03"   # length of the first string
            "one\x00"            # string padded to 4 bytes
            "\x00\x00\x00\x03"
            "two\x00"

            "\x00\x00\x00\x01")  # shorts are encoded in 4 bytes

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
        self.assertEqual(res.body, """Dataset {
    Structure {
        Int32 SimpleGrid[y = 2][x = 3];
    } SimpleGrid;
} SimpleGrid;
Data:
"""
            "\x00\x00\x00\x06"
            "\x00\x00\x00\x06"
            "\x00\x00\x00\x00"
            "\x00\x00\x00\x01"
            "\x00\x00\x00\x02"
            "\x00\x00\x00\x03"
            "\x00\x00\x00\x04"
            "\x00\x00\x00\x05")


class TestDODSResponseNestedSequence(unittest.TestCase):

    """Test the DODS response with nested sequences."""

    def setUp(self):
        """Create the base WSGI app."""
        self.app = TestApp(BaseHandler(NestedSequence))

    def test_body(self):
        """Test response body."""
        res = self.app.get("/.dods")
        dds, xdrdata = res.body.split('\nData:\n', 1)
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

        output = xdrdata.replace('\x5a\x00\x00\x00', '<start of sequence>')
        output = output.replace('\xa5\x00\x00\x00', '<end of sequence>')
        self.assertEqual(
            output,
            "<start of sequence>"
                "\x00\x00\x00\x01"
                "\x00\x00\x00\x01"
                "\x00\x00\x00\x01"
                "<start of sequence>"
                    "\x00\x00\x00\n"
                    "\x00\x00\x00\x0b"
                    "\x00\x00\x00\x0c"
                "<start of sequence>"
                    "\x00\x00\x00\x15"
                    "\x00\x00\x00\x16"
                    "\x00\x00\x00\x17"
            "<end of sequence>"
            "<start of sequence>"
                "\x00\x00\x00\x02"
                "\x00\x00\x00\x04"
                "\x00\x00\x00\x04"
                "<start of sequence>"
                    "\x00\x00\x00\x0f"
                    "\x00\x00\x00\x10"
                    "\x00\x00\x00\x11"
            "<end of sequence>"
            "<start of sequence>"
                "\x00\x00\x00\x03"
                "\x00\x00\x00\x06"
                "\x00\x00\x00\t"
            "<start of sequence>"
                "\x00\x00\x00\x04"
                "\x00\x00\x00\x08"
                "\x00\x00\x00\x10"
                "<start of sequence>"
                    "\x00\x00\x00\x1f"
                    "\x00\x00\x00 "
                    "\x00\x00\x00!"
                "<start of sequence>"
                    "\x00\x00\x00)"
                    "\x00\x00\x00*"
                    "\x00\x00\x00+"
                "<start of sequence>"
                    "\x00\x00\x003"
                    "\x00\x00\x004"
                    "\x00\x00\x005"
                "<start of sequence>"
                    "\x00\x00\x00="
                    "\x00\x00\x00>"
                    "\x00\x00\x00?"
                "<end of sequence>"
            "<end of sequence>")
