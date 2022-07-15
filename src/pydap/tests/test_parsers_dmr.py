"""Test DAP4 parsing functions."""

import pydap.parsers.dmr
import os

# Examples are taken from https://docs.opendap.org/index.php/DAP4:_Specification_Volume_1.
single_scalar_dmr = """<Dataset name="foo"><Int32 name="x"/></Dataset>"""

with open(os.path.join(os.path.dirname(__file__), 'data/test.02.dmr'), 'r') as dap:
    coads_climatology2_dmr = dap.read()

with open(os.path.join(os.path.dirname(__file__), 'data/ATL03_20181228015957_13810110_003_01.2var.h5.dmrpp.dmr'), 'r') as dap:
    atl03_dmr = dap.read()


def test_single_scalar():
    """Test a single scalar case."""
    dataset = pydap.parsers.dmr.dmr_to_dataset(single_scalar_dmr)
    assert dataset['x'].dtype == '>i4'


def test_coads_climatology2():
    dataset = pydap.parsers.dmr.dmr_to_dataset(coads_climatology2_dmr)

    assert dataset['SST'].attributes['long_name'] == 'SEA SURFACE TEMPERATURE'
    assert dataset['SST'].attributes['missing_value'] == '-9.99999979e+33'
    assert dataset['AIRT'].shape == [12, 90, 180]
    assert dataset['SPEH'].dtype.str == '>f4'


def test_atl03():
    # Contains groups
    dataset = pydap.parsers.dmr.dmr_to_dataset(atl03_dmr)
    assert dataset['/gt1r/bckgrd_atlas/bckgrd_int_height'].attributes['contentType'] == 'modelResult'




test_single_scalar()