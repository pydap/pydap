import unittest

import numpy as np
from webtest import TestApp
from webob.headers import ResponseHeaders

from pydap.model import *
from pydap.handlers.lib import BaseHandler
from pydap.handlers.dap import unpack_data
from pydap.tests.datasets import bounds, rain, SimpleStructure
from pydap.responses.dods import dods
from pydap.parsers.dds import build_dataset


class TestDODSResponseSequence(unittest.TestCase):
    def setUp(self):
        # create WSGI app
        app = TestApp(BaseHandler(bounds))
        self.res = app.get('/.dods')

    def test_dispatcher(self):
        with self.assertRaises(StopIteration):
            dods(None)

    def test_status(self):
        self.assertEqual(self.res.status, "200 OK")

    def test_content_type(self):
        self.assertEqual(self.res.content_type, "application/octet-stream")

    def test_charset(self):
        self.assertEqual(self.res.charset, None)

    def test_headers(self):
        self.assertEqual(self.res.headers,
            ResponseHeaders([
                ('XDODS-Server', 'pydap/3.2'), 
                ('Content-description', 'dods_data'), 
                ('Content-type', 'application/octet-stream'), 
                ('Access-Control-Allow-Origin', '*'), 
                ('Access-Control-Allow-Headers', 
                    'Origin, X-Requested-With, Content-Type'), 
                ('Content-Length', '213')]))

    def test_body(self):
        dds, xdrdata = self.res.body.split('\nData:\n', 1)                                   
        dataset = build_dataset(dds)                                                
        data = unpack_data(xdrdata, dataset)
        np.testing.assert_array_equal(data, [
            np.array([(100, -10, 0, -1, 42), (200, 10, 500, 1, 43)], 
            dtype=[
                ('lon', '<i4'), 
                ('lat', '<i4'), 
                ('depth', '<i4'),
                ('time', '<i4'), 
                ('measurement', '<i4'),
            ])
        ])


class TestDODSResponseGrid(unittest.TestCase):
    def setUp(self):
        # create WSGI app
        app = TestApp(BaseHandler(rain))
        self.res = app.get('/.dods')

    def test_status(self):
        self.assertEqual(self.res.status, "200 OK")

    def test_content_type(self):
        self.assertEqual(self.res.content_type, "application/octet-stream")

    def test_charset(self):
        self.assertEqual(self.res.charset, None)

    def test_headers(self):
        self.assertEqual(self.res.headers,
            ResponseHeaders([
                ('XDODS-Server', 'pydap/3.2'), 
                ('Content-description', 'dods_data'), 
                ('Content-type', 'application/octet-stream'), 
                ('Access-Control-Allow-Origin', '*'), 
                ('Access-Control-Allow-Headers', 
                    'Origin, X-Requested-With, Content-Type'), 
                ('Content-length', '238')]))

    def test_body(self):
        dds, xdrdata = self.res.body.split('\nData:\n', 1)                                   
        dataset = build_dataset(dds)                                                
        data = np.array(unpack_data(xdrdata, dataset))
        np.testing.assert_array_equal(data[0][0],
            np.array([[0, 1, 2], [3, 4, 5]], dtype=np.int32))
        np.testing.assert_array_equal(data[0][1],
            np.array([0, 1, 2], dtype=np.int32))
        np.testing.assert_array_equal(data[0][2],
            np.array([0, 1], dtype=np.int32))


class NotTestDODSResponseStructure(unittest.TestCase):
    def notest_body(self):
        app = TestApp(BaseHandler(SimpleStructure))
        res = app.get('/.dods')
        dds, xdrdata = res.body.split('\nData:\n', 1)                                   
        #dataset = build_dataset(dds)                                                
        #data = unpack_data(xdrdata, dataset)
        #np.testing.assert_array_equal(data, [])
