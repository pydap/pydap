import os

import numpy

from ..client import open_dap_file


def load_dap(file_path):
    abs_path = os.path.join(os.path.dirname(__file__), file_path)
    return open_dap_file(abs_path)


def test_jpl1():
    file_path = (
        "data/daps/20220102090000-JPL-L4_GHRSST-SSTfnd-MUR-GLOB-v02.0-fv04.1_subset.dap"
    )
    dataset = load_dap(file_path)
    values = dataset["sea_ice_fraction"].data[0, 0, 0:2]
    expected = numpy.array([98, 98], dtype="int8")
    assert numpy.array_equal(values, expected)


def test_jpl2():
    file_path = (
        "data/daps/20220531090000-JPL-L4_GHRSST-SSTfnd-MUR-GLOB-v02.0-fv04.1.dap"
    )
    dataset = load_dap(file_path)
    values = dataset["lon"].data[0:5]
    expected = numpy.array(
        [-179.99, -179.98, -179.97, -179.96, -179.95], dtype="float32"
    )
    assert numpy.array_equal(values, expected)


def test_coads():
    file_path = "data/daps/coads_climatology.nc.dap"
    dataset = load_dap(file_path)
    values = dataset["SST"][0, 2, 0:3].data
    expected = numpy.array([0.12833333, -0.05000002, -0.06363636], dtype="float32")
    numpy.testing.assert_almost_equal(values, expected)


def test_my1qnd1():
    fname = "data/daps/MY1DQND1.sst.ADD2005001.040.2006011070802.hdf.dap"
    load_dap(fname)


if __name__ == "__main__":
    pass
    # test_my1qnd1()
    # test_coads()
