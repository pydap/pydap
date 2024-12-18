"""Test the DRM response with DAP4 protocol."""

import os
import unittest

from webob.headers import ResponseHeaders
from webtest import TestApp as App

from pydap.handlers.lib import BaseHandler
from pydap.lib import __version__
from pydap.responses.dmr import dmr
from pydap.tests.datasets import SimpleGroup


def load_dmr_file(file_path):
    abs_path = os.path.join(os.path.dirname(__file__), file_path)
    with open(abs_path, "r") as dmr_file:
        text = dmr_file.read()
    return text


class TestDMRResponseGroup(unittest.TestCase):
    """Test DRM response from sequences."""

    def setUp(self):
        """Create a simple WSGI app."""
        app = App(BaseHandler(SimpleGroup))
        self.res = app.get("/.dmr")

    def test_status(self):
        """Test the status code."""
        self.assertEqual(self.res.status, "200 OK")

    def test_dispatcher(self):
        """Test the single dispatcher."""
        with self.assertRaises(StopIteration):
            dmr(None)

    def test_content_type(self):
        """Test the content type."""
        self.assertEqual(self.res.content_type, "text/plain")

    def test_charset(self):
        """Test the charset."""
        self.assertEqual(self.res.charset, "ascii")

    def test_headers(self):
        """Test the headers from the response."""
        self.assertEqual(
            self.res.headers,
            ResponseHeaders(
                [
                    ("OPeNDAP-Server", "pydap/" + __version__),
                    ("Content-description", "dmr"),
                    ("Content-type", "text/plain; charset=ascii"),
                    ("Access-Control-Allow-Origin", "*"),
                    (
                        "Access-Control-Allow-Headers",
                        "Origin, X-Requested-With, Content-Type",
                    ),
                    ("Content-Length", "2276"),
                ]
            ),
        )

    def test_body(self):
        """Test the generated DMR response"""
        dmr_text = load_dmr_file("data/dmrs/SimpleGroup.dmr")
        self.assertEqual(self.res.text, dmr_text)
