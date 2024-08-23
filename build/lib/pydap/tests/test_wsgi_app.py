"""Tests for the pydap server."""

import multiprocessing
import os
import shutil
import tempfile
import unittest
from xml.etree import ElementTree as etree

from webob import Response
from webob.dec import wsgify
from webtest import AppError
from webtest import TestApp as App

from pydap.exceptions import ExtensionNotSupportedError
from pydap.wsgi.app import DapServer, PyDapApplication, StaticMiddleware, init


class TestDapServer(unittest.TestCase):
    """Tests for the pydap server."""

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
        self.app = App(app)

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

    def test_thredds_catalog_request(self):
        """Test that THREDDS Catalog requests work."""
        res = self.app.get("/catalog.xml")
        self.assertEqual(res.status, "200 OK")
        self.assertTrue(res.text.startswith("<?xml"))
        xml = etree.fromstring(res.text)
        self.assertEqual(
            xml.tag,
            "{http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0}catalog",
        )  # noqa

    def test_not_found(self):
        """Test 404 responses."""
        with self.assertRaises(AppError):
            self.app.get("/README.html")

    def test_asset(self):
        """Test that we can load a static asset."""
        res = self.app.get("/static/style.css")
        self.assertEqual(res.status, "200 OK")


class TestPyDapApplication(unittest.TestCase):
    """tests the configuration of Application"""

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
        nworks = multiprocessing.cpu_count() // 2
        nthreads = multiprocessing.cpu_count() // 2
        self.app = PyDapApplication(
            app, host="127.0.1", port="8001", workers=nworks, threads=nthreads
        )

    def tearDown(self):
        """Remove the installation."""
        shutil.rmtree(self.install)

    def test_app_bind(self):
        """Test the correct config."""
        bind = self.app.cfg.settings["bind"].value[0]
        self.assertEqual(bind, "127.0.1:8001")

    def test_app_cfgworkers(self):
        workers = self.app.cfg.settings["workers"].value
        self.assertEqual(workers, multiprocessing.cpu_count() // 2)

    def test_app_cfgthreads(self):
        threads = self.app.cfg.settings["threads"].value
        self.assertEqual(threads, multiprocessing.cpu_count() // 2)


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
        self.app = App(app)

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
