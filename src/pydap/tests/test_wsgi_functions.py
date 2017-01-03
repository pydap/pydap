"""Test the server-side functions that come with Pydap."""

import copy

from webtest import TestApp

from pydap.handlers.lib import BaseHandler
from pydap.tests.datasets import SimpleSequence, SimpleGrid
from pydap.wsgi.ssf import ServerSideFunctions
from pydap.exceptions import ConstraintExpressionError, ServerError

import unittest


class TestDensity(unittest.TestCase):

    """Test the density function."""

    def setUp(self):
        """Create simple WSGI app."""
        self.app = TestApp(ServerSideFunctions(BaseHandler(SimpleSequence)))

    def test_wrong_type(self):
        """Test passing the wrong type."""
        app = TestApp(ServerSideFunctions(BaseHandler(SimpleGrid)))
        with self.assertRaises(ConstraintExpressionError):
            app.get('/.dds?density(SimpleGrid,SimpleGrid,SimpleGrid)')

    def test_plain(self):
        """Test a direct request."""
        res = self.app.get('/.asc')
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
                         '"1", 100, -10, 0, -1, 21, 35, 0\n'
                         '"2", 200, 10, 500, 1, 15, 35, 100\n'
                         '\n')

    def test_projection(self):
        """Test using density as a projection."""
        res = self.app.get(
            '/.asc?density(cast.salinity,cast.temperature,cast.pressure)')
        self.assertEqual(res.text,
                         'Dataset {\n'
                         '    Sequence {\n'
                         '        Float64 rho;\n'
                         '    } result;\n'
                         '} SimpleSequence;\n'
                         '---------------------------------------------\n'
                         'result.rho\n'
                         '1024.37\n'
                         '1026.29\n'
                         '\n')

    def test_selection(self):
        """Test using density as a selection."""
        res = self.app.get(
            "/.asc?cast.temperature&"
            "density(cast.salinity,cast.temperature,cast.pressure)>1025")
        self.assertEqual(res.text,
                         'Dataset {\n'
                         '    Sequence {\n'
                         '        Int32 temperature;\n'
                         '    } cast;\n'
                         '} SimpleSequence;\n'
                         '---------------------------------------------\n'
                         'cast.temperature\n'
                         '15\n'
                         '\n')


class TestBounds(unittest.TestCase):

    """Test the ``bounds`` function, used by GrADS."""

    def setUp(self):
        """Create a simple WSGI app."""
        self.app = TestApp(ServerSideFunctions(BaseHandler(SimpleSequence)))

    def test_wrong_type(self):
        """Test passing a wrong type to the function."""
        app = TestApp(ServerSideFunctions(BaseHandler(SimpleGrid)))
        with self.assertRaises(ConstraintExpressionError):
            app.get('/.dds?SimpleGrid'
                    '&bounds(0,360,-90,90,500,500,00Z01JAN1970,00Z01JAN1970)')

    def test_default(self):
        """Test the default bounding box."""
        res = self.app.get('/.asc?cast&bounds(0,360,-90,90,0,500,'
                           '00Z01JAN1970,00Z01JAN1970)')
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
                         '\n')

    def test_selection_only(self):
        """Test using the function alone in the selection."""
        res = self.app.get('/.asc?bounds(0,360,-90,90,0,500,'
                           '00Z01JAN1970,00Z01JAN1970)')
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
                         '\n')

    def test_subset(self):
        """Test a requesting a subset of the data."""
        res = self.app.get('/.asc?bounds(0,360,-90,90,0,500,'
                           '00Z01JAN1970,00Z31JAN1970)')
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

    def test_subset_with_selection(self):
        """Test combining selections."""
        res = self.app.get("/.asc?"
                           "bounds(0,360,-90,90,0,500,"
                           "00Z01JAN1969,00Z31JAN1970)&cast.lat<0")
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
                         '"1", 100, -10, 0, -1, 21, 35, 0\n'
                         '\n')

    def test_projection(self):
        """Test bounds used as a projection."""
        res = self.app.get("/.asc?cast.pressure&"
                           "bounds(0,360,-90,90,0,500,"
                           "00Z01JAN1970,00Z31JAN1970)")
        self.assertEqual(res.text,
                         'Dataset {\n'
                         '    Sequence {\n'
                         '        Int32 pressure;\n'
                         '    } cast;\n'
                         '} SimpleSequence;\n'
                         '---------------------------------------------\n'
                         'cast.pressure\n'
                         '100\n'
                         '\n')

    def test_point(self):
        """Test a request for a point."""
        res = self.app.get("/.asc?bounds(100,100,-10,-10,0,0,"
                           "00Z31DEC1969,00Z31DEC1969)")
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
                         '"1", 100, -10, 0, -1, 21, 35, 0\n'
                         '\n')

    def test_grads_step(self):
        """Test different GrADS time steps."""
        modified = copy.copy(SimpleSequence)
        modified.cast.time.attributes['grads_step'] = '1mn'
        app = TestApp(ServerSideFunctions(BaseHandler(modified)))
        res = app.get("/.asc?cast.pressure&"
                      "bounds(0,360,-90,90,0,500,12Z01JAN1970,12Z01JAN1970)")
        self.assertEqual(res.text,
                         'Dataset {\n'
                         '    Sequence {\n'
                         '        Int32 pressure;\n'
                         '    } cast;\n'
                         '} SimpleSequence;\n'
                         '---------------------------------------------\n'
                         'cast.pressure\n'
                         '\n')

        modified.cast.time.attributes['grads_step'] = '1hr'
        app = TestApp(ServerSideFunctions(BaseHandler(modified)))
        res = app.get("/.asc?cast.pressure&"
                      "bounds(0,360,-90,90,0,500,12Z01JAN1970,12Z01JAN1970)")
        self.assertEqual(res.text,
                         'Dataset {\n'
                         '    Sequence {\n'
                         '        Int32 pressure;\n'
                         '    } cast;\n'
                         '} SimpleSequence;\n'
                         '---------------------------------------------\n'
                         'cast.pressure\n'
                         '\n')

        modified.cast.time.attributes['grads_step'] = '1dy'
        app = TestApp(ServerSideFunctions(BaseHandler(modified)))
        res = app.get("/.asc?cast.pressure&"
                      "bounds(0,360,-90,90,0,500,12Z01JAN1970,12Z01JAN1970)")
        self.assertEqual(res.text,
                         'Dataset {\n'
                         '    Sequence {\n'
                         '        Int32 pressure;\n'
                         '    } cast;\n'
                         '} SimpleSequence;\n'
                         '---------------------------------------------\n'
                         'cast.pressure\n'
                         '100\n'
                         '\n')

        modified.cast.time.attributes['grads_step'] = '1mo'
        app = TestApp(ServerSideFunctions(BaseHandler(modified)))
        with self.assertRaises(NotImplementedError):
            res = app.get("/.asc?cast.pressure&"
                          "bounds(0,360,-90,90,0,500,"
                          "12Z01JAN1970,12Z01JAN1970)")

        modified.cast.time.attributes['grads_step'] = '1yr'
        app = TestApp(ServerSideFunctions(BaseHandler(modified)))
        with self.assertRaises(NotImplementedError):
            res = app.get("/.asc?cast.pressure&"
                          "bounds(0,360,-90,90,0,500,"
                          "12Z01JAN1970,12Z01JAN1970)")

        modified.cast.time.attributes['grads_step'] = '1xx'
        app = TestApp(ServerSideFunctions(BaseHandler(modified)))
        with self.assertRaises(ServerError):
            res = app.get("/.asc?cast.pressure&"
                          "bounds(0,360,-90,90,0,500,"
                          "12Z01JAN1970,12Z01JAN1970)")


class TestMean(unittest.TestCase):

    """Test the ``mean`` function."""

    def setUp(self):
        """Create a simple WSGI app."""
        self.app = TestApp(ServerSideFunctions(BaseHandler(SimpleGrid)))

    def test_wrong_type(self):
        """Test passing a wrong type to mean function."""
        app = TestApp(ServerSideFunctions(BaseHandler(SimpleSequence)))
        with self.assertRaises(ConstraintExpressionError):
            app.get('/.dds?mean(sequence)')

    def test_base_type(self):
        """Test mean of base types."""
        res = self.app.get("/.asc?mean(x)")
        self.assertEqual(res.text,
                         'Dataset {\n'
                         '    Float64 x;\n'
                         '} SimpleGrid;\n'
                         '---------------------------------------------\n'
                         'x\n'
                         '1\n')

    def test_grid_type(self):
        """Test mean of grid objects."""
        res = self.app.get("/.asc?mean(SimpleGrid)")
        self.assertEqual(res.text,
                         'Dataset {\n'
                         '    Grid {\n'
                         '        Array:\n'
                         '            Float64 SimpleGrid[y = 3];\n'
                         '        Maps:\n'
                         '            Int32 y[y = 2];\n'
                         '    } SimpleGrid;\n'
                         '} SimpleGrid;\n'
                         '---------------------------------------------\n'
                         'SimpleGrid.SimpleGrid\n'
                         '[0] 1.5\n'
                         '[1] 2.5\n'
                         '[2] 3.5\n'
                         '\n'
                         'SimpleGrid.y\n'
                         '[0] 0\n'
                         '[1] 1\n'
                         '\n'
                         '\n')

    def test_nested(self):
        """Test nested function calls."""
        res = self.app.get("/.asc?mean(mean(SimpleGrid))")
        self.assertEqual(res.text,
                         'Dataset {\n'
                         '    Grid {\n'
                         '        Array:\n'
                         '            Float64 SimpleGrid;\n'
                         '        Maps:\n'
                         '    } SimpleGrid;\n'
                         '} SimpleGrid;\n'
                         '---------------------------------------------\n'
                         'SimpleGrid.SimpleGrid\n'
                         '2.5\n'
                         '\n')
