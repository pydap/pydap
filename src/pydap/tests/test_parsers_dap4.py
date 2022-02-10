"""Test DAP4 parsing functions."""

import numpy as np
from pydap.parsers.das import add_attributes, parse_das
#from pydap.parsers.dds import build_dataset
from pydap.parsers.dmr import build_dataset_dmr
from pydap.tests.test_parsers_dds import DDS
import unittest

# Examples are taken from https://docs.opendap.org/index.php/DAP4:_Specification_Volume_1.
DMR_single_scalar = """<Dataset name="foo">
<Int32 name="x"/>
</Dataset>
"""

DMR_coads_climatology2 = """<Dataset xmlns="http://xml.opendap.org/ns/DAP/4.0#" xml:base="http://test.opendap.org:8080/opendap/hyrax/data/nc/coads_climatology2.nc" dapVersion="4.0" dmrVersion="1.0" name="coads_climatology2.nc">
<Dimension name="COADSX" size="180"/>
<Dimension name="COADSY" size="90"/>
<Dimension name="TIME" size="12"/>
<Float64 name="COADSX">
<Dim name="/COADSX"/>
<Attribute name="units" type="String">
<Value>degrees_east</Value>
</Attribute>
<Attribute name="modulo" type="String">
<Value> </Value>
</Attribute>
<Attribute name="point_spacing" type="String">
<Value>even</Value>
</Attribute>
</Float64>
<Float64 name="COADSY">
<Dim name="/COADSY"/>
<Attribute name="units" type="String">
<Value>degrees_north</Value>
</Attribute>
<Attribute name="point_spacing" type="String">
<Value>even</Value>
</Attribute>
</Float64>
<Float64 name="TIME">
<Dim name="/TIME"/>
<Attribute name="units" type="String">
<Value>hour since 0000-01-01 00:00:00</Value>
</Attribute>
<Attribute name="time_origin" type="String">
<Value>1-JAN-0000 00:00:00</Value>
</Attribute>
<Attribute name="modulo" type="String">
<Value> </Value>
</Attribute>
</Float64>
<Float32 name="SST">
<Dim name="/TIME"/>
<Dim name="/COADSY"/>
<Dim name="/COADSX"/>
<Attribute name="missing_value" type="Float32">
<Value>-9.99999979e+33</Value>
</Attribute>
<Attribute name="_FillValue" type="Float32">
<Value>-9.99999979e+33</Value>
</Attribute>
<Attribute name="long_name" type="String">
<Value>SEA SURFACE TEMPERATURE</Value>
</Attribute>
<Attribute name="history" type="String">
<Value>From coads_climatology</Value>
</Attribute>
<Attribute name="units" type="String">
<Value>Deg C</Value>
</Attribute>
<Map name="/TIME"/>
<Map name="/COADSY"/>
<Map name="/COADSX"/>
</Float32>
<Float32 name="AIRT">
<Dim name="/TIME"/>
<Dim name="/COADSY"/>
<Dim name="/COADSX"/>
<Attribute name="missing_value" type="Float32">
<Value>-9.99999979e+33</Value>
</Attribute>
<Attribute name="_FillValue" type="Float32">
<Value>-9.99999979e+33</Value>
</Attribute>
<Attribute name="long_name" type="String">
<Value>AIR TEMPERATURE</Value>
</Attribute>
<Attribute name="history" type="String">
<Value>From coads_climatology</Value>
</Attribute>
<Attribute name="units" type="String">
<Value>DEG C</Value>
</Attribute>
<Map name="/TIME"/>
<Map name="/COADSY"/>
<Map name="/COADSX"/>
</Float32>
<Float32 name="SPEH">
<Dim name="/TIME"/>
<Dim name="/COADSY"/>
<Dim name="/COADSX"/>
<Attribute name="missing_value" type="Float32">
<Value>-9.99999979e+33</Value>
</Attribute>
<Attribute name="_FillValue" type="Float32">
<Value>-9.99999979e+33</Value>
</Attribute>
<Attribute name="long_name" type="String">
<Value>SPECIFIC HUMIDITY</Value>
</Attribute>
<Attribute name="history" type="String">
<Value>From coads_climatology</Value>
</Attribute>
<Attribute name="units" type="String">
<Value>G/KG</Value>
</Attribute>
<Map name="/TIME"/>
<Map name="/COADSY"/>
<Map name="/COADSX"/>
</Float32>
<Float32 name="WSPD">
<Dim name="/TIME"/>
<Dim name="/COADSY"/>
<Dim name="/COADSX"/>
<Attribute name="missing_value" type="Float32">
<Value>-9.99999979e+33</Value>
</Attribute>
<Attribute name="_FillValue" type="Float32">
<Value>-9.99999979e+33</Value>
</Attribute>
<Attribute name="long_name" type="String">
<Value>WIND SPEED</Value>
</Attribute>
<Attribute name="history" type="String">
<Value>From coads_climatology</Value>
</Attribute>
<Attribute name="units" type="String">
<Value>M/S</Value>
</Attribute>
<Map name="/TIME"/>
<Map name="/COADSY"/>
<Map name="/COADSX"/>
</Float32>
<Float32 name="UWND">
<Dim name="/TIME"/>
<Dim name="/COADSY"/>
<Dim name="/COADSX"/>
<Attribute name="missing_value" type="Float32">
<Value>-9.99999979e+33</Value>
</Attribute>
<Attribute name="_FillValue" type="Float32">
<Value>-9.99999979e+33</Value>
</Attribute>
<Attribute name="long_name" type="String">
<Value>ZONAL WIND</Value>
</Attribute>
<Attribute name="history" type="String">
<Value>From coads_climatology</Value>
</Attribute>
<Attribute name="units" type="String">
<Value>M/S</Value>
</Attribute>
<Map name="/TIME"/>
<Map name="/COADSY"/>
<Map name="/COADSX"/>
</Float32>
<Float32 name="VWND">
<Dim name="/TIME"/>
<Dim name="/COADSY"/>
<Dim name="/COADSX"/>
<Attribute name="missing_value" type="Float32">
<Value>-9.99999979e+33</Value>
</Attribute>
<Attribute name="_FillValue" type="Float32">
<Value>-9.99999979e+33</Value>
</Attribute>
<Attribute name="long_name" type="String">
<Value>MERIDIONAL WIND</Value>
</Attribute>
<Attribute name="history" type="String">
<Value>From coads_climatology</Value>
</Attribute>
<Attribute name="units" type="String">
<Value>M/S</Value>
</Attribute>
<Map name="/TIME"/>
<Map name="/COADSY"/>
<Map name="/COADSX"/>
</Float32>
<Float32 name="SLP">
<Dim name="/TIME"/>
<Dim name="/COADSY"/>
<Dim name="/COADSX"/>
<Attribute name="missing_value" type="Float32">
<Value>-9.99999979e+33</Value>
</Attribute>
<Attribute name="_FillValue" type="Float32">
<Value>-9.99999979e+33</Value>
</Attribute>
<Attribute name="long_name" type="String">
<Value>SEA LEVEL PRESSURE</Value>
</Attribute>
<Attribute name="history" type="String">
<Value>From coads_climatology</Value>
</Attribute>
<Attribute name="units" type="String">
<Value>MB</Value>
</Attribute>
<Map name="/TIME"/>
<Map name="/COADSY"/>
<Map name="/COADSX"/>
</Float32>
<Attribute name="NC_GLOBAL" type="Container">
<Attribute name="history" type="String">
<Value>FERRET V5.22 11-Jan-01</Value>
</Attribute>
</Attribute>
<Attribute name="DODS_EXTRA" type="Container">
<Attribute name="Unlimited_Dimension" type="String">
<Value>TIME</Value>
</Attribute>
</Attribute>
</Dataset>
"""

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


