"""
This test module uses a simple development server
to test http-specific options like timeout
or caching.

It is based on simple data but with more handlers
it could work with more data formats.
"""

import numpy as np
import pytest

from pydap.handlers.lib import BaseHandler
from pydap.model import DatasetType, BaseType, SequenceType
from pydap.client import open_url
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
def test_netcdf(sequence_type_data):
    """Test that LocalTestServer works properly"""
    TestDataset = DatasetType('Test')
    TestDataset['float'] = BaseType('float', np.array(1, dtype=np.float32))

    with TestDataset.to_netcdf() as ds:
        assert 'float' in ds.variables
        assert ds['float'].dtype == np.float32
        assert ds['float'][:] == np.array(1, dtype=np.float32)
