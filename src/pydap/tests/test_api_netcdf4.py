"""Test the DAP handler, which forms the core of the client."""

import sys
import netCDF4
import tempfile
import os
import numpy as np
from six.moves import zip

from pydap.handlers.netcdf import NetCDFHandler
from pydap.apis.netCDF4 import Dataset
from pydap.wsgi.ssf import ServerSideFunctions

if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest


class TestDataset(unittest.TestCase):

    """Test that the handler creates the correct dataset from a URL."""
    data = [(10, 15.2, 'Diamond_St'),
            (11, 13.1, 'Blacktail_Loop'),
            (12, 13.3, 'Platinum_St'),
            (13, 12.1, 'Kodiak_Trail')]

    def setUp(self):
        """Create WSGI apps"""

        # Create tempfile:
        fileno, self.test_file = tempfile.mkstemp(suffix='.nc')
        # must close file number:
        os.close(fileno)
        with netCDF4.Dataset(self.test_file, 'w') as output:
            output.createDimension('index', None)
            temp = output.createVariable('index', '<i4', ('index',))
            split_data = zip(*self.data)
            temp[:] = next(split_data)
            temp = output.createVariable('temperature', '<f8', ('index',))
            temp[:] = next(split_data)
            temp = output.createVariable('station', 'S40', ('index',))
            for item_id, item in enumerate(next(split_data)):
                temp[item_id] = item
        self.app = ServerSideFunctions(NetCDFHandler(self.test_file))

    def test_dataset_direct(self):
        """Test that dataset has the correct data proxies for grids."""
        dtype = [('index', '<i4'),
                 ('temperature', '<f8'),
                 ('station', 'S40')]
        dataset = Dataset('http://localhost:8000/',
                          application=self.app)
        retrieved_data = list(zip(dataset['index'][:],
                                  dataset['temperature'][:],
                                  dataset['station'][:]))
        np.testing.assert_array_equal(np.array(retrieved_data, dtype=dtype),
                                      np.array(self.data, dtype=dtype))

    def tearDown(self):
        os.remove(self.test_file)
