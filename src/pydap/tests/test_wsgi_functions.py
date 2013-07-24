"""Test the server-side functions that come with Pydap."""

import sys
import copy
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

from webtest import TestApp

from pydap.handlers.lib import BaseHandler
from pydap.tests.datasets import SimpleSequence, SimpleGrid
from pydap.wsgi.ssf import ServerSideFunctions
from pydap.exceptions import ConstraintExpressionError, ServerError


class TestDensity(unittest.TestCase):

    """Test the density function."""

    def setUp(self):
        # create WSGI app
        self.app = TestApp(ServerSideFunctions(BaseHandler(SimpleSequence)))

    def test_wrong_type(self):
        app = TestApp(ServerSideFunctions(BaseHandler(SimpleGrid)))
        with self.assertRaises(ConstraintExpressionError):
            res = app.get('/.dds?density(SimpleGrid,SimpleGrid,SimpleGrid)')

    def test_plain(self):
        res = self.app.get('/.asc')
        self.assertEqual(res.body, """Dataset {
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

    def test_projection(self):
        res = self.app.get(
            '/.asc?density(cast.salinity,cast.temperature,cast.pressure)')
        self.assertEqual(res.body, """Dataset {
    Sequence {
        Float64 rho;
    } result;
} SimpleSequence;
---------------------------------------------
result.rho
1024.37
1026.29

""")

    def test_selection(self):
        res = self.app.get(
            '/.asc?cast.temperature&density(cast.salinity,cast.temperature,cast.pressure)>1025')
        self.assertEqual(res.body, """Dataset {
    Sequence {
        Int32 temperature;
    } cast;
} SimpleSequence;
---------------------------------------------
cast.temperature
15

""")


class TestBounds(unittest.TestCase):
    def setUp(self):
        # create WSGI app
        self.app = TestApp(ServerSideFunctions(BaseHandler(SimpleSequence)))

    def test_wrong_type(self):
        app = TestApp(ServerSideFunctions(BaseHandler(SimpleGrid)))
        with self.assertRaises(ConstraintExpressionError):
            res = app.get(
                '/.dds?SimpleGrid'
                '&bounds(0,360,-90,90,500,500,00Z01JAN1970,00Z01JAN1970)')

    def test_default(self):
        res = self.app.get(
            '/.asc?cast&bounds(0,360,-90,90,0,500,00Z01JAN1970,00Z01JAN1970)')
        self.assertEqual(res.body, """Dataset {
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

""")

    def test_selection_only(self):
        res = self.app.get(
            '/.asc?bounds(0,360,-90,90,0,500,00Z01JAN1970,00Z01JAN1970)')
        self.assertEqual(res.body, """Dataset {
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

""")

    def test_subset(self):
        res = self.app.get('/.asc?bounds(0,360,-90,90,0,500,00Z01JAN1970,00Z31JAN1970)')
        self.assertEqual(res.body, """Dataset {
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
"2", 200, 10, 500, 1, 15, 35, 100

""")

    def test_subset_with_selection(self):
        res = self.app.get('/.asc?bounds(0,360,-90,90,0,500,00Z01JAN1969,00Z31JAN1970)&cast.lat<0')
        self.assertEqual(res.body, """Dataset {
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

""")

    def test_projection(self):
        res = self.app.get('/.asc?cast.pressure&bounds(0,360,-90,90,0,500,00Z01JAN1970,00Z31JAN1970)')
        self.assertEqual(res.body, """Dataset {
    Sequence {
        Int32 pressure;
    } cast;
} SimpleSequence;
---------------------------------------------
cast.pressure
100

""")

    def test_point(self):
        res = self.app.get('/.asc?bounds(100,100,-10,-10,0,0,00Z31DEC1969,00Z31DEC1969)')
        self.assertEqual(res.body, """Dataset {
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

""")

    def test_grads_step(self):
        modified = copy.copy(SimpleSequence)
        modified.cast.time.attributes['grads_step'] = '1mn'
        app = TestApp(ServerSideFunctions(BaseHandler(modified)))
        res = app.get('/.asc?cast.pressure&bounds(0,360,-90,90,0,500,12Z01JAN1970,12Z01JAN1970)')
        self.assertEqual(res.body, """Dataset {
    Sequence {
        Int32 pressure;
    } cast;
} SimpleSequence;
---------------------------------------------
cast.pressure

""")

        modified.cast.time.attributes['grads_step'] = '1hr'
        app = TestApp(ServerSideFunctions(BaseHandler(modified)))
        res = app.get('/.asc?cast.pressure&bounds(0,360,-90,90,0,500,12Z01JAN1970,12Z01JAN1970)')
        self.assertEqual(res.body, """Dataset {
    Sequence {
        Int32 pressure;
    } cast;
} SimpleSequence;
---------------------------------------------
cast.pressure

""")

        modified.cast.time.attributes['grads_step'] = '1dy'
        app = TestApp(ServerSideFunctions(BaseHandler(modified)))
        res = app.get('/.asc?cast.pressure&bounds(0,360,-90,90,0,500,12Z01JAN1970,12Z01JAN1970)')
        self.assertEqual(res.body, """Dataset {
    Sequence {
        Int32 pressure;
    } cast;
} SimpleSequence;
---------------------------------------------
cast.pressure
100

""")

        modified.cast.time.attributes['grads_step'] = '1mo'
        app = TestApp(ServerSideFunctions(BaseHandler(modified)))
        with self.assertRaises(NotImplementedError):
            res = app.get('/.asc?cast.pressure&bounds(0,360,-90,90,0,500,12Z01JAN1970,12Z01JAN1970)')

        modified.cast.time.attributes['grads_step'] = '1yr'
        app = TestApp(ServerSideFunctions(BaseHandler(modified)))
        with self.assertRaises(NotImplementedError):
            res = app.get('/.asc?cast.pressure&bounds(0,360,-90,90,0,500,12Z01JAN1970,12Z01JAN1970)')

        modified.cast.time.attributes['grads_step'] = '1xx'
        app = TestApp(ServerSideFunctions(BaseHandler(modified)))
        with self.assertRaises(ServerError):
            res = app.get('/.asc?cast.pressure&bounds(0,360,-90,90,0,500,12Z01JAN1970,12Z01JAN1970)')


class TestMean(unittest.TestCase):
    def setUp(self):
        # create WSGI app
        self.app = TestApp(ServerSideFunctions(BaseHandler(SimpleGrid)))

    def test_wrong_type(self):
        app = TestApp(ServerSideFunctions(BaseHandler(SimpleSequence)))
        with self.assertRaises(ConstraintExpressionError):
            res = app.get('/.dds?mean(sequence)')
    
    def test_base_type(self):
        res = self.app.get("/.asc?mean(x)")
        self.assertEqual(res.body, """Dataset {
    Float64 x;
} SimpleGrid;
---------------------------------------------
x
1
""")

    def test_grid_type(self):
        res = self.app.get("/.asc?mean(SimpleGrid)")
        self.assertEqual(res.body, """Dataset {
    Grid {
        Array:
            Float64 SimpleGrid[y = 3];
        Maps:
            Int32 y[y = 2];
    } SimpleGrid;
} SimpleGrid;
---------------------------------------------
SimpleGrid.SimpleGrid
[0] 1.5
[1] 2.5
[2] 3.5

SimpleGrid.y
[0] 0
[1] 1


""")

    def test_nested(self):
        res = self.app.get("/.asc?mean(mean(SimpleGrid))")
        self.assertEqual(res.body, """Dataset {
    Grid {
        Array:
            Float64 SimpleGrid;
        Maps:
    } SimpleGrid;
} SimpleGrid;
---------------------------------------------
SimpleGrid.SimpleGrid
2.5

""")
