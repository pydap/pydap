"""
This is a simple example from the DODS Test Server.

    http://test.opendap.org:8080/dods/dts/D1

"""
import unittest                                                                 

import numpy as np
from webtest import TestApp
import requests
                                                                                
from pydap.model import *                                                       
from pydap.handlers.lib import BaseHandler
from pydap.client import open_url
from pydap.tests import requests_intercept


DATA = zip(
    [("This is a data test string (pass %d)." % (1+i*2)) for i in range(5)],
    [("This is a data test string (pass %d)." % (i*2)) for i in range(5)],
    [1000.0, 999.95, 999.80, 999.55, 999.20],
    [999.95, 999.55, 998.75, 997.55, 995.95])
                                 
                                                                                
class Test_D1(unittest.TestCase):                                            
    def setUp(self):
        # create dataset
        dataset = DatasetType('EOSDB.DBO')                                 
        dataset['Drifters'] = SequenceType('Drifters')                     
        dataset['Drifters']['instrument_id'] = BaseType('instrument_id')
        dataset['Drifters']['location'] = BaseType('location')
        dataset['Drifters']['latitude'] = BaseType('latitude')
        dataset['Drifters']['longitude'] = BaseType('longitude')

        dataset.Drifters.data = np.rec.fromrecords(
            DATA, names=dataset.Drifters.keys())

        # create WSGI app
        self.app = TestApp(BaseHandler(dataset))

        # intercept HTTP requests
        self.requests_get = requests.get
        requests.get = requests_intercept(self.app, 'http://localhost:8001/')

    def tearDown(self):
        requests.get = self.requests_get

    def test_dds(self):
        self.assertEqual(self.app.get('/.dds').body, 
            '''Dataset {
    Sequence {
        String instrument_id;
        String location;
        Float64 latitude;
        Float64 longitude;
    } Drifters;
} EOSDB%2EDBO;
''')

    def test_data(self):
        dataset = open_url('http://localhost:8001/')
        data = list(dataset.Drifters)
        self.assertEqual(data, DATA)

    def test_filtering(self):
        dataset = open_url('http://localhost:8001/')
        drifters = dataset.Drifters
        selection = np.rec.fromrecords(
            list(drifters[ drifters.longitude < 999 ]), names=drifters.keys())

        data = np.rec.fromrecords(DATA, names=drifters.keys())
        filtered = data[ data['longitude'] < 999 ]

        np.testing.assert_array_equal(filtered, selection)

    def test_filtering_child(self):
        dataset = open_url('http://localhost:8001/')
        drifters = dataset.Drifters
        selection = np.array(
            list(drifters[ drifters.longitude < 999 ]['location']))

        data = np.rec.fromrecords(DATA, names=drifters.keys())
        filtered = data[ data['longitude'] < 999 ]['location']

        np.testing.assert_array_equal(filtered, selection)

