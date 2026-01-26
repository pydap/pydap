"""Test DAP4 parsing functions."""

import os
import re
import unittest
from xml.etree import ElementTree as ET

import numpy as np
import pytest

from ..client import open_dmr_file
from ..lib import walk
from ..model import BaseType
from ..parsers.dmr import DMRParser, DMRPPParser, dmr_to_dataset, get_groups


def load_dmr_file(file_path):
    abs_path = os.path.join(os.path.dirname(__file__), file_path)
    return open_dmr_file(abs_path)


def read_dmr_file(file_path):
    abs_path = os.path.join(os.path.dirname(__file__), file_path)
    with open(abs_path, "r") as dmr_file:
        dmr = dmr_file.read()
    _dmr = re.sub(' xmlns="[^"]+"', "", dmr, count=1)
    return ET.fromstring(_dmr)


DMRPPTest_file = os.path.join(
    os.path.dirname(__file__), "data/dmrs/TestGroupData.nc4.dmrpp"
)


class TestDMRParser(unittest.TestCase):
    """Test parsing a DMR."""

    def test_single_scalar(self):
        """Test a single scalar case."""
        single_scalar_dmr = (
            """<Dataset name="foo" dmrVersion="1.0"><Int32 name="x"/></Dataset>"""
        )
        dataset = dmr_to_dataset(single_scalar_dmr)
        self.assertEqual(dataset["x"].dtype, "int32")

    def test_missing_value(self):
        """Test cases with missing value."""
        NAN_dmr = """<Dataset name="foo" dmrVersion="1.0">\n    <Int32 name="x">\n
                <Attribute name="missing_value" type="Float32">\n
                            <Value>NaN</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        INF_dmr = """<Dataset name="foo" dmrVersion="1.0">\n    <Int32 name="x">\n
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
        byte_dmr = """<Dataset name="foo" dmrVersion="1.0">\n    <Int32 name="x">\n
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
        self.assertEqual(dataset["VWND"].dtype.str, "<f4")

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
        node = read_dmr_file(dmr_file)
        groups = get_groups(node)
        assert isinstance(groups, dict)
        assert list(groups.keys()) == ["/SimpleGroup"]
        entry = groups["/SimpleGroup"]
        assert entry["attributes"] == {"Description": "Test group with numerical data"}
        assert entry["dimensions"] == {"Y": 4, "X": 4}
        assert entry["path"] == "/"
        assert entry["Maps"] == ()

    def test_nested_groups(self):
        dmr_file = "data/dmrs/Nested_Group.dmr"
        node = read_dmr_file(dmr_file)
        groups = get_groups(node)
        assert list(groups.keys()) == ["/Group1", "/Group1/subgroup1"]
        assert groups["/Group1"]["dimensions"] == {"lat": 1, "lon": 2}
        assert groups["/Group1/subgroup1"]["dimensions"] == {"lat": 2, "lon": 2}


class TestAttrsTypesDMRParser(unittest.TestCase):
    """Test parsing a DMR with all types"""

    def test_int8(self):
        dmr = """<Dataset name="foo" dmrVersion="1.0">\n    <Int32 name="x">\n
                <Attribute name="attr" type="Int8">\n
                            <Value>1</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], int)

    def test_uint8(self):
        dmr = """<Dataset name="foo" dmrVersion="1.0">\n    <Int32 name="x">\n
                <Attribute name="attr" type="UInt8">\n
                            <Value>1</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], int)

    def test_Char(self):
        dmr = """<Dataset name="foo" dmrVersion="1.0">\n    <Int32 name="x">\n
                <Attribute name="attr" type="Char">\n
                            <Value>1</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], int)

    def test_int16(self):
        dmr = """<Dataset name="foo" dmrVersion="1.0">\n    <Int32 name="x">\n
                <Attribute name="attr" type="Int16">\n
                            <Value>1</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], int)

    def test_uint16(self):
        dmr = """<Dataset name="foo" dmrVersion="1.0">\n    <Int32 name="x">\n
                <Attribute name="attr" type="UInt16">\n
                            <Value>1</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], int)

    def test_int32(self):
        dmr = """<Dataset name="foo" dmrVersion="1.0">\n    <Int32 name="x">\n
                <Attribute name="attr" type="Int32">\n
                            <Value>1</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], int)

    def test_uint32(self):
        dmr = """<Dataset name="foo" dmrVersion="1.0">\n    <Int32 name="x">\n
                <Attribute name="attr" type="UInt32">\n
                            <Value>1</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], int)

    def test_int64(self):
        dmr = """<Dataset name="foo" dmrVersion="1.0">\n    <Int32 name="x">\n
                <Attribute name="attr" type="Int64">\n
                            <Value>1</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], int)

    def test_uint64(self):
        dmr = """<Dataset name="foo" dmrVersion="1.0">\n    <Int32 name="x">\n
                <Attribute name="attr" type="UInt64">\n
                            <Value>1</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], int)

    def test_float32(self):
        dmr = """<Dataset name="foo" dmrVersion="1.0">\n    <Int32 name="x">\n
                <Attribute name="attr" type="Float32">\n
                            <Value>1</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], float)

    def test_float64(self):
        dmr = """<Dataset name="foo" dmrVersion="1.0">\n    <Int32 name="x">\n
                <Attribute name="attr" type="Float64">\n
                            <Value>1</Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], float)

    def test_floatNone(self):
        dmr = """<Dataset name="foo" dmrVersion="1.0">\n    <Int32 name="x">\n
                <Attribute name="attr" type="Float32">\n
                            <Value></Value>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert ds["x"].attributes["attr"] is None

    def test_TDSfloat64(self):
        dmr = """<Dataset name="foo" dmrVersion="1.0">\n    <Int32 name="x">\n
                <Attribute name="attr" type="Float64">\n
                            <Value value="0.0"/>\n        </Attribute>\n
                                </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert isinstance(ds["x"].attributes["attr"], float)

    def test_multiple_entries(self):
        dmr = """<Dataset name="foo" dmrVersion="1.0">\n    <Int32 name="x">\n
        <Attribute name="attr" type="Float32">\n
                    <Value>-1</Value>\n        <Value value="1"/>\n</Attribute>\n
                        </Int32>\n</Dataset>"""

        dmr2 = """<Dataset name="foo" dmrVersion="1.0">\n    <Int32 name="x">\n
        <Attribute name="attr" type="Float32">\n
                    <Value value="-1"/>\n        <Value>1</Value>\n</Attribute>\n
                        </Int32>\n</Dataset>"""

        ds = dmr_to_dataset(dmr)
        ds2 = dmr_to_dataset(dmr2)
        assert ds["x"].attributes["attr"] == [-1.0, 1.0]
        assert ds2["x"].attributes["attr"] == [-1.0, 1.0]

    def test_multiple_entries2(self):
        dmr = """<Dataset name="foo" dmrVersion="1.0">\n    <Int32 name="x">\n
        <Attribute name="attr" type="Float32" value="100">\n
                    <Value></Value>\n        <Value>2</Value>\n
                            <Value value="1"/>\n</Attribute>\n
                        </Int32>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert ds["x"].attributes["attr"] == [100, None, 2.0, 1.0]

    def test_string(self):
        dmr = """<Dataset name="foo" dmrVersion="1.0">\n    <String name="bears">\n
                <Attribute name="attr" type="Float32">\n
                            <Value></Value>\n        </Attribute>\n
                                </String>\n</Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert "bears" in ds.variables()
        assert ds["bears"].dtype == "S128"

    def test_attr_InlineValue(self):
        dmr = """
        <Dataset name="foo" dmrVersion="1.0">\n
        <String name="bears">\n
            <Attribute name="attr" type="Float32" value="100"/>\n
        </String>\n
        </Dataset>"""
        ds = dmr_to_dataset(dmr)
        assert ds["bears"].attributes["attr"] == 100.0

    def test_escapedcharacters(self):
        dmr = """
        <Dataset name="FamilyNames.h5" dmrVersion="1.0">\n
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


@pytest.mark.parametrize(
    "ns, expected",
    [
        ("dap", "http://xml.opendap.org/ns/DAP/4.0#"),
        ("dmrpp", "http://xml.opendap.org/dap/dmrpp/1.0.0#"),
        ("xmlns", "http://www.w3.org/XML/1998/namespace"),
    ],
)
def dmrpp_parse(TestGroupDMRPP, ns, expected):
    dmrpp_instance = DMRPPParser(root=TestGroupDMRPP.read())
    assert dmrpp_instance._NS[ns] == expected


@pytest.mark.parametrize(
    "filepath, expected",
    [
        (None, "http://test.opendap.org/opendap/dap4/TestGroupData.nc4.h5"),
        (
            os.path.join(os.path.dirname(__file__), "FakeFileName.nc4"),
            os.path.join(os.path.dirname(__file__), "FakeFileName.nc4"),
        ),
    ],
)
def test_datafile_path(filepath, expected):
    """Test that when filepath not given, extract the filepath from the DMRpp. But if
    filepath is given, user provided filepath takes precedence.
    """
    dmrpp_instance = DMRPPParser(
        root=ET.fromstring(open(DMRPPTest_file).read()), data_filepath=filepath
    )
    assert dmrpp_instance.data_filepath == expected


@pytest.mark.parametrize(
    "Group, parsed_dims",
    [
        ("/", [{"time": 1}]),
        ("SimpleGroup", [{"Y": 40}, {"X": 40}]),
        ("data", [{"lat": 25}, {"lon": 53}]),
    ],
)
def test_parsed_dim_tag(Group, parsed_dims):
    """Check that dmrpp parses correctly the dimensions defined within
    each group (including the root group).
    """
    dmrpp_instance = DMRPPParser(root=ET.fromstring(open(DMRPPTest_file).read()))
    dim_tags = dmrpp_instance._find_dimension_tags(dmrpp_instance.find_node_fqn(Group))
    dims = [dmrpp_instance._parse_dim(dim_tag) for dim_tag in dim_tags]
    assert dims == parsed_dims


@pytest.mark.parametrize(
    "var_path, expected",
    [
        (
            "/SimpleGroup/Temperature",
            {
                "0.0.0": {
                    "path": "http://test.opendap.org/opendap/dap4/TestGroupData.nc4.h5",
                    "offset": 12762,
                    "length": 6400,
                }
            },
        ),
        (
            "/SimpleGroup/Salinity",
            {
                "0.0.0": {
                    "path": "http://test.opendap.org/opendap/dap4/TestGroupData.nc4.h5",
                    "offset": 19162,
                    "length": 6400,
                }
            },
        ),
        (
            "/data/air",
            {
                "0.0.0": {
                    "path": "http://test.opendap.org/opendap/dap4/TestGroupData.nc4.h5",
                    "offset": 30129,
                    "length": 2650,
                }
            },
        ),
    ],
)
def test_dmrpp_chunkmanifest_variable(var_path, expected):
    """Test that the chunk manifest matches the expected value. All variables have
    data that were created with single chunks.
    """
    dmrpp_instance = DMRPPParser(root=ET.fromstring(open(DMRPPTest_file).read()))
    var_tag = dmrpp_instance.find_node_fqn(var_path)
    chunk_manifest = dmrpp_instance._parse_variable(var_tag)["chunkmanifest"]

    assert chunk_manifest == expected


def test_dmrpp_parser_variable_keys():
    """Test elements of parsed variable dictionary"""
    dmrpp_instance = DMRPPParser(root=ET.fromstring(open(DMRPPTest_file).read()))
    var_tag = dmrpp_instance.find_node_fqn("SimpleGroup/Temperature")
    parsed_variable_elements = list(dmrpp_instance._parse_variable(var_tag).keys())
    expected_elements = [
        "shape",
        "data_type",
        "chunk_shape",
        "codecs",
        "dimension_names",
        "fqn_dims",
        "Maps",
        "attributes",
        "fill_value",
        "chunkmanifest",
    ]
    assert parsed_variable_elements == expected_elements


@pytest.mark.parametrize(
    "var_path, expected",
    [
        ("/data/air", {"time": 1, "lat": 25, "lon": 53}),
        ("/SimpleGroup/Temperature", {"time": 1, "Y": 40, "X": 40}),
        ("/SimpleGroup/Salinity", {"time": 1, "Y": 40, "X": 40}),
    ],
)
def test_dmrpp_dimension_names_variable(var_path, expected):
    dmrpp_instance = DMRPPParser(root=ET.fromstring(open(DMRPPTest_file).read()))
    var_tag = dmrpp_instance.find_node_fqn(var_path)
    dimension_names = dmrpp_instance._parse_variable(var_tag)["dimension_names"]
    assert dimension_names == expected


@pytest.mark.parametrize(
    "var_path, expected",
    [
        ("/data/air", ["/time", "/data/lat", "/data/lon"]),
        ("/SimpleGroup/Temperature", ["/time", "/SimpleGroup/Y", "/SimpleGroup/X"]),
        ("/SimpleGroup/Salinity", ["/time", "/SimpleGroup/Y", "/SimpleGroup/X"]),
    ],
)
def test_dmrpp_fqn_dims_variable(var_path, expected):
    dmrpp_instance = DMRPPParser(root=ET.fromstring(open(DMRPPTest_file).read()))
    var_tag = dmrpp_instance.find_node_fqn(var_path)
    dimension_names = dmrpp_instance._parse_variable(var_tag)["fqn_dims"]
    assert dimension_names == expected


@pytest.mark.parametrize(
    "var_path, expected",
    [
        ("/data/air", ["/time", "/data/lat", "/data/lon"]),
        ("/SimpleGroup/Temperature", ["/time", "/SimpleGroup/Y", "/SimpleGroup/X"]),
        ("/SimpleGroup/Salinity", ["/time", "/SimpleGroup/Y", "/SimpleGroup/X"]),
    ],
)
def test_dmrpp_Maps_variable(var_path, expected):
    dmrpp_instance = DMRPPParser(root=ET.fromstring(open(DMRPPTest_file).read()))
    var_tag = dmrpp_instance.find_node_fqn(var_path)
    dimension_names = dmrpp_instance._parse_variable(var_tag)["Maps"]
    assert dimension_names == expected


@pytest.mark.parametrize(
    "var_path, expected",
    [
        ("/data/air", (1, 25, 53)),
        ("/SimpleGroup/Temperature", (1, 40, 40)),
        ("/SimpleGroup/Salinity", (1, 40, 40)),
    ],
)
def test_dmrpp_shape_parsedvariable(var_path, expected):
    dmrpp_instance = DMRPPParser(root=ET.fromstring(open(DMRPPTest_file).read()))
    var_tag = dmrpp_instance.find_node_fqn(var_path)
    assert dmrpp_instance._parse_variable(var_tag)["shape"] == expected


@pytest.mark.parametrize(
    "var_path, expected",
    [
        ("/data/air", np.dtype(np.int16)),
        ("/SimpleGroup/Temperature", np.dtype(np.float32)),
        ("/SimpleGroup/Salinity", np.dtype(np.float32)),
    ],
)
def test_dmrpp_datatype_parsedvariable(var_path, expected):
    dmrpp_instance = DMRPPParser(root=ET.fromstring(open(DMRPPTest_file).read()))
    var_tag = dmrpp_instance.find_node_fqn(var_path)
    assert dmrpp_instance._parse_variable(var_tag)["data_type"] == expected


@pytest.mark.parametrize(
    "var_path, expected",
    [
        ("/data/air", (1, 25, 53)),
        ("/SimpleGroup/Temperature", (1, 40, 40)),
        ("/SimpleGroup/Salinity", (1, 40, 40)),
    ],
)
def test_dmrpp_chunk_shape_parsedvariable(var_path, expected):
    """Data has a single chunk."""
    dmrpp_instance = DMRPPParser(root=ET.fromstring(open(DMRPPTest_file).read()))
    var_tag = dmrpp_instance.find_node_fqn(var_path)
    assert dmrpp_instance._parse_variable(var_tag)["chunk_shape"] == expected


def test_dmrpp_attributes_parsedvariable():
    """Test attributes keys and some its elements"""
    dmrpp_instance = DMRPPParser(root=ET.fromstring(open(DMRPPTest_file).read()))
    var_tag = dmrpp_instance.find_node_fqn("/data/air")
    attrs = dmrpp_instance._parse_variable(var_tag)["attributes"]

    expected_keys = [
        "long_name",
        "units",
        "precision",
        "GRIB_id",
        "GRIB_name",
        "var_desc",
        "dataset",
        "level_desc",
        "statistic",
        "parent_stat",
        "actual_range",
        "scale_factor",
    ]

    assert list(attrs.keys()) == expected_keys

    actual_range = [round(val, 6) for val in attrs["actual_range"]]
    assert actual_range == [185.160004, 322.100006]


def test_fill_value_parsedvariable():
    """Test that demonstrates how fill values may appear for a given variable

    In addition, this DMRPP has a chunk element with a fill value to be set as nan.
    Asserts that is the case.
    """
    dmrpp_instance = DMRPPParser(root=ET.fromstring(open(DMRPPTest_file).read()))
    var_tag = dmrpp_instance.find_node_fqn("/SimpleGroup/Temperature")
    parsed_var = dmrpp_instance._parse_variable(var_tag)
    assert "_FillValue" in parsed_var["attributes"]
    assert "fill_value" in parsed_var
    assert np.isnan(parsed_var["fill_value"])


@pytest.mark.parametrize(
    "Group, skip_variables, expected_parsed_variables",
    [
        ("/", None, ["time"]),
        ("/SimpleGroup", ("Temperature", "Salinity"), ["Y", "X"]),
        ("/data", ("lat", "lon"), ["air"]),
    ],
)
def test_parsed_dataset(Group, skip_variables, expected_parsed_variables):
    """testing elements of parsed dataset"""
    dmrpp_instance = DMRPPParser(
        root=ET.fromstring(open(DMRPPTest_file).read()), skip_variables=skip_variables
    )
    variables, _ = dmrpp_instance._parse_dataset(dmrpp_instance.find_node_fqn(Group))
    assert list(variables.keys()) == expected_parsed_variables


@pytest.mark.parametrize(
    "url, expected_dmrVersion",
    [
        ("""<Dataset name="foo" dmrVersion="1.0"><Int32 name="x"/></Dataset>""", "1.0"),
        ("""<Dataset name="foo" dmrVersion="2.0"><Int32 name="x"/></Dataset>""", "2.0"),
    ],
)
def test_dmr_version(url, expected_dmrVersion):
    dmr_instance = DMRParser(url)
    assert dmr_instance.dmrVersion == expected_dmrVersion


def test_tds_dmrVersion2():
    dmr = """
    <Dataset name="FamilyNames.h5" dmrVersion="1.0">\n
        <Attribute name='_NCProperties' type='String' value='version=2,
        netcdf=4.9.2,hdf5=1.14.4'/>\n
        <Attribute name='_DAP4_Little_Endian' type='UInt8' value="1"/>\n
    </Dataset>
    """
    dmr_instance = DMRParser(dmr)
    assert dmr_instance.dmrVersion == "2.0"


def test_nested_empty_groups_dmrVersion2():
    """Test that empty nested groups are parsed correctly with dmrVersion=2."""
    nested_empty_groups_dmr = """
    <Dataset dapVersion="4.0" dmrVersion="2.0" name="all_aligned_child_nodes.nc.h5">
        <Group name="Group1">
            <Group name="subgroup1">
                <Dimension name="lat" size="1"/>
                <Dimension name="lon" size="2"/>
                <Float64 name="subgroup_1_var">
                    <Dim name="/Group1/subgroup1/lat"/>
                    <Dim name="/Group1/subgroup1/lon"/>
                </Float64>
            </Group>
        </Group>
    </Dataset>
    """
    dataset = dmr_to_dataset(nested_empty_groups_dmr)
    assert set(["Group1", "subgroup1"]).issubset(dataset.groups().keys())
