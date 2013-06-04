import os
import unittest                                                                 

import numpy as np
from webtest import TestApp                                                     
import requests                                                                 
                                                                                
from pydap.model import *                                                       
from pydap.handlers.lib import BaseHandler                                      
from pydap.client import open_url, open_dods, open_file, Functions
from pydap.tests import requests_intercept
from pydap.wsgi.ssf import ServerSideFunctions


DODS = os.path.join(os.path.dirname(__file__), 'test.01.dods')
DAS = os.path.join(os.path.dirname(__file__), 'test.01.das')

DATA = zip(                                                                     
    [("This is a data test string (pass %d)." % (1+i*2)) for i in range(5)],    
    [("This is a data test string (pass %d)." % (i*2)) for i in range(5)],      
    [1000.0, 999.95, 999.80, 999.55, 999.20],                                   
    [999.95, 999.55, 998.75, 997.55, 995.95])


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
        # create dataset                                                        
        dataset = DatasetType('EOSDB.DBO', type='Drifters')
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

    def test_open_dods(self):
        dataset = open_dods('http://localhost:8001/.dods')
        data = np.array(np.rec.fromrecords(DATA, names=dataset.Drifters.keys()))
        np.testing.assert_array_equal(data, dataset.Drifters.data)
        self.assertEqual(dataset.attributes, {})

    def test_open_dods_with_attributes(self):
        dataset = open_dods('http://localhost:8001/.dods', True)
        self.assertEqual(dataset.attributes['NC_GLOBAL'], {})
        self.assertEqual(dataset.attributes['DODS_EXTRA'], {})
        self.assertEqual(dataset.attributes['type'], "Drifters")

    def test_open_url(self):
        dataset = open_url('http://localhost:8001/')
        np.testing.assert_array_equal(DATA, list(dataset.Drifters.data))
        self.assertEqual(dataset.attributes['NC_GLOBAL'], {})
        self.assertEqual(dataset.attributes['DODS_EXTRA'], {})
        self.assertEqual(dataset.attributes['type'], "Drifters")


class Test_Functions(unittest.TestCase):
    def setUp(self):                                                            
        # create dataset                                                        
        dataset = DatasetType('test')
        rain = dataset['rain'] = GridType('rain')
        rain['rain'] = BaseType('rain', np.arange(6).reshape(2, 3), dimensions=('y', 'x'))
        rain['x'] = BaseType('x', np.arange(3), units='degrees_east')           
        rain['y'] = BaseType('y', np.arange(2), units='degrees_north')
                                                                                
        # create WSGI app                                                       
        self.app = TestApp(ServerSideFunctions(BaseHandler(dataset)))
                                                                                
        # intercept HTTP requests                                               
        self.requests_get = requests.get                                        
        requests.get = requests_intercept(self.app, 'http://localhost:8001/')   
                                                                                
    def tearDown(self):                                                         
        requests.get = self.requests_get   

    def test_Functions(self):
        dataset = open_url('http://localhost:8001/')
        rain = dataset.rain
        self.assertEqual(rain.rain.shape, (2, 3))

        functions = Functions('http://localhost:8001/')

        dataset = functions.mean(rain, 0)
        self.assertEqual(dataset.rain.rain.shape, (3,))
        np.testing.assert_array_equal(dataset.rain.rain.data,
            np.array([1.5, 2.5, 3.5]))
        dataset = functions.mean(rain, 0)
        self.assertEqual(dataset['rain']['rain'].shape, (3,))
        np.testing.assert_array_equal(dataset.rain.rain.data,
            np.array([1.5, 2.5, 3.5]))

        dataset = functions.mean(rain, 1)
        self.assertEqual(dataset.rain.rain.shape, (2,))
        np.testing.assert_array_equal(dataset.rain.rain.data,
            np.array([1.0, 4.0]))
        dataset = functions.mean(rain, 1)
        self.assertEqual(dataset['rain']['rain'].shape, (2,))
        np.testing.assert_array_equal(dataset.rain.rain.data,
            np.array([1.0, 4.0]))

        dataset = functions.mean(functions.mean(rain, 0), 0)
        self.assertEqual(dataset['rain']['rain'].shape, ())
        np.testing.assert_array_equal(dataset.rain.rain.data,
            np.array(2.5))


