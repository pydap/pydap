"""Test DAP4 parsing functions."""

import numpy as np
from pydap.parsers.das import add_attributes, parse_das
#from pydap.parsers.dds import build_dataset
from pydap.parsers.dmr import build_dataset_dmr
from pydap.tests.test_parsers_dds import DDS
import unittest
import os

# Examples are taken from https://docs.opendap.org/index.php/DAP4:_Specification_Volume_1.
DMR_single_scalar = """
<Dataset name="foo">
    <Int32 name="x"/>
</Dataset>
"""

with open(os.path.join(os.path.dirname(__file__), './test.02.dap'), 'r') as dap:
    DMR_coads_climatology2 = dap.read()

# It is important to add attributes that have the same
# name as the dimensions of SPEH. This is an edge
# case that can break the das parser.


class TestParseDMR(unittest.TestCase):

    """Test DMR parser."""

#    def setUp(self):
#        """Load a dataset and apply DAS to it."""
#        attributes = parse_das(DMR)
#        add_attributes(self.dataset, attributes)

    def test_single_scalar(self):
        """Test a single scalar case."""
        self.dataset = build_dataset_dmr(DMR_single_scalar)
#        import pdb; pdb.set_trace()
#        self.assertEqual(self.dataset["x"].name, 'x')

    def test_coads_climatology2(self):
        """Test a single scalar case."""
        self.dataset = build_dataset_dmr(DMR_coads_climatology2)
        self.assertEqual(self.dataset['SST'].attributes['long_name'], 'SEA SURFACE TEMPERATURE')
        self.assertEqual(self.dataset['SST'].attributes['missing_value'], '-9.99999979e+33')
        self.assertEqual(self.dataset['AIRT'].shape, ['12', '90', '180'])
        self.assertEqual(self.dataset['SPEH'].dtype.str, '>f4')
#        import pdb; pdb.set_trace()        
        # for v in self.dataset:
        #     print("dataset has " + v)

#        self.assertEqual(self.dataset["x"].name, 'x')


