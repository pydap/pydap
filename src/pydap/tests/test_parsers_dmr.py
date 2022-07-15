"""Test DAP4 parsing functions."""

from pydap.parsers.dmr import dmr_to_dataset

import unittest
import os

# Examples are taken from https://docs.opendap.org/index.php/DAP4:_Specification_Volume_1.
DMR_single_scalar = """
<Dataset name="foo">
    <Int32 name="x"/>
</Dataset>
"""

with open(os.path.join(os.path.dirname(__file__), 'data/test.02.dmr'), 'r') as dap:
    DMR_coads_climatology2 = dap.read()

# It is important to add attributes that have the same
# name as the dimensions of SPEH. This is an edge
# case that can break the das parser.


class TestParseDMR(unittest.TestCase):

    """Test DMR parser."""

    def test_single_scalar(self):
        """Test a single scalar case."""
        self.dataset = dmr_to_dataset(DMR_single_scalar)

    def test_coads_climatology2(self):
        """Test a single scalar case."""
        self.dataset = dmr_to_dataset(DMR_coads_climatology2)
        self.assertEqual(self.dataset['SST'].attributes['long_name'], 'SEA SURFACE TEMPERATURE')
        self.assertEqual(self.dataset['SST'].attributes['missing_value'], '-9.99999979e+33')
        self.assertEqual(self.dataset['AIRT'].shape, [12, 90, 180])
        self.assertEqual(self.dataset['SPEH'].dtype.str, '>f4')



