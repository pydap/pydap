import unittest

from webtest import TestApp

from pydap.handlers.lib import BaseHandler
from pydap.tests.datasets import bounds, rain, ctd
from pydap.wsgi.ssf import ServerSideFunctions
from pydap.exceptions import ConstraintExpressionError


class TestWrongType(unittest.TestCase):
    def test_grid_to_bounds(self):
        app = TestApp(ServerSideFunctions(BaseHandler(rain)))
        with self.assertRaises(ConstraintExpressionError):
            res = app.get('/.dds?rain&bounds(0,360,-90,90,500,500,00Z01JAN1970,00Z01JAN1970)')

    def test_grid_to_density(self):
        app = TestApp(ServerSideFunctions(BaseHandler(rain)))
        with self.assertRaises(ConstraintExpressionError):
            res = app.get('/.dds?rain&density(rain,rain,rain)')

    def test_sequence_to_mean(self):
        app = TestApp(ServerSideFunctions(BaseHandler(bounds)))
        with self.assertRaises(ConstraintExpressionError):
            res = app.get('/.dds?mean(sequence)')


class TestNoParsedResponse(unittest.TestCase):
    def test_method(self):
        def wsgi_app(environ, start_response):
            start_response('200 OK', [('Content-type', 'text/plain')])
            return ['Hi!']
        app = TestApp(ServerSideFunctions(wsgi_app))
        self.assertEqual(app.get('/.dds').body, "Hi!")


class TestDensity(unittest.TestCase):
    def setUp(self):
        # create WSGI app
        self.app = TestApp(ServerSideFunctions(BaseHandler(ctd)))

    def test_plain(self):
        res = self.app.get('/.asc')
        self.assertEqual(res.body, """Dataset {
    Sequence {
        Int32 temperature;
        Int32 salinity;
        Int32 pressure;
    } cast;
} ctd;
---------------------------------------------
cast.temperature, cast.salinity, cast.pressure
21, 35, 0
15, 35, 100

""")

    def test_projection(self):
        res = self.app.get('/.asc?density(cast.salinity,cast.temperature,cast.pressure)')
        self.assertEqual(res.body, """Dataset {
    Sequence {
        Float64 rho;
    } result;
} ctd;
---------------------------------------------
result.rho
1024.37
1026.29

""")

    def test_selection(self):
        res = self.app.get('/.asc?cast.temperature&density(cast.salinity,cast.temperature,cast.pressure)>1025')
        self.assertEqual(res.body, """Dataset {
    Sequence {
        Int32 temperature;
    } cast;
} ctd;
---------------------------------------------
cast.temperature
15

""")


class TestBounds(unittest.TestCase):
    def setUp(self):
        # create WSGI app
        self.app = TestApp(ServerSideFunctions(BaseHandler(bounds)))

    def test_plain(self):
        res = self.app.get('/.asc')
        self.assertEqual(res.body, """Dataset {
    Sequence {
        Int32 lon;
        Int32 lat;
        Int32 depth;
        Int32 time;
        Int32 measurement;
    } sequence;
} test;
---------------------------------------------
sequence.lon, sequence.lat, sequence.depth, sequence.time, sequence.measurement
100, -10, 0, -1, 42
200, 10, 500, 1, 43

""")

    def test_default(self):
        res = self.app.get('/.asc?sequence&bounds(0,360,-90,90,0,500,00Z01JAN1970,00Z01JAN1970)')
        self.assertEqual(res.body, """Dataset {
    Sequence {
        Int32 lon;
        Int32 lat;
        Int32 depth;
        Int32 time;
        Int32 measurement;
    } sequence;
} test;
---------------------------------------------
sequence.lon, sequence.lat, sequence.depth, sequence.time, sequence.measurement

""")

    def test_selection_only(self):
        res = self.app.get('/.asc?bounds(0,360,-90,90,0,500,00Z01JAN1970,00Z01JAN1970)')
        self.assertEqual(res.body, """Dataset {
    Sequence {
        Int32 lon;
        Int32 lat;
        Int32 depth;
        Int32 time;
        Int32 measurement;
    } sequence;
} test;
---------------------------------------------
sequence.lon, sequence.lat, sequence.depth, sequence.time, sequence.measurement

""")

    def test_subset(self):
        res = self.app.get('/.asc?bounds(0,360,-90,90,0,500,00Z01JAN1970,00Z31JAN1970)')
        self.assertEqual(res.body, """Dataset {
    Sequence {
        Int32 lon;
        Int32 lat;
        Int32 depth;
        Int32 time;
        Int32 measurement;
    } sequence;
} test;
---------------------------------------------
sequence.lon, sequence.lat, sequence.depth, sequence.time, sequence.measurement
200, 10, 500, 1, 43

""")

    def test_subset_with_selection(self):
        res = self.app.get('/.asc?bounds(0,360,-90,90,0,500,00Z01JAN1969,00Z31JAN1970)&sequence.lat<0')
        self.assertEqual(res.body, """Dataset {
    Sequence {
        Int32 lon;
        Int32 lat;
        Int32 depth;
        Int32 time;
        Int32 measurement;
    } sequence;
} test;
---------------------------------------------
sequence.lon, sequence.lat, sequence.depth, sequence.time, sequence.measurement
100, -10, 0, -1, 42

""")

    def test_projection(self):
        res = self.app.get('/.asc?sequence.measurement&bounds(0,360,-90,90,0,500,00Z01JAN1970,00Z31JAN1970)')
        self.assertEqual(res.body, """Dataset {
    Sequence {
        Int32 measurement;
    } sequence;
} test;
---------------------------------------------
sequence.measurement
43

""")

    def test_point(self):
        res = self.app.get('/.asc?bounds(100,100,-10,-10,0,0,00Z31DEC1969,00Z31DEC1969)')
        self.assertEqual(res.body, """Dataset {
    Sequence {
        Int32 lon;
        Int32 lat;
        Int32 depth;
        Int32 time;
        Int32 measurement;
    } sequence;
} test;
---------------------------------------------
sequence.lon, sequence.lat, sequence.depth, sequence.time, sequence.measurement
100, -10, 0, -1, 42

""")

    def test_grads_step(self):
        modified = bounds.clone()
        modified.sequence.time.attributes['grads_step'] = '1mn'
        app = TestApp(ServerSideFunctions(BaseHandler(modified)))
        res = app.get('/.asc?sequence.measurement&bounds(0,360,-90,90,0,500,12Z01JAN1970,12Z01JAN1970)')
        self.assertEqual(res.body, """Dataset {
    Sequence {
        Int32 measurement;
    } sequence;
} test;
---------------------------------------------
sequence.measurement

""")

        modified.sequence.time.attributes['grads_step'] = '1hr'
        app = TestApp(ServerSideFunctions(BaseHandler(modified)))
        res = app.get('/.asc?sequence.measurement&bounds(0,360,-90,90,0,500,12Z01JAN1970,12Z01JAN1970)')
        self.assertEqual(res.body, """Dataset {
    Sequence {
        Int32 measurement;
    } sequence;
} test;
---------------------------------------------
sequence.measurement

""")

        modified.sequence.time.attributes['grads_step'] = '1dy'
        app = TestApp(ServerSideFunctions(BaseHandler(modified)))
        res = app.get('/.asc?sequence.measurement&bounds(0,360,-90,90,0,500,12Z01JAN1970,12Z01JAN1970)')
        self.assertEqual(res.body, """Dataset {
    Sequence {
        Int32 measurement;
    } sequence;
} test;
---------------------------------------------
sequence.measurement
43

""")

        modified.sequence.time.attributes['grads_step'] = '1mo'
        app = TestApp(ServerSideFunctions(BaseHandler(modified)))
        with self.assertRaises(NotImplementedError):
            res = app.get('/.asc?sequence.measurement&bounds(0,360,-90,90,0,500,12Z01JAN1970,12Z01JAN1970)')

        modified.sequence.time.attributes['grads_step'] = '1yr'
        app = TestApp(ServerSideFunctions(BaseHandler(modified)))
        with self.assertRaises(NotImplementedError):
            res = app.get('/.asc?sequence.measurement&bounds(0,360,-90,90,0,500,12Z01JAN1970,12Z01JAN1970)')
