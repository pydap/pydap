import os
import unittest

import numpy as np
from webtest import TestApp
import requests

from pydap.model import *
from pydap.handlers.lib import BaseHandler
from pydap.client import open_url, open_dods, open_file, Functions
from pydap.tests import requests_intercept
from pydap.tests.datasets import D1, rain
from pydap.wsgi.ssf import ServerSideFunctions


DODS = os.path.join(os.path.dirname(__file__), 'test.01.dods')
DAS = os.path.join(os.path.dirname(__file__), 'test.01.das')


class Test_open_file(unittest.TestCase):
    def test_open_file(self):
        dataset = open_file(DODS, DAS)
        self.assertEqual(dataset.data, [
            0, 1, 0, 0, 0, 0.0, 1000.0,
            'This is a data test string (pass 0).',
            'http://www.dods.org',
        ])

        self.assertEqual(dataset.i32.units, 'unknown')
        self.assertEqual(dataset.i32.Description, 'A 32 bit test server int')
        self.assertEqual(dataset.b.units, 'unknown')
        self.assertEqual(dataset.b.Description, 'A test byte')
        self.assertEqual(dataset.Facility['DataCenter'],
            "COAS Environmental Computer Facility")
        self.assertEqual(dataset.Facility['PrincipleInvestigator'],
            ['Mark Abbott', 'Ph.D'])
        self.assertEqual(dataset.Facility['DrifterType'],
            "MetOcean WOCE/OCM")


class Test_open_dods(unittest.TestCase):
    def setUp(self):
        # create WSGI app
        self.app = TestApp(BaseHandler(D1))

        # intercept HTTP requests
        self.requests_get = requests.get
        requests.get = requests_intercept(self.app, 'http://localhost:8001/')

    def tearDown(self):
        requests.get = self.requests_get

    def test_open_dods(self):
        dataset = open_dods('http://localhost:8001/.dods')
        data = np.array(np.rec.fromrecords(D1.Drifters.data.tolist(),
            names=dataset.Drifters.keys()))
        np.testing.assert_array_equal(data, dataset.Drifters.data)
        self.assertEqual(dataset.attributes, {})

    def test_open_dods_with_attributes(self):
        dataset = open_dods('http://localhost:8001/.dods', True)
        self.assertEqual(dataset.attributes['NC_GLOBAL'], {})
        self.assertEqual(dataset.attributes['DODS_EXTRA'], {})
        self.assertEqual(dataset.attributes['type'], "Drifters")

    def test_open_url(self):
        dataset = open_url('http://localhost:8001/')
        np.testing.assert_array_equal(D1.Drifters.data.tolist(),
                list(dataset.Drifters.data))
        self.assertEqual(dataset.attributes['NC_GLOBAL'], {})
        self.assertEqual(dataset.attributes['DODS_EXTRA'], {})
        self.assertEqual(dataset.attributes['type'], "Drifters")


class Test_Functions(unittest.TestCase):
    def setUp(self):
        # create WSGI app
        self.app = TestApp(ServerSideFunctions(BaseHandler(rain)))

        # intercept HTTP requests
        self.requests_get = requests.get
        requests.get = requests_intercept(self.app, 'http://localhost:8001/')

    def tearDown(self):
        requests.get = self.requests_get

    def test_Functions(self):
        original = open_url('http://localhost:8001/')
        self.assertEqual(original.rain.rain.shape, (2, 3))

        functions = Functions('http://localhost:8001/')

        dataset = functions.mean(original.rain, 0)
        self.assertEqual(dataset.rain.rain.shape, (3,))
        np.testing.assert_array_equal(dataset.rain.rain.data,
            np.array([1.5, 2.5, 3.5]))
        dataset = functions.mean(original.rain, 0)
        self.assertEqual(dataset['rain']['rain'].shape, (3,))
        np.testing.assert_array_equal(dataset.rain.rain.data,
            np.array([1.5, 2.5, 3.5]))

        dataset = functions.mean(original.rain, 1)
        self.assertEqual(dataset.rain.rain.shape, (2,))
        np.testing.assert_array_equal(dataset.rain.rain.data,
            np.array([1.0, 4.0]))
        dataset = functions.mean(original.rain, 1)
        self.assertEqual(dataset['rain']['rain'].shape, (2,))
        np.testing.assert_array_equal(dataset.rain.rain.data,
            np.array([1.0, 4.0]))

        dataset = functions.mean(functions.mean(original.rain, 0), 0)
        self.assertEqual(dataset['rain']['rain'].shape, ())
        np.testing.assert_array_equal(dataset.rain.rain.data,
            np.array(2.5))
