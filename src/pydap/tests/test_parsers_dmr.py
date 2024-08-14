"""Test DAP4 parsing functions."""

import os
import unittest

import numpy as np

from ..lib import walk
from ..model import BaseType
from ..parsers.dmr import dmr_to_dataset


def load_dmr_file(file_path):
    abs_path = os.path.join(os.path.dirname(__file__), file_path)
    with open(abs_path, "r") as dmr_file:
        dmr = dmr_file.read()
    dataset = dmr_to_dataset(dmr)
    return dataset


class DMRParser(unittest.TestCase):
    """Test parsing a DMR."""

    def test_single_scalar(self):
        """Test a single scalar case."""
        single_scalar_dmr = """<Dataset name="foo"><Int32 name="x"/></Dataset>"""
        dataset = dmr_to_dataset(single_scalar_dmr)
        self.assertEqual(dataset["x"].dtype, ">i4")

    def test_missing_value(self):
        """Test cases with missing value."""
        NAN_dmr = """<Dataset name="foo">\n    <Int32 name="x">\n
                <Attribute name="missing_value" type="Float32">\n
                            <Value>NaN</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        INF_dmr = """<Dataset name="foo">\n    <Int32 name="x">\n
                <Attribute name="missing_value" type="Float32">\n
                            <Value>Inf</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""

        dataset_nan = dmr_to_dataset(NAN_dmr)
        dataset_inf = dmr_to_dataset(INF_dmr)

        X_nan = dataset_nan["x"]
        X_inf = dataset_inf["x"]
        self.assertEqual(np.isnan(X_nan.attributes["missing_value"]), True)
        self.assertEqual(np.isinf(X_inf.attributes["missing_value"]), True)

    def test_attribute_warning(self):
        byte_dmr = """<Dataset name="foo">\n    <Int32 name="x">\n
                <Attribute name="missing_value" type="Byte">\n
                            <Value>x00</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        with self.assertRaises(Warning):
            dmr_to_dataset(byte_dmr)

    def test_coads_climatology2(self):
        dataset = load_dmr_file("data/dmrs/coads_climatology.nc.dmr")
        self.assertEqual(
            dataset["SST"].attributes["long_name"], "SEA SURFACE TEMPERATURE"
        )
        self.assertEqual(dataset["SST"].attributes["missing_value"], -9.99999979e33)
        self.assertEqual(dataset["AIRT"].shape, (12, 90, 180))
        self.assertEqual(dataset["VWND"].dtype.str, ">f4")

    def test_atl03(self):
        # Contains groups
        dataset = load_dmr_file(
            "data/dmrs/ATL03_20181228015957_13810110_003_01.2var.h5.dmrpp.dmr"
        )
        self.assertEqual(
            dataset["/gt1r/bckgrd_atlas/bckgrd_int_height"].attributes["contentType"],
            "modelResult",
        )

    def test_jpl(self):
        # Contains groups
        dataset = load_dmr_file(
            "data/dmrs/20220102090000-JPL-L4_GHRSST-SSTfnd-MUR-GLOB-v02.0-fv04.1.dmr"
        )
        self.assertEqual(dataset["sea_ice_fraction"].dimensions, ["time", "lat", "lon"])

    def test_mod05(self):
        dataset = load_dmr_file(
            "data/dmrs/MOD05_L2.A2019336.2315.061.2019337071952.hdf.dmr"
        )
        self.assertEqual(
            dataset["Water_Vapor_Infrared"].dimensions,
            [
                "Cell_Along_Swath_5km",
                "Cell_Across_Swath_5km",
            ],
        )

    def test_SWOT(self):
        dataset = load_dmr_file("data/dmrs/SWOT_GPR.dmr")
        # pick a single variable Maps
        maps = ("/data_01/longitude", "/data_01/latitude")
        self.assertEqual(dataset["data_01/ku/swh_ocean"].Maps, maps)

    def tests_global_dimensions(self):
        dataset = load_dmr_file("data/dmrs/SimpleGroup.dmr")
        # pick a single variable Maps
        names = tuple([item[0] for item in dataset.dimensions])
        sizes = tuple([item[1] for item in dataset.dimensions])
        self.assertEqual(names, ("time", "nv"))
        self.assertEqual(sizes, (1, 2))

    def tests_named_dimension(self):
        dataset = load_dmr_file("data/dmrs/SimpleGroup.dmr")
        # get only names of dimensions
        names = tuple([item[0] for item in dataset.dimensions])
        # get all variables/arrays
        variables = []
        for var in walk(dataset, BaseType):
            variables.append(var.name)
        # assert nv is a Global dimension
        self.assertIn("nv", names)
        # assert nv is NOT a variable/array
        self.assertNotIn("nv", variables)
