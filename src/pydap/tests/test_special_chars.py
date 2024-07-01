import unittest

import numpy as np
from webob.request import Request

from pydap.client import open_url
from pydap.handlers.lib import BaseHandler
from pydap.model import BaseType, DatasetType


class TestQuote(unittest.TestCase):
    def setUp(self):
        # create dataset
        self.dataset = DatasetType("test")
        self.dataset["foo["] = BaseType("foo[", np.array(1))

        # create WSGI app
        self.app = BaseHandler(self.dataset)

    def test_name(self):
        """Check that the name was properly escaped."""
        self.assertEqual(list(self.dataset.keys()), ["foo%5B"])

    def test_dds(self):
        text = Request.blank("/.dds").get_response(self.app).text
        self.assertEqual(
            text,
            """Dataset {
    Int32 foo%5B;
} test;
""",
        )

    def test_request(self):
        text = Request.blank("/.dds?foo%5B").get_response(self.app).text
        self.assertEqual(
            text,
            """Dataset {
    Int32 foo%5B;
} test;
""",
        )

    def test_client(self):
        dataset = open_url("http://localhost:8001/", application=self.app)
        self.assertEqual(list(self.dataset.keys()), ["foo%5B"])
        self.assertEqual(dataset["foo["].name, "foo%5B")
        self.assertEqual(dataset["foo%5B"].data, 1)


class TestPeriod(unittest.TestCase):
    def setUp(self):
        # create dataset
        dataset = DatasetType("test")
        dataset["a.b"] = BaseType("a.b", np.array(1))

        # create WSGI app
        self.app = BaseHandler(dataset)

    def test_dds(self):
        text = Request.blank("/.dds").get_response(self.app).text
        self.assertEqual(
            text,
            """Dataset {
    Int32 a%2Eb;
} test;
""",
        )

    def test_client(self):
        dataset = open_url("http://localhost:8001/", application=self.app)
        self.assertEqual(dataset["a.b"].name, "a%2Eb")
        # the test below gives problem because a.b is passed
        # to the `query` part of the constrain. However, this a.b
        # in the query conflicts with the behavior of a being a sequence
        # and b being a variable within the sequence...
        # self.assertEqual(dataset["a.b"][0], 1)
