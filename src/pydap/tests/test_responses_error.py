import sys
from webob import Request

from pydap.responses.error import ErrorResponse
from pydap.lib import __version__
import unittest


class TestErrorResponse(unittest.TestCase):
    def setUp(self):
        # create an exception that would happen in runtime
        try:
            1/0
        except:
            error = ErrorResponse(sys.exc_info())

        req = Request.blank('/')
        self.res = req.get_response(error)

    def test_status(self):
        self.assertEqual(self.res.status, "500 Internal Error")

    def test_content_type(self):
        self.assertEqual(self.res.content_type, "text/plain")

    def test_charset(self):
        self.assertEqual(self.res.charset, "utf-8")

    def test_headers(self):
        self.assertEqual(self.res.headers['Content-Type'],
                         'text/plain; charset=utf-8')
        self.assertEqual(self.res.headers['Content-description'], 'dods_error')
        self.assertEqual(self.res.headers['XDODS-Server'],
                         'pydap/' + __version__)

    def test_body(self):
        self.assertRegexpMatches(self.res.text, """Error {
    code = -1;
    message = "Traceback \(most recent call last\):
  File .*
    1/0
ZeroDivisionError:( integer)? division( or modulo)? by zero
";
}""")
