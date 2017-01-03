import numpy as np
from webob.request import Request
from pydap.model import DatasetType, BaseType
from pydap.handlers.lib import BaseHandler
from pydap.client import open_url
import unittest


class TestQuote(unittest.TestCase):
    def setUp(self):
        # create dataset
        self.dataset = DatasetType("test")
        self.dataset["foo["] = BaseType("foo[", np.array(1))

        # create WSGI app
        self.app = BaseHandler(self.dataset)

    def test_name(self):
        """Check that the name was properly escaped."""
        self.assertEqual(self.dataset.keys(), ["foo%5B"])

    def test_dds(self):
        text = Request.blank("/.dds").get_response(self.app).text
        self.assertEqual(text, """Dataset {
    Int32 foo%5B;
} test;
""")

    def test_request(self):
        text = Request.blank("/.dds?foo%255B").get_response(self.app).text
        self.assertEqual(text, """Dataset {
    Int32 foo%5B;
} test;
""")

    def test_client(self):
        dataset = open_url("http://localhost:8001/", application=self.app)
        self.assertEqual(self.dataset.keys(), ["foo%5B"])
        self.assertEqual(dataset["foo["].name, "foo%5B")
        self.assertEqual(dataset["foo%5B"][0], 1)


class TestPeriod(unittest.TestCase):
    def setUp(self):
        # create dataset
        dataset = DatasetType("test")
        dataset["a.b"] = BaseType("a.b", np.array(1))

        # create WSGI app
        self.app = BaseHandler(dataset)

    def test_dds(self):
        text = Request.blank("/.dds").get_response(self.app).text
        self.assertEqual(text, """Dataset {
    Int32 a%2Eb;
} test;
""")

    def test_client(self):
        dataset = open_url("http://localhost:8001/", application=self.app)
        self.assertEqual(dataset["a.b"].name, "a%2Eb")
        self.assertEqual(dataset["a.b"][0], 1)
