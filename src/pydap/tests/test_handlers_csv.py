"""Test the DAP handler, which forms the core of the client."""

import sys
import csv
import tempfile
import os
import numpy as np

from pydap.handlers.csv import CSVHandler
from pydap.handlers.dap import DAPHandler


if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest


class TestCSVHandler(unittest.TestCase):

    """Test that the handler creates the correct dataset from a URL."""
    data = [(10, 15.2, 'Diamond_St'),
            (11, 13.1, 'Blacktail_Loop'),
            (12, 13.3, 'Platinum_St'),
            (13, 12.1, 'Kodiak_Trail')]

    def setUp(self):
        """Create TEST data in CSV format"""

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
        dataset = DAPHandler("http://localhost:8001/",
                             CSVHandler(self.test_file)).dataset
        seq = dataset['sequence']
        dtype = [('index', '<i4'),
                 ('temperature', '<f8'),
                 ('station', 'S40')]
        retrieved_data = [line for line in seq]

        np.testing.assert_array_equal(np.array(retrieved_data, dtype=dtype),
                                      np.array(self.data, dtype=dtype))

    def tearDown(self):
        # Remove test file:
        os.remove(self.test_file)
