"""
This test module uses a simple development server
to test http-specific options like timeout
or caching.

It is based on simple data but with more handlers
it could work with more data formats.
"""

import numpy as np
import pytest
import time

from webob.exc import HTTPError
from pydap.handlers.lib import BaseHandler
from pydap.handlers.dap import SequenceProxy, BaseProxy
from pydap.model import DatasetType, BaseType, SequenceType
from pydap.client import open_url, open_dods
from pydap.server.devel import LocalTestServer


server = pytest.mark.server


@pytest.fixture
def sequence_type_data():
    """
    Simple sequence test data
    """
    data = [(10, 15.2, 'Diamond_St'),
            (11, 13.1, 'Blacktail_Loop'),
            (12, 13.3, 'Platinum_St'),
            (13, 12.1, 'Kodiak_Trail')]
    dtype = [('index', '<i4'),
             ('temperature', '<f8'),
             ('station', 'S40')]
    seq = SequenceType('sequence')
    seq['index'] = BaseType('index')
    seq['temperature'] = BaseType('temperature')
    seq['station'] = BaseType('station')
    seq.data = np.array(data, dtype=dtype)
    return seq


@server
def test_open(sequence_type_data):
    """Test that LocalTestServer works properly"""
    TestDataset = DatasetType('Test')
    TestDataset['sequence'] = sequence_type_data
    with LocalTestServer(BaseHandler(TestDataset)) as server:
        url = ("http://0.0.0.0:%s/" % server.port)
        dataset = open_url(url)
        seq = dataset['sequence']
        retrieved_data = [line for line in seq]

    np.testing.assert_array_equal(np.array(
                                    retrieved_data,
                                    dtype=sequence_type_data.data.dtype),
                                  np.array(
                                    sequence_type_data.data[:],
                                    dtype=sequence_type_data.data.dtype))


@server
def test_timeout(sequence_type_data):
    """Test that timeout works properly"""
    TestDataset = DatasetType('Test')
    TestDataset['sequence'] = sequence_type_data
    TestDataset['byte'] = BaseType('byte', 0)
    application = BaseHandler(TestDataset)

    # Explictly add latency on the devel server
    # to guarantee that it timeouts
    def wrap_mocker(func):
        def mock_add_latency(*args, **kwargs):
            time.sleep(1e-1)
            return func(*args, **kwargs)
        return mock_add_latency

    application = wrap_mocker(application)
    with LocalTestServer(application) as server:
        url = ("http://0.0.0.0:%s/" % server.port)

        # test open_url
        assert open_url(url) == TestDataset
        with pytest.raises(HTTPError) as e:
            open_url(url, timeout=1e-5)
        assert 'Timeout' in str(e)

        # test open_dods
        with pytest.raises(HTTPError):
            open_dods(url + '.dods?sequence', timeout=1e-5)
        assert 'Timeout' in str(e)

        # test sequenceproxy
        dataset = open_url(url)
        seq = dataset['sequence']
        assert isinstance(seq.data, SequenceProxy)
        # Change the timeout of the sequence proxy:
        seq.data.timeout = 1e-5
        with pytest.raises(HTTPError) as e:
            next(seq.iterdata())
        assert 'Timeout' in str(e)

        # test baseproxy:
        dat = dataset['byte']
        assert isinstance(dat.data, BaseProxy)
        # Change the timeout of the baseprox proxy:
        dat.data.timeout = 1e-5
        with pytest.raises(HTTPError) as e:
            dat[:]
        assert 'Timeout' in str(e)
