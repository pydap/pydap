"""Test DAP4 parsing functions."""

import pydap.parsers.dmr
import os


def load_dmr_file(file_path):
    abs_path = os.path.join(os.path.dirname(__file__), file_path)
    with open(abs_path, 'r') as dmr_file:
        dmr = dmr_file.read()
    dataset = pydap.parsers.dmr.dmr_to_dataset(dmr)
    return dataset


def test_single_scalar():
    """Test a single scalar case."""
    single_scalar_dmr = """<Dataset name="foo"><Int32 name="x"/></Dataset>"""
    dataset = pydap.parsers.dmr.dmr_to_dataset(single_scalar_dmr)
    assert dataset['x'].dtype == '>i4'


def test_coads_climatology2():
    dataset = load_dmr_file('data/dmrs/coads_climatology.nc.dmr')
    assert dataset['SST'].attributes['long_name'] == 'SEA SURFACE TEMPERATURE'
    assert dataset['SST'].attributes['missing_value'] == '-9.99999979e+33'
    assert dataset['AIRT'].shape == (12, 90, 180)
    assert dataset['VWND'].dtype.str == '>f4'


def test_atl03():
    # Contains groups
    dataset = load_dmr_file('data/dmrs/ATL03_20181228015957_13810110_003_01.2var.h5.dmrpp.dmr')
    assert dataset['/gt1r/bckgrd_atlas/bckgrd_int_height'].attributes['contentType'] == 'modelResult'


def test_jpl():
    # Contains groups
    dataset = load_dmr_file('data/dmrs/20220102090000-JPL-L4_GHRSST-SSTfnd-MUR-GLOB-v02.0-fv04.1.dmr')
    assert dataset['sea_ice_fraction'].dimensions == ['time', 'lat', 'lon']


def test_mod05():
    dataset = load_dmr_file('data/dmrs/MOD05_L2.A2019336.2315.061.2019337071952.hdf.dmr')
    assert dataset['Water_Vapor_Infrared'].dimensions == ['Cell_Along_Swath_5km', 'Cell_Across_Swath_5km']





