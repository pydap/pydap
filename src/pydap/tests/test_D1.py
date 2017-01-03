"""
This is a simple example from the DODS Test Server.

    http://test.opendap.org:8080/dods/dts/D1

"""
import unittest

import numpy as np
from webob.request import Request

from pydap.handlers.lib import BaseHandler
from pydap.client import open_url
from pydap.tests.datasets import D1


class TestD1(unittest.TestCase):
    def setUp(self):
        # create WSGI app
        self.app = BaseHandler(D1)

    def test_dds(self):
        self.assertEqual(Request.blank('/.dds').get_response(self.app).text,
            '''Dataset {
    Sequence {
        String instrument_id;
        String location;
        Float64 latitude;
        Float64 longitude;
    } Drifters;
} EOSDB%2EDBO;
''')

    def test_ascii(self):
        resp = Request.blank('/.asc').get_response(self.app)
        content = resp.text
        self.assertEqual(content,
            '''Dataset {
    Sequence {
        String instrument_id;
        String location;
        Float64 latitude;
        Float64 longitude;
    } Drifters;
} EOSDB%2EDBO;
---------------------------------------------
Drifters.instrument_id, Drifters.location, Drifters.latitude, Drifters.longitude
"This is a data test string (pass 1).", "This is a data test string (pass 0).", 1000, 999.95
"This is a data test string (pass 3).", "This is a data test string (pass 2).", 999.95, 999.55
"This is a data test string (pass 5).", "This is a data test string (pass 4).", 999.8, 998.75
"This is a data test string (pass 7).", "This is a data test string (pass 6).", 999.55, 997.55
"This is a data test string (pass 9).", "This is a data test string (pass 8).", 999.2, 995.95

''')

    def test_data(self):
        dataset = open_url('http://localhost:8001/', application=self.app)
        data = list(dataset.Drifters)
        self.assertEqual(data, D1.Drifters.data.tolist())

    def test_filtering(self):
        dataset = open_url('http://localhost:8001/', application=self.app)
        drifters = dataset.Drifters
        selection = np.rec.fromrecords(
            list(drifters[drifters.longitude < 999]), names=drifters.keys())

        data = np.rec.fromrecords(
                D1.Drifters.data.tolist(), names=drifters.keys())
        filtered = data[data['longitude'] < 999]

        np.testing.assert_array_equal(filtered, selection)

    def test_filtering_child(self):
        dataset = open_url('http://localhost:8001/', application=self.app)
        drifters = dataset.Drifters
        selection = np.array(
            list(drifters[drifters.longitude < 999]['location']))

        data = np.rec.fromrecords(
                D1.Drifters.data.tolist(), names=drifters.keys())
        filtered = data[data['longitude'] < 999]['location']

        np.testing.assert_array_equal(filtered, selection)
