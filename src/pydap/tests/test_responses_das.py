import unittest

import numpy as np
from webtest import TestApp
from webob.headers import ResponseHeaders

from pydap.model import *
from pydap.handlers.lib import BaseHandler
from pydap.tests.datasets import D1, rain
from pydap.responses.ascii import ascii


class TestDASResponseSequence(unittest.TestCase):
    def setUp(self):
        # create WSGI app                                                       
        app = TestApp(BaseHandler(D1))
        self.res = app.get('/.dds')

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
                ('Content-description', 'dods_dds'), 
                ('Content-type', 'text/plain; charset=utf-8'), 
                ('Access-Control-Allow-Origin', '*'), 
                ('Access-Control-Allow-Headers',
                    'Origin, X-Requested-With, Content-Type'), 
                ('Content-Length', '164')]))
                                                                                
    def test_body(self):                                                        
        self.assertEqual(self.res.body, """Dataset {
    Sequence {
        String instrument_id;
        String location;
        Float64 latitude;
        Float64 longitude;
    } Drifters;
} EOSDB%2EDBO;
""")


class TestDASResponseGrid(unittest.TestCase):
    def setUp(self):
        # create WSGI app                                                       
        app = TestApp(BaseHandler(rain))
        self.res = app.get('/.dds')

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
                ('Content-description', 'dods_dds'), 
                ('Content-type', 'text/plain; charset=utf-8'), 
                ('Access-Control-Allow-Origin', '*'), 
                ('Access-Control-Allow-Headers', 
                    'Origin, X-Requested-With, Content-Type'), 
                ('Content-Length', '164')]))

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
""")
