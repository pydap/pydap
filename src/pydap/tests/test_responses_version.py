import sys
import unittest

from webob import Request
from webob.headers import ResponseHeaders
from webtest import TestApp

from pydap.responses.version import VersionResponse
from pydap.handlers.lib import BaseHandler
from pydap.tests.datasets import D1


class TestVersionResponse(unittest.TestCase):
    def setUp(self):
        app = TestApp(BaseHandler(D1))                                          
        self.res = app.get('/.ver')

    def test_status(self):
        self.assertEqual(self.res.status, "200 OK")

    def test_content_type(self):
        self.assertEqual(self.res.content_type, "application/json")

    def test_charset(self):
        self.assertEqual(self.res.charset, "utf-8")

    def test_headers(self):
        self.assertEqual(self.res.headers['Content-Type'],
                'application/json; charset=utf-8')
        self.assertEqual(self.res.headers['Content-description'],
                'dods_version')
        self.assertEqual(self.res.headers['XDODS-Server'], 'pydap/3.2')

    def test_body(self):
        self.assertEqual(self.res.body, r"""{
    "python": "2.7.4 (default, Apr 19 2013, 18:28:01) \n[GCC 4.7.3]", 
    "pydap": "3.2", 
    "dap": "2.15", 
    "responses": {
        "dods": "3.2", 
        "ver": "3.2", 
        "dds": "3.2", 
        "asc": "3.2", 
        "html": "3.2", 
        "das": "3.2", 
        "ascii": "3.2"
    }, 
    "handlers": {
        "netcdf": "0.7"
    }
}""")
