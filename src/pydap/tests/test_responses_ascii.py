"""Test ASCII response."""

import sys
from webtest import TestApp
from webob.headers import ResponseHeaders
from pydap.lib import __version__
from pydap.handlers.lib import BaseHandler
from pydap.tests.datasets import SimpleSequence, SimpleGrid
from pydap.responses.ascii import ascii
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
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
        self.assertEqual(self.res.text,
                         'Dataset {\n'
                         '    Sequence {\n'
                         '        String id;\n'
                         '        Int32 lon;\n'
                         '        Int32 lat;\n'
                         '        Int32 depth;\n'
                         '        Int32 time;\n'
                         '        Int32 temperature;\n'
                         '        Int32 salinity;\n'
                         '        Int32 pressure;\n'
                         '    } cast;\n'
                         '} SimpleSequence;\n'
                         '---------------------------------------------\n'
                         'cast.id, cast.lon, cast.lat, cast.depth, cast.time, '
                         'cast.temperature, cast.salinity, cast.pressure\n'
                         '"1", 100, -10, 0, -1, 21, 35, 0\n'
                         '"2", 200, 10, 500, 1, 15, 35, 100\n'
                         '\n')


class TestASCIIResponseGrid(unittest.TestCase):

    """Test ASCII response from a grid."""

    def test_body(self):
        """Test the generated ASCII response."""
        app = TestApp(BaseHandler(SimpleGrid))
        res = app.get('/.asc')
        self.assertEqual(res.text,
                         'Dataset {\n'
                         '    Grid {\n'
                         '        Array:\n'
                         '            Int32 SimpleGrid[y = 2][x = 3];\n'
                         '        Maps:\n'
                         '            Int32 x[x = 3];\n'
                         '            Int32 y[y = 2];\n'
                         '    } SimpleGrid;\n'
                         '    Int32 x[x = 3];\n'
                         '    Int32 y[y = 2];\n'
                         '} SimpleGrid;\n'
                         '---------------------------------------------\n'
                         'SimpleGrid.SimpleGrid\n'
                         '[0][0] 0\n'
                         '[0][1] 1\n'
                         '[0][2] 2\n'
                         '[1][0] 3\n'
                         '[1][1] 4\n'
                         '[1][2] 5\n'
                         '\n'
                         'SimpleGrid.x\n'
                         '[0] 0\n'
                         '[1] 1\n'
                         '[2] 2\n'
                         '\n'
                         'SimpleGrid.y\n'
                         '[0] 0\n'
                         '[1] 1\n'
                         '\n'
                         '\n'
                         'x\n'
                         '[0] 0\n'
                         '[1] 1\n'
                         '[2] 2\n'
                         '\n'
                         'y\n'
                         '[0] 0\n'
                         '[1] 1\n'
                         '\n')
