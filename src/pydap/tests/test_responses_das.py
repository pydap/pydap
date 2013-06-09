import unittest

import numpy as np
from webtest import TestApp
from webob.headers import ResponseHeaders

from pydap.model import *
from pydap.handlers.lib import BaseHandler
from pydap.tests.datasets import bounds, rain, SimpleStructure
from pydap.responses.das import das


class TestDASResponseSequence(unittest.TestCase):
    def setUp(self):
        # create WSGI app                                                       
        app = TestApp(BaseHandler(bounds))
        self.res = app.get('/.das')

    def test_dispatcher(self):
        with self.assertRaises(StopIteration):
            das(None)

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
                ('Content-description', 'dods_das'), 
                ('Content-type', 'text/plain; charset=utf-8'), 
                ('Access-Control-Allow-Origin', '*'), 
                ('Access-Control-Allow-Headers', 
                    'Origin, X-Requested-With, Content-Type'), 
                ('Content-Length', '333')]))
                                                                                
    def test_body(self):                                                        
        self.assertEqual(self.res.body, """Attributes {
    sequence {
        lon {
            String axis "X";
        }
        lat {
            String axis "Y";
        }
        depth {
            String axis "Z";
        }
        time {
            String units "days since 1970-01-01";
            String axis "T";
        }
        measurement {
        }
    }
}
""")


class TestDASResponseGrid(unittest.TestCase):
    def setUp(self):
        # create WSGI app                                                       
        app = TestApp(BaseHandler(rain))
        self.res = app.get('/.das')

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
                ('Content-description', 'dods_das'),
                ('Content-type', 'text/plain; charset=utf-8'),
                ('Access-Control-Allow-Origin', '*'),
                ('Access-Control-Allow-Headers', 
                    'Origin, X-Requested-With, Content-Type'),
                ('Content-Length', '32')]))

    def test_body(self):
        self.assertEqual(self.res.body, """Attributes {
    rain {
    }
}
""")


class TestDASResponseStructure(unittest.TestCase):
    def test_body(self):
        app = TestApp(BaseHandler(SimpleStructure))
        res = app.get('/.das')
        self.assertEqual(res.body, """Attributes {
    types {
        String key "value";
        nested {
            Int32 array 1;
            Float64 float 1000;
            Int32 list 42, 43;
            String string "bar";
        }
        b {
        }
        i32 {
        }
        ui32 {
        }
        i16 {
        }
        ui16 {
        }
        f32 {
        }
        f64 {
        }
        s {
        }
        u {
        }
    }
}
""")
