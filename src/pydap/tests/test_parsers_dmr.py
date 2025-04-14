"""Test DAP4 parsing functions."""

import os
import re
import unittest
from xml.etree import ElementTree as ET

import numpy as np

from ..client import open_dmr_file
from ..lib import walk
from ..model import BaseType
from ..parsers.dmr import dmr_to_dataset, get_groups


def load_dmr_file(file_path):
    abs_path = os.path.join(os.path.dirname(__file__), file_path)
    return open_dmr_file(abs_path)


class TestDMRParser(unittest.TestCase):
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
        self.assertEqual(dataset["sea_ice_fraction"].dims, ["/time", "/lat", "/lon"])
        self.assertEqual(dataset.attributes["Conventions"], "CF-1.7")

    def test_mod05(self):
        dataset = load_dmr_file(
            "data/dmrs/MOD05_L2.A2019336.2315.061.2019337071952.hdf.dmr"
        )
        self.assertEqual(
            dataset["Water_Vapor_Infrared"].dims,
            [
                "/Cell_Along_Swath_5km",
                "/Cell_Across_Swath_5km",
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
        names = [key for key in dataset.dimensions.keys()]
        sizes = [v[1] for v in dataset.dimensions.items()]
        self.assertEqual(names, ["time", "nv"])
        self.assertEqual(sizes, [1, 2])

    def tests_named_dimension(self):
        dataset = load_dmr_file("data/dmrs/SimpleGroup.dmr")
        # get only names of dimensions
        names = [key for key in dataset.dimensions.keys()]
        # get all variables/arrays
        variables = []
        for var in walk(dataset, BaseType):
            variables.append(var.name)
        # assert nv is a Global dimension
        self.assertIn("nv", names)
        # assert nv is NOT a variable/array
        self.assertNotIn("nv", variables)

    def tests_FlatGroups(self):
        dataset = load_dmr_file("data/dmrs/SimpleGroupFlat.dmr")
        # pick a single variable Maps
        Groups = dataset.groups()
        Variables = [item for (item, _) in dataset.variables().items()]
        self.assertEqual(Groups, {})
        self.assertEqual(
            Variables,
            [
                "SimpleGroup/Temperature",
                "SimpleGroup/Salinity",
                "SimpleGroup/Y",
                "SimpleGroup/X",
                "time",
                "time_bnds",
            ],
        )

    def test_get_groups(self):
        dmr_file = "data/dmrs/SimpleGroup.dmr"
        abs_path = os.path.join(os.path.dirname(__file__), dmr_file)
        with open(abs_path, "r") as dmr_file:
            dmr = dmr_file.read()
        _dmr = re.sub(' xmlns="[^"]+"', "", dmr, count=1)
        node = ET.fromstring(_dmr)
        groups = get_groups(node)
        assert isinstance(groups, dict)
        assert list(groups.keys()) == ["/SimpleGroup"]
        entry = groups["/SimpleGroup"]
        assert entry["attributes"] == {"Description": "Test group with numerical data"}
        assert entry["dimensions"] == {"Y": 4, "X": 4}
        assert entry["path"] == "/"
        assert entry["Maps"] == ()


class TestAttrsTypesDMRParser(unittest.TestCase):
    """Test parsing a DMR with all types"""

    def test_int8(self):
        dmr = """<Dataset name="foo">\n    <Int32 name="x">\n
                <Attribute name="attr" type="Int8">\n
                            <Value>1</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], int)

    def test_uint8(self):
        dmr = """<Dataset name="foo">\n    <Int32 name="x">\n
                <Attribute name="attr" type="UInt8">\n
                            <Value>1</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], int)

    def test_Char(self):
        dmr = """<Dataset name="foo">\n    <Int32 name="x">\n
                <Attribute name="attr" type="Char">\n
                            <Value>1</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], int)

    def test_int16(self):
        dmr = """<Dataset name="foo">\n    <Int32 name="x">\n
                <Attribute name="attr" type="Int16">\n
                            <Value>1</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], int)

    def test_uint16(self):
        dmr = """<Dataset name="foo">\n    <Int32 name="x">\n
                <Attribute name="attr" type="UInt16">\n
                            <Value>1</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], int)

    def test_int32(self):
        dmr = """<Dataset name="foo">\n    <Int32 name="x">\n
                <Attribute name="attr" type="Int32">\n
                            <Value>1</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], int)

    def test_uint32(self):
        dmr = """<Dataset name="foo">\n    <Int32 name="x">\n
                <Attribute name="attr" type="UInt32">\n
                            <Value>1</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], int)

    def test_int64(self):
        dmr = """<Dataset name="foo">\n    <Int32 name="x">\n
                <Attribute name="attr" type="Int64">\n
                            <Value>1</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], int)

    def test_uint64(self):
        dmr = """<Dataset name="foo">\n    <Int32 name="x">\n
                <Attribute name="attr" type="UInt64">\n
                            <Value>1</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], int)

    def test_float32(self):
        dmr = """<Dataset name="foo">\n    <Int32 name="x">\n
                <Attribute name="attr" type="Float32">\n
                            <Value>1</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], float)

    def test_float64(self):
        dmr = """<Dataset name="foo">\n    <Int32 name="x">\n
                <Attribute name="attr" type="Float64">\n
                            <Value>1</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], float)

    def test_floatNone(self):
        dmr = """<Dataset name="foo">\n    <Int32 name="x">\n
                <Attribute name="attr" type="Float32">\n
                            <Value></Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert ds["x"].attributes["attr"] is None

    def test_TDSfloat64(self):
        dmr = """<Dataset name="foo">\n    <Int32 name="x">\n
                <Attribute name="attr" type="Float64">\n
                            <Value value="0.0"/>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], float)

    def test_multiple_entries(self):
        dmr = """<Dataset name="foo">\n    <Int32 name="x">\n
        <Attribute name="attr" type="Float32">\n
                    <Value>-1</Value>\n        <Value value="1"/>\n</Attribute>\n
                        </Int32>\n</Dataset>"""

        dmr2 = """<Dataset name="foo">\n    <Int32 name="x">\n
        <Attribute name="attr" type="Float32">\n
                    <Value value="-1"/>\n        <Value>1</Value>\n</Attribute>\n
                        </Int32>\n</Dataset>"""

        ds = dmr_to_dataset(dmr)
        ds2 = dmr_to_dataset(dmr2)
        assert ds["x"].attributes["attr"] == [-1.0, 1.0]
        assert ds2["x"].attributes["attr"] == [-1.0, 1.0]

    def test_multiple_entries2(self):
        dmr = """<Dataset name="foo">\n    <Int32 name="x">\n
        <Attribute name="attr" type="Float32" value="100">\n
                    <Value></Value>\n        <Value>2</Value>\n
                            <Value value="1"/>\n</Attribute>\n
                        </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert ds["x"].attributes["attr"] == [100, None, 2.0, 1.0]

    def test_string(self):
        dmr = """<Dataset name="foo">\n    <String name="bears">\n
                <Attribute name="attr" type="Float32">\n
                            <Value></Value>\n        </Attribute>\n
                                </String>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert "bears" in ds.variables()
        assert ds["bears"].dtype == "S128"

    def test_attr_InlineValue(self):
        dmr = """
        <Dataset name="foo">\n
        <String name="bears">\n
            <Attribute name="attr" type="Float32" value="100"/>\n
        </String>\n
        </Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert ds["bears"].attributes["attr"] == 100.0

    def test_escapedcharacters(self):
        dmr = """
        <Dataset name="FamilyNames.h5">\n
            <Group name="Last Names">\n
                <String name="Simpson"/>\n
            </Group>\n
            <Group name="First Names">\n
                <String name="Homer J."/>\n
                <String name="Bart"/>\n
                <String name="Lisa"/>\n
                <String name="Maggie"/>\n
            </Group>\n
            <Group name="Ages">\n
                <String name="35.0"/>\n
                <String name="8.5"/>\n
                <String name="7.1"/>\n
                <String name="2.1"/>\n
            </Group>\n
            <Attribute name='description' type='String' value='hello'/>\n
        </Dataset>
        """
        ds = dmr_to_dataset(dmr)
        assert ds["Last Names"].name == "Last%20Names"
