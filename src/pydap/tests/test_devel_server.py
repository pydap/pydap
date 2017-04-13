"""
This test module uses a simple development server
to test http-specific options like timeout
or caching.

It is based on CSV data but with more handlers
it could work with more data formats.
"""

import csv
import tempfile
import os
import numpy as np
from nose.plugins.attrib import attr
import warnings

from pydap.handlers.csv import CSVHandler
from webob.exc import HTTPError
from pydap.client import open_url
from pydap.simple_server import LocalTestServer
from pydap.model import DatasetType

import unittest


@attr('server')
class TestCSVserver(unittest.TestCase):

    """Test that the handler creates the correct dataset from a URL."""
    data = [(10, 15.2, 'Diamond_St'),
            (11, 13.1, 'Blacktail_Loop'),
            (12, 13.3, 'Platinum_St'),
            (13, 12.1, 'Kodiak_Trail')]

    def setUp(self):
        """Create test data"""

        # Create tempfile:
        fileno, self.test_file = tempfile.mkstemp(suffix='.csv')
        # must close file number:
        os.close(fileno)
        with open(self.test_file, 'w') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
            writer.writerow(['index', 'temperature', 'site'])
            for row in self.data:
                writer.writerow(row)

    def test_open(self):
        """Test that dataset has the correct data proxies for grids."""
        dtype = [('index', '<i4'),
                 ('temperature', '<f8'),
                 ('station', 'S40')]
        with LocalTestServer(self.test_file, handler=CSVHandler) as server:
            url = ("http://0.0.0.0:%s/" % server.port +
                   os.path.basename(self.test_file))
            dataset = open_url(url)
            seq = dataset['sequence']
            retrieved_data = [line for line in seq]

        np.testing.assert_array_equal(np.array(retrieved_data, dtype=dtype),
                                      np.array(self.data, dtype=dtype))

    def test_timeout_open_url(self):
        """Test that timeout on open_url  raises the correct HTTPError"""
        with LocalTestServer(self.test_file, handler=CSVHandler) as server:
            url = ("http://0.0.0.0:%s/" % server.port +
                   os.path.basename(self.test_file))
            dataset = open_url(url)
            assert isinstance(dataset, DatasetType)
            with self.assertRaises(HTTPError):
                    open_url(url, timeout=1e-8)

    def test_timeout_open_dods(self):
        """Test that timeout on open_dods  raises the correct HTTPError"""
        with LocalTestServer(self.test_file, handler=CSVHandler) as server:
            url = ("http://0.0.0.0:%s/.dods" % server.port +
                   os.path.basename(self.test_file))
            with self.assertRaises(HTTPError):
                with warnings.catch_warnings():
                    open_url(url, timeout=1e-8)

    def tearDown(self):
        # Remove test file:
        os.remove(self.test_file)
