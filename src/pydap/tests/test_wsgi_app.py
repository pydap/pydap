"""Tests for the Pydap server."""

import os
import tempfile
import shutil

from webtest import TestApp, AppError
from webob import Response
from webob.dec import wsgify

from pydap.wsgi.app import init, DapServer, StaticMiddleware
from pydap.exceptions import ExtensionNotSupportedError

import unittest


class TestDapServer(unittest.TestCase):

    """Tests for the Pydap server."""

    def setUp(self):
        """Create an installation."""
        self.install = tempfile.mkdtemp(suffix="pydap")

        # create directory for data with two files
        data = os.path.join(self.install, "data")
        os.mkdir(data)
        os.mkdir(os.path.join(data, "subdir"))
        with open(os.path.join(data, "README.txt"), "w") as fp:
            fp.write("Hello, world!")
        with open(os.path.join(data, "data.foo"), "w") as fp:
            pass

        # create templates directory
        templates = os.path.join(self.install, "templates")
        init(templates)

        app = DapServer(data, templates)
        app.handlers = [DummyHandler]
        app = StaticMiddleware(app, os.path.join(templates, "static"))
        self.app = TestApp(app)

    def tearDown(self):
        """Remove the installation."""
        shutil.rmtree(self.install)

    def test_app_root(self):
        """Test a regular request."""
        res = self.app.get("/")
        self.assertEqual(res.status, "200 OK")

    def test_app_hack(self):
        """Test a request to a resource that is outside the root dir."""
        with self.assertRaises(AppError):
            self.app.get("/../../../../../../../etc/passwd")

    def test_app_file(self):
        """Test that we can download a file."""
        res = self.app.get("/README.txt")
        self.assertEqual(res.text, "Hello, world!")

    def test_dap_request(self):
        """Test that DAP requests work."""
        res = self.app.get("/data.foo.dds")
        self.assertEqual(res.text, "Success!")

    def test_invalid_dap_request(self):
        """Test invalid DAP requests."""
        with self.assertRaises(ExtensionNotSupportedError):
            self.app.get("/README.txt.dds")

    def test_not_found(self):
        """Test 404 responses."""
        with self.assertRaises(AppError):
            self.app.get("/README.html")

    def test_asset(self):
        """Test that we can load a static asset."""
        res = self.app.get("/static/style.css")
        self.assertEqual(res.status, "200 OK")


class TestPackageAssets(unittest.TestCase):

    """Test that we can load assets from the package."""

    def setUp(self):
        """Create an installation."""
        self.install = tempfile.mkdtemp(suffix="pydap")

        # create directory for data with two files
        data = os.path.join(self.install, "data")
        os.mkdir(data)
        with open(os.path.join(data, "README.txt"), "w") as fp:
            fp.write("Hello, world!")
        with open(os.path.join(data, "data.foo"), "w") as fp:
            pass

        app = DapServer(data)
        app = StaticMiddleware(app, ("pydap.wsgi", "templates/static"))
        self.app = TestApp(app)

    def tearDown(self):
        """Remove the installation."""
        shutil.rmtree(self.install)

    def test_asset(self):
        """Test that we can load a static asset."""
        res = self.app.get("/static/style.css")
        self.assertEqual(res.status, "200 OK")

    def test_not_found(self):
        """Test 404 responses."""
        with self.assertRaises(AppError):
            self.app.get("/static/missing")


class DummyHandler(object):

    """A dummy handler for testing the server."""

    extensions = r"^.*\.foo$"

    def __init__(self, filepath):
        pass

    @wsgify
    def __call__(self, req):
        return Response("Success!")
