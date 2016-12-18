"""Tests for the server-side function WSGI middleware."""

import sys
from six import next

from webtest import TestApp
import numpy as np

from pydap.model import SequenceType, BaseType
from pydap.handlers.lib import BaseHandler
from pydap.tests.datasets import SimpleSequence, SimpleGrid
from pydap.wsgi.ssf import ServerSideFunctions
from pydap.exceptions import ServerError
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest


class TestMiddleware(unittest.TestCase):

    """Tests for the server-side function middleware."""

    def test_das(self):
        """Test that DAS requests are ignored."""
        # create a simple app
        app = TestApp(ServerSideFunctions(BaseHandler(SimpleSequence)))

        # test a DAS response with a non-existing function
        app.get("/.das?non_existing_function(sequence)")

        # now test a DDS response
        with self.assertRaises(KeyError):
            app.get("/.dds?non_existing_function(sequence)")

    def test_no_parsed_response(self):
        """Test that non-parsed responses work or raise error.

        Pydap returns WSGI responses that contain the "parsed" dataset, so it
        can be manipulated by middleware.

        """
        app = TestApp(
            ServerSideFunctions(Accumulator(BaseHandler(SimpleGrid))))

        # a normal request should work, even though server-side functions are
        # not working in the WSGI pipeline
        app.get("/.dds")

        # this will fail, since it's impossible to build the response
        with self.assertRaises(ServerError):
            app.get("/.dds?mean(x)")

    def test_selection(self):
        """Test a selection server-side function."""
        app = TestApp(ServerSideFunctions(BaseHandler(SimpleSequence)))
        res = app.get(
            "/.asc?density(cast.salinity,cast.temperature,cast.pressure)>1025")
        self.assertEqual(res.text,
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
                         '"2", 200, 10, 500, 1, 15, 35, 100\n'
                         '\n')

    def test_operators(self):
        """Test different operators on selection using a dummy function."""
        app = TestApp(
            ServerSideFunctions(BaseHandler(SimpleSequence), double=double))
        res = app.get("/.asc?cast.lat&double(cast.lat)>10")
        self.assertEqual(res.text,
                         'Dataset {\n'
                         '    Sequence {\n'
                         '        Int32 lat;\n'
                         '    } cast;\n'
                         '} SimpleSequence;\n'
                         '---------------------------------------------\n'
                         'cast.lat\n'
                         '10\n'
                         '\n')

        res = app.get("/.asc?cast.lat&double(cast.lat)>=20")
        self.assertEqual(res.text,
                         'Dataset {\n'
                         '    Sequence {\n'
                         '        Int32 lat;\n'
                         '    } cast;\n'
                         '} SimpleSequence;\n'
                         '---------------------------------------------\n'
                         'cast.lat\n'
                         '10\n'
                         '\n')

        res = app.get("/.asc?cast.lat&double(cast.lat)<10")
        self.assertEqual(res.text,
                         'Dataset {\n'
                         '    Sequence {\n'
                         '        Int32 lat;\n'
                         '    } cast;\n'
                         '} SimpleSequence;\n'
                         '---------------------------------------------\n'
                         'cast.lat\n'
                         '-10\n'
                         '\n')

        res = app.get("/.asc?cast.lat&double(cast.lat)<=-20")
        self.assertEqual(res.text,
                         'Dataset {\n'
                         '    Sequence {\n'
                         '        Int32 lat;\n'
                         '    } cast;\n'
                         '} SimpleSequence;\n'
                         '---------------------------------------------\n'
                         'cast.lat\n'
                         '-10\n'
                         '\n')

        res = app.get("/.asc?cast.lat&double(cast.lat)=20")
        self.assertEqual(res.text,
                         'Dataset {\n'
                         '    Sequence {\n'
                         '        Int32 lat;\n'
                         '    } cast;\n'
                         '} SimpleSequence;\n'
                         '---------------------------------------------\n'
                         'cast.lat\n'
                         '10\n'
                         '\n')

        res = app.get("/.asc?cast.lat&double(cast.lat)!=20")
        self.assertEqual(res.text,
                         'Dataset {\n'
                         '    Sequence {\n'
                         '        Int32 lat;\n'
                         '    } cast;\n'
                         '} SimpleSequence;\n'
                         '---------------------------------------------\n'
                         'cast.lat\n'
                         '-10\n'
                         '\n')

    def test_selection_no_comparison(self):
        """Test function calls in the selection without comparison.

        Some functions, like ``bounds``, have no comparison. In this case, the
        selection is implicitely applied by comparing the result to 1.

        """
        app = TestApp(ServerSideFunctions(BaseHandler(SimpleSequence)))
        res = app.get("/.asc?cast.lat,cast.lon&"
                      "bounds(0,360,-90,0,0,500,00Z01JAN1900,00Z01JAN2000)")
        self.assertEqual(res.text,
                         'Dataset {\n'
                         '    Sequence {\n'
                         '        Int32 lat;\n'
                         '        Int32 lon;\n'
                         '    } cast;\n'
                         '} SimpleSequence;\n'
                         '---------------------------------------------\n'
                         'cast.lat, cast.lon\n'
                         '-10, 100\n'
                         '\n')

    def test_projection(self):
        """Test a simple function call on a projection."""
        app = TestApp(ServerSideFunctions(BaseHandler(SimpleGrid)))
        res = app.get("/.asc?mean(x)")
        self.assertEqual(res.text,
                         'Dataset {\n'
                         '    Float64 x;\n'
                         '} SimpleGrid;\n'
                         '---------------------------------------------\n'
                         'x\n'
                         '1\n')

    def test_projection_clash(self):
        """Test a function call creating a variable with a conflicting name."""
        app = TestApp(ServerSideFunctions(BaseHandler(SimpleGrid)))
        res = app.get("/.asc?mean(x),x")
        self.assertEqual(res.text,
                         'Dataset {\n'
                         '    Int32 x[x = 3];\n'
                         '} SimpleGrid;\n'
                         '---------------------------------------------\n'
                         'x\n'
                         '[0] 0\n'
                         '[1] 1\n'
                         '[2] 2\n'
                         '\n')

    def test_nested_projection(self):
        """Test a nested function call."""
        app = TestApp(ServerSideFunctions(BaseHandler(SimpleGrid)))
        res = app.get("/.asc?mean(mean(SimpleGrid.SimpleGrid,0),0)")
        self.assertEqual(res.text,
                         'Dataset {\n'
                         '    Float64 SimpleGrid;\n'
                         '} SimpleGrid;\n'
                         '---------------------------------------------\n'
                         'SimpleGrid\n'
                         '2.5\n')


class Accumulator(object):
    """A WSGI middleware that breaks streaming."""

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        return list(self.app(environ, start_response))


def double(dataset, var):
    """A dummy function that doubles a value.

    The value must be in a sequence. Return a new sequence with the value
    doubled.

    """
    # sequence is the first variable
    sequence = next(dataset.children())

    # get a single variable and double its value
    selection = sequence[var.name]
    rows = [(value*2,) for value in selection]

    # create output sequence
    out = SequenceType("result")
    out["double"] = BaseType("double")
    out.data = np.rec.fromrecords(rows, names=["double"])

    return out
