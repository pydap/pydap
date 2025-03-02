"""
This test module uses a simple development server
to test http-specific options like timeout
or caching.

It is based on simple data but with more handlers
it could work with more data formats.
"""

import ssl
import sys
import time

import numpy as np
import pytest
import requests

from pydap.client import open_url
from pydap.handlers.lib import BaseHandler
from pydap.model import BaseType, DatasetType, SequenceType
from pydap.server.devel_ssl import LocalTestServerSSL

server = pytest.mark.server


@pytest.fixture
def sequence_type_data():
    """
    Simple sequence test data
    """
    data = [
        (10, 15.2, "Diamond_St"),
        (11, 13.1, "Blacktail_Loop"),
        (12, 13.3, "Platinum_St"),
        (13, 12.1, "Kodiak_Trail"),
    ]
    dtype = [("index", "<i4"), ("temperature", "<f8"), ("station", "S40")]
    seq = SequenceType("sequence")
    seq["index"] = BaseType("index")
    seq["temperature"] = BaseType("temperature")
    seq["station"] = BaseType("station")
    seq.data = np.array(data, dtype=dtype)
    return seq


@server
def test_open(sequence_type_data):
    """Test that LocalTestServerSSL works properly"""
    TestDataset = DatasetType("Test")
    TestDataset["sequence"] = sequence_type_data
    with LocalTestServerSSL(BaseHandler(TestDataset)) as server:
        time.sleep(0.1)
        dataset = open_url(server.url, protocol="dap2")
        seq = dataset["sequence"]
        retrieved_data = [line for line in seq]

    np.testing.assert_array_equal(
        np.array(retrieved_data, dtype=sequence_type_data.data.dtype),
        np.array(sequence_type_data.data[:], dtype=sequence_type_data.data.dtype),
    )


@pytest.mark.filterwarnings("ignore::urllib3.exceptions.InsecureRequestWarning")
@server
def test_verify_open_url(sequence_type_data):
    """Test that open_url raises the correct SSLError"""
    # warnings.simplefilter("always")

    TestDataset = DatasetType("Test")
    TestDataset["sequence"] = sequence_type_data
    TestDataset["byte"] = BaseType("byte", 0)
    application = BaseHandler(TestDataset)
    with LocalTestServerSSL(application, ssl_context="adhoc") as server:
        try:
            time.sleep(0.2)
            open_url(
                server.url, verify=False, session=requests.Session(), protocol="dap2"
            )
        except (ssl.SSLError, requests.exceptions.SSLError):
            pytest.fail("SSLError should not be raised.")

        with pytest.raises(requests.exceptions.SSLError):
            open_url(server.url, session=requests.Session())

        if not (sys.version_info >= (3, 0) and sys.version_info < (3, 4, 4)):
            # verify is disabled by default for python 3 before 3.4.4:
            with pytest.raises(requests.exceptions.SSLError):
                open_url(server.url)
