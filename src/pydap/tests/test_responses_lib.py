"""Test the base functions for handlers."""

import unittest

from webob import Request

import pydap.responses
from pydap.model import DatasetType
from pydap.responses.lib import BaseResponse, load_responses
from pydap.tests.datasets import VerySimpleSequence


class TestLoadResponse(unittest.TestCase):
    """Test that responses are loaded correctly."""

    def setUp(self):
        """Load all available responses.

        At least the DDS, DAS, DODS, DMR, HTML, ASC and version responses should be
        loaded, since they are included in pydap. Other third-party responses
        may also be present.

        """
        self.responses = load_responses()

    def test_responses_das(self):
        """Test that the DAS response is loaded."""
        self.assertIs(self.responses["das"], pydap.responses.das.DASResponse)

    def test_responses_dds(self):
        """Test that the DDS response is loaded."""
        self.assertIs(self.responses["dds"], pydap.responses.dds.DDSResponse)

    def test_responses_dods(self):
        """Test that the DODS response is loaded."""
        self.assertIs(self.responses["dods"], pydap.responses.dods.DODSResponse)

    def test_responses_html(self):
        """Test that the HTML response is loaded."""
        self.assertIs(self.responses["html"], pydap.responses.html.HTMLResponse)

    def test_responses_ascii(self):
        """Test that the ASCII response is loaded."""
        self.assertIs(self.responses["ascii"], pydap.responses.ascii.ASCIIResponse)
        self.assertIs(self.responses["asc"], pydap.responses.ascii.ASCIIResponse)

    def test_responses_dmr(self):
        """Test that the dmr response is loaded."""
        self.assertIs(self.responses["dmr"], pydap.responses.dmr.DMRResponse)

    def test_responses_ver(self):
        """Test that the version response is loaded."""
        self.assertIs(self.responses["ver"], pydap.responses.version.VersionResponse)


class TestBaseResponse(unittest.TestCase):
    """Test the response super class."""

    def setUp(self):
        """Instantiate a response."""
        self.response = BaseResponse(VerySimpleSequence)

    def test_call(self):
        """Test calling the WSGI app."""
        req = Request.blank("/")
        res = req.get_response(self.response)
        self.assertEqual(res.status, "200 OK")

        # note that the iterable returned by our WSGI app is the object itself:
        self.assertIs(res.app_iter, self.response)

    def test_serialization(self):
        """Test the serialization code."""
        req = Request.blank("/")
        res = req.get_response(self.response)

        # get a dataset when we pass ``DatsetType``
        self.assertIs(
            res.app_iter.x_wsgiorg_parsed_response(DatasetType), VerySimpleSequence
        )

        # when we pass something the method should return None
        self.assertIsNone(res.app_iter.x_wsgiorg_parsed_response("dataset"))

    def test_iter(self):
        """Test that calling the base class directly raises an exception."""
        with self.assertRaises(NotImplementedError):
            iter(self.response)
