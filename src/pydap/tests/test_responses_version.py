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
        self.assertEqual(self.res.body, """{
    "pydap": "3.2", 
    "dap": "2.15"
}""")
