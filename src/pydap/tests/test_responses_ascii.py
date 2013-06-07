import unittest

import numpy as np
from webtest import TestApp
from webob.headers import ResponseHeaders

from pydap.model import *
from pydap.handlers.lib import BaseHandler
from pydap.tests.datasets import D1, rain
from pydap.responses.ascii import ascii


class TestASCIIResponseSequence(unittest.TestCase):
    def setUp(self):
        # create WSGI app                                                       
        app = TestApp(BaseHandler(D1))
        self.res = app.get('/.asc')

    def test_dispatcher(self):
        with self.assertRaises(StopIteration):
            ascii(None)

    def test_status(self):                                                      
        self.assertEqual(self.res.status, "200 OK")                 
                                                                                
    def test_content_type(self):                                                
        self.assertEqual(self.res.content_type, "text/plain")                   
                                                                                
    def test_charset(self):                                                     
        self.assertEqual(self.res.charset, "utf-8")                             
                                                                                
    def test_headers(self):                                                     
        self.assertEqual(self.res.headers,                                      
            ResponseHeaders([
                ('XDODS-Server', 'pydap/3.2'), 
                ('Content-description', 'dods_ascii'), 
                ('Content-type', 'text/plain; charset=utf-8'),
                ('Content-Length', '763')]))
                                                                                
    def test_body(self):                                                        
        self.assertEqual(self.res.body, """Dataset {
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

""")


class TestASCIIResponseGrid(unittest.TestCase):
    def setUp(self):
        # create WSGI app                                                       
        app = TestApp(BaseHandler(rain))
        self.res = app.get('/.asc')

    def test_status(self):
        self.assertEqual(self.res.status, "200 OK")                 
                                                                                
    def test_content_type(self):                                                
        self.assertEqual(self.res.content_type, "text/plain")                   
                                                                                
    def test_charset(self):                                                     
        self.assertEqual(self.res.charset, "utf-8")                             
                                                                                
    def test_headers(self):                                                     
        self.assertEqual(self.res.headers,                                      
            ResponseHeaders([
                ('XDODS-Server', 'pydap/3.2'), 
                ('Content-description', 'dods_ascii'), 
                ('Content-type', 'text/plain; charset=utf-8'), 
                ('Content-Length', '292')]))

    def test_body(self):
        self.assertEqual(self.res.body, """Dataset {
    Grid {
        Array:
            Int32 rain[y = 2][x = 3];
        Maps:
            Int32 x[x = 3];
            Int32 y[y = 2];
    } rain;
} test;
---------------------------------------------
rain.rain
[0][0] "[[0 1 2]
 [3 4 5]]"

rain.x
[0] "[0 1 2]"

rain.y
[0] "[0 1]"


""")
