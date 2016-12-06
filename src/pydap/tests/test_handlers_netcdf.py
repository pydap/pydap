"""Test the DAP handler, which forms the core of the client."""

import sys
from netCDF4 import Dataset
import tempfile
import multiprocessing
import os
import time
import numpy as np

from pydap.handlers.netcdf import NetCDFHandler
from pydap.handlers.dap import DAPHandler
from werkzeug.serving import run_simple
from pydap.wsgi.ssf import ServerSideFunctions
from pydap.client import open_url


if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest


class TestNetCDFHandler(unittest.TestCase):

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
        with Dataset(self.test_file, 'w') as output:
            output.createDimension('index', None)
            temp = output.createVariable('index', '<i4', ('index',))
            split_data = zip(*self.data)
            temp[:] = next(split_data)
            temp = output.createVariable('temperature', '<f8', ('index',))
            temp[:] = next(split_data)
            temp = output.createVariable('station', 'S40', ('index',))
            for item_id, item in enumerate(next(split_data)):
                temp[item_id] = item

    def test_handler_direct(self):
        """Test that dataset has the correct data proxies for grids."""
        dataset = NetCDFHandler(self.test_file).dataset
        dtype = [('index', '<i4'),
                 ('temperature', '<f8'),
                 ('station', 'S40')]
        retrieved_data = list(zip(dataset['index'][:],
                                  dataset['temperature'].array[:],
                                  dataset['station'].array[:]))
        np.testing.assert_array_equal(np.array(retrieved_data, dtype=dtype),
                                      np.array(self.data, dtype=dtype))

    def tearDown(self):
        os.remove(self.test_file)


class TestNetCDFHandlerServer(unittest.TestCase):

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
        with Dataset(self.test_file, 'w') as output:
            output.createDimension('index', None)
            temp = output.createVariable('index', '<i4', ('index',))
            split_data = zip(*self.data)
            temp[:] = next(split_data)
            temp = output.createVariable('temperature', '<f8', ('index',))
            temp[:] = next(split_data)
            temp = output.createVariable('station', 'S40', ('index',))
            for item_id, item in enumerate(next(split_data)):
                temp[item_id] = item

        #def run_simple_server(test_file):
        #    application = NetCDFHandler(test_file)
        #    application = ServerSideFunctions(application)
        #    run_simple('localhost', 8001, application,
        #               use_reloader=True)
        #self.server_process = multiprocessing.Process(target=run_simple_server,
        #                                              args=(self.test_file,))
        #self.server_process.start()
        #time.sleep(1000)

    def test_open(self):
        """Test that NetCDFHandler can be read through open_url."""
        handler = NetCDFHandler(self.test_file)
        application = ServerSideFunctions(handler)
        dataset = DAPHandler("http://localhost:8001/", application).dataset
        dtype = [('index', '<i4'),
                 ('temperature', '<f8'),
                 ('station', 'S40')]
        retrieved_data = list(zip(dataset['index'][:],
                                  dataset['temperature'].array[:],
                                  dataset['station'].array[:]))
        np.testing.assert_array_equal(np.array(retrieved_data, dtype=dtype),
                                      np.array(self.data, dtype=dtype))

    def tearDown(self):
        #self.server_process.terminate()
        #self.server_process.join()
        #del(self.server_process)
        os.remove(self.test_file)
