"""Test the version response."""

import unittest

from webtest import TestApp

from pydap.lib import __version__
from pydap.handlers.lib import BaseHandler
from pydap.tests.datasets import VerySimpleSequence


class TestVersionResponse(unittest.TestCase):

    """Simple tests for the version response.

    Here we don't test the actual response body, since it will vary from
    system to system and breaks continuous integration.

    """

    def setUp(self):
        """Create a simple WSGI app with a dataset."""
        app = TestApp(BaseHandler(VerySimpleSequence))
        self.res = app.get('/.ver')

    def test_status(self):
        """Test the status code."""
        self.assertEqual(self.res.status, "200 OK")

    def test_content_type(self):
        """Test that content-type is correctly set."""
        self.assertEqual(self.res.content_type, "application/json")

    def test_charset(self):
        """Test that charset is correctly set."""
        self.assertEqual(self.res.charset, "utf-8")

    def test_headers(self):
        """Test that all headers are present."""
        self.assertEqual(self.res.headers['Content-Type'],
                         'application/json; charset=utf-8')
        self.assertEqual(self.res.headers['Content-description'],
                         'dods_version')
        self.assertEqual(self.res.headers['XDODS-Server'],
                         'pydap/' + __version__)
