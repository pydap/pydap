"""Test the DDS response."""

from webtest import TestApp
from webob.headers import ResponseHeaders
from pydap.lib import __version__
from pydap.handlers.lib import BaseHandler
from pydap.tests.datasets import SimpleSequence, SimpleGrid, SimpleStructure
from pydap.responses.dds import dds
import unittest


class TestDDSResponseSequence(unittest.TestCase):
    """Test DDS response from sequences."""

    def setUp(self):
        """Create a simple WSGI app."""
        app = TestApp(BaseHandler(SimpleSequence))
        self.res = app.get('/.dds')

    def test_dispatcher(self):
        """Test the single dispatcher."""
        with self.assertRaises(StopIteration):
            dds(None)

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
        """Test the headers from the response."""
        self.assertEqual(
            self.res.headers,
            ResponseHeaders([
                ('XDODS-Server', 'pydap/' + __version__),
                ('Content-description', 'dods_dds'),
                ('Content-type', 'text/plain; charset=ascii'),
                ('Access-Control-Allow-Origin', '*'),
                ('Access-Control-Allow-Headers',
                    'Origin, X-Requested-With, Content-Type'),
                ('Content-Length', '228')]))

    def test_body(self):
        """Test the generated DDS response."""
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
""")


class TestDDSResponseGrid(unittest.TestCase):

    """Test DDS response from grids."""

    def test_body(self):
        """Test the generated DDS response."""
        app = TestApp(BaseHandler(SimpleGrid))
        res = app.get('/.dds')
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
""")


class TestDDSResponseStructure(unittest.TestCase):

    """Test DDS response from structures."""

    def test_body(self):
        """Test the generated DDS response."""
        app = TestApp(BaseHandler(SimpleStructure))
        res = app.get('/.dds')
        self.assertEqual(res.text, """Dataset {
    Structure {
        Byte b;
        Int32 i32;
        UInt32 ui32;
        Int16 i16;
        UInt16 ui16;
        Float32 f32;
        Float64 f64;
        String s;
        String u;
    } types;
} SimpleStructure;
""")
