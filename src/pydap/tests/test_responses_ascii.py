"""Test ASCII response."""

import sys

from webtest import TestApp
from webob.headers import ResponseHeaders

from pydap.lib import __version__
from pydap.handlers.lib import BaseHandler
from pydap.tests.datasets import SimpleSequence, SimpleGrid
from pydap.responses.ascii import ascii

import unittest


class TestASCIIResponseSequence(unittest.TestCase):

    """Test ASCII response from a sequence."""

    def setUp(self):
        """Create a simple WSGI app for testing."""
        app = TestApp(BaseHandler(SimpleSequence))
        self.res = app.get('/.asc')

    def test_dispatcher(self):
        """Test the single dispatcher."""
        with self.assertRaises(StopIteration):
            ascii(None)

    def test_status(self):
        """Test the status code."""
        self.assertEqual(self.res.status, "200 OK")

    def test_content_type(self):
        """Test the content type."""
        self.assertEqual(self.res.content_type, "text/plain")

    def test_charset(self):
        """Test the charset."""
        self.assertEqual(self.res.charset, "ascii")

    def test_headers(self):
        """Test headers from the response."""
        self.assertEqual(
            self.res.headers,
            ResponseHeaders([
                ('XDODS-Server', 'pydap/' + __version__),
                ('Content-description', 'dods_ascii'),
                ('Content-type', 'text/plain; charset=ascii'),
                ('Content-Length', '440')]))

    def test_body(self):
        """Test the generated ASCII response."""
        self.assertEqual(self.res.text, """Dataset {
    Sequence {
        String id;
        Int32 lon;
        Int32 lat;
        Int32 depth;
        Int32 time;
        Int32 temperature;
        Int32 salinity;
        Int32 pressure;
    } cast;
} SimpleSequence;
---------------------------------------------
cast.id, cast.lon, cast.lat, cast.depth, cast.time, cast.temperature, cast.salinity, cast.pressure
"1", 100, -10, 0, -1, 21, 35, 0
"2", 200, 10, 500, 1, 15, 35, 100

""")


class TestASCIIResponseGrid(unittest.TestCase):

    """Test ASCII response from a grid."""

    def test_body(self):
        """Test the generated ASCII response."""
        app = TestApp(BaseHandler(SimpleGrid))
        res = app.get('/.asc')
        self.assertEqual(res.text, """Dataset {
    Grid {
        Array:
            Int32 SimpleGrid[y = 2][x = 3];
        Maps:
            Int32 x[x = 3];
            Int32 y[y = 2];
    } SimpleGrid;
    Int32 x[x = 3];
    Int32 y[y = 2];
} SimpleGrid;
---------------------------------------------
SimpleGrid.SimpleGrid
[0][0] 0
[0][1] 1
[0][2] 2
[1][0] 3
[1][1] 4
[1][2] 5

SimpleGrid.x
[0] 0
[1] 1
[2] 2

SimpleGrid.y
[0] 0
[1] 1


x
[0] 0
[1] 1
[2] 2

y
[0] 0
[1] 1

""")
