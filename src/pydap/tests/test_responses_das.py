"""Test the DAS response."""

from webtest import TestApp
from webob.headers import ResponseHeaders
from pydap.lib import __version__
from pydap.handlers.lib import BaseHandler
from pydap.tests.datasets import SimpleSequence, SimpleGrid, SimpleStructure
from pydap.responses.das import das

import unittest


class TestDASResponseSequence(unittest.TestCase):

    """Test the DAS response from a sequence."""

    def setUp(self):
        """Create a simple WSGI app."""
        app = TestApp(BaseHandler(SimpleSequence))
        self.res = app.get('/.das')

    def test_dispatcher(self):
        """Test the single dispatcher."""
        with self.assertRaises(StopIteration):
            das(None)

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
        """Test the response headers."""
        self.assertEqual(
            self.res.headers,
            ResponseHeaders([
                ('XDODS-Server', 'pydap/' + __version__),
                ('Content-description', 'dods_das'),
                ('Content-type', 'text/plain; charset=ascii'),
                ('Access-Control-Allow-Origin', '*'),
                ('Access-Control-Allow-Headers',
                    'Origin, X-Requested-With, Content-Type'),
                ('Content-Length', '510')]))

    def test_body(self):
        """Test the generated DAS response."""
        self.assertEqual(self.res.text, """Attributes {
    String description "A simple sequence for testing.";
    nested {
        Int32 value 42;
    }
    cast {
        id {
        }
        lon {
            String axis "X";
        }
        lat {
            String axis "Y";
        }
        depth {
            String axis "Z";
        }
        time {
            String axis "T";
            String units "days since 1970-01-01";
        }
        temperature {
        }
        salinity {
        }
        pressure {
        }
    }
}
""")


class TestDASResponseGrid(unittest.TestCase):

    """Test the DAS response from a grid."""

    def test_body(self):
        """Test the generated DAS response."""
        app = TestApp(BaseHandler(SimpleGrid))
        res = app.get('/.das')
        self.assertEqual(res.text, """Attributes {
    String description "A simple grid for testing.";
    SimpleGrid {
    }
    x {
        String axis "X";
        String units "degrees_east";
    }
    y {
        String axis "Y";
        String units "degrees_north";
    }
}
""")


class TestDASResponseStructure(unittest.TestCase):

    """The the DAS response from a structure."""

    def test_body(self):
        """Test the generated DAS response."""
        app = TestApp(BaseHandler(SimpleStructure))
        res = app.get('/.das')
        self.assertEqual(res.text, """Attributes {
    types {
        String key "value";
        nested {
            String string "bar";
            Int32 list 42, 43;
            Int32 array 1;
            Float64 float 1000;
        }
        b {
        }
        i32 {
        }
        ui32 {
        }
        i16 {
        }
        ui16 {
        }
        f32 {
        }
        f64 {
        }
        s {
        }
        u {
        }
    }
}
""")
