"""Test the HTML response from Pydap."""

from webtest import TestApp
from webob import Request
from webob.headers import ResponseHeaders
from bs4 import BeautifulSoup
from jinja2 import Environment, DictLoader

from pydap.lib import walk, __version__
from pydap.handlers.lib import BaseHandler
from pydap.tests.datasets import VerySimpleSequence, SimpleGrid
import unittest
from collections import OrderedDict


class TestHTMLResponseSequence(unittest.TestCase):

    """Test the HTML response with a dataset containing a sequence."""

    def setUp(self):
        """Create a simple app and request HTML response."""
        self.app = TestApp(BaseHandler(VerySimpleSequence))

    def test_status(self):
        """Test the status code."""
        res = self.app.get('/.html')
        self.assertEqual(res.status, "200 OK")

    def test_content_type(self):
        """Test the content type header."""
        res = self.app.get('/.html')
        self.assertEqual(res.content_type, "text/html")

    def test_charset(self):
        """Test the charset."""
        res = self.app.get('/.html')
        self.assertEqual(res.charset, "utf-8")

    def test_headers(self):
        """Test the response headers."""
        res = self.app.get('/.html')
        self.assertEqual(
            res.headers, ResponseHeaders([
                ('XDODS-Server', 'pydap/' + __version__),
                ('Content-description', 'dods_form'),
                ('Content-type', 'text/html; charset=utf-8'),
                ('Content-Length', '5215')]))

    def test_body(self):
        """Test the HTML response.

        We use BeautifulSoup to parse the response, and check for some
        elements that should be there.

        """
        res = self.app.get('/.html')
        soup = BeautifulSoup(res.text, "html.parser")

        self.assertEqual(soup.title.string, "Dataset http://localhost/.html")
        self.assertEqual(soup.form["action"], "http://localhost/.html")
        self.assertEqual(soup.form["method"], "POST")

        # check that all variables are present
        ids = [var.id for var in walk(VerySimpleSequence)]
        for h2, id_ in zip(soup.find_all("h2"), ids):
            self.assertEqual(h2.string, id_)

    def test_post(self):
        """Test that the data redirect works."""
        res = self.app.post('/.html')
        self.assertEqual(res.status, "303 See Other")
        self.assertEqual(res.location, "http://localhost/.ascii")

    def test_post_selection(self):
        """Test that the data redirect works with a subset request."""
        res = self.app.post('/.html', {"sequence.byte": "on"})
        self.assertEqual(res.location, "http://localhost/.ascii?sequence.byte")

    def test_post_multiple_selection(self):
        """Test that the data redirect works with a subset request."""
        # from nose.tools import set_trace; set_trace()
        res = self.app.post('/.html',
                            OrderedDict([("sequence.byte", "on"),
                                         ("sequence.int", "on")]))
        self.assertEqual(
            res.location, "http://localhost/.ascii?sequence.byte,sequence.int")

    def test_filter(self):
        """Test that filtering the data works."""
        res = self.app.post(
            '/.html', {
                "var1_sequence": "sequence.byte",
                "op_sequence": ">",
                "var2_sequence": "10",
            })
        self.assertEqual(
            res.location, "http://localhost/.ascii?&sequence.byte>10")


class TestHTMLResponseGrid(unittest.TestCase):

    """Test the HTML response with a dataset containing a sequence."""

    def setUp(self):
        """Create a simple app and request HTML response."""
        self.app = TestApp(BaseHandler(SimpleGrid))

    def test_filter(self):
        """Test filtering the grid."""
        res = self.app.post(
            '/.html', {
                "SimpleGrid": "on",
                "SimpleGrid[0]": "0",
                "SimpleGrid[1]": "0",
            })
        self.assertEqual(
            res.location, "http://localhost/.ascii?SimpleGrid[0][0]")


class TestHTMLTemplate(unittest.TestCase):

    """Test that global environment is used if available.

    The HTML response has its own environment and loader, for when used in
    standalone mode. If used with a Pydap server that defines its own
    environment, the HTML response will reuse the global environment after
    injecting its loader as a backup. This allows the HTML response to work in
    case the global environment does not have the HTML templates.

    """

    def test_environ_loader_with_template(self):
        """Test that global environment is used."""
        loader = DictLoader({'html.html': 'global'})
        env = Environment(loader=loader)

        app = BaseHandler(VerySimpleSequence)
        req = Request.blank('/.html')
        req.environ["pydap.jinja2.environment"] = env
        res = req.get_response(app)
        self.assertEqual(res.text, "global")

    def test_environ_loader_without_template(self):
        """Test that global environment is used."""
        env = Environment()
        self.assertIsNone(env.loader)

        app = BaseHandler(VerySimpleSequence)
        req = Request.blank('/.html')
        req.environ["pydap.jinja2.environment"] = env
        res = req.get_response(app)
        self.assertNotEqual(res.text, "global")
