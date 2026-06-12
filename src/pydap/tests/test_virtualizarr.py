import os
import textwrap
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import pytest
import requests

from pydap.virtualizarr.parser import DMRPPParser  # DMRParser,

DMRPPTest_file = os.path.join(
    os.path.dirname(__file__), "data/dmrs/TestGroupData.nc4.dmrpp"
)

DMRPPTest_file2 = os.path.join(os.path.dirname(__file__), "data/dmrs/MOD13Q1.hdf.dmrpp")

DMRPPTest_file3 = os.path.join(
    os.path.dirname(__file__), "data/dmrs/fill_value_scalar_no_chunks.nc4.dmrpp"
)
DMRPPTest_file4 = os.path.join(os.path.dirname(__file__), "data/dmrs/air.nc.dmrpp")
DMRPPTest_file5 = os.path.join(
    os.path.dirname(__file__), "data/dmrs/air_groups.nc.dmrpp"
)


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
        (None, "TestGroupData.nc4.h5"),
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
    "file, var_path, expected",
    [
        (
            DMRPPTest_file,
            "/SimpleGroup/Temperature",
            {
                "0.0.0": {
                    "path": "TestGroupData.nc4.h5",
                    "offset": 12762,
                    "length": 6400,
                }
            },
        ),
        (
            DMRPPTest_file,
            "/SimpleGroup/Salinity",
            {
                "0.0.0": {
                    "path": "TestGroupData.nc4.h5",
                    "offset": 19162,
                    "length": 6400,
                }
            },
        ),
        (
            DMRPPTest_file2,
            "/MODIS_Grid_16DAY_250m_500m_VI/XDim",
            {
                "0": {
                    "path": "/sidecar/MOD13Q1/1.hdf_mvs.h5",
                    "offset": 138734334,
                    "length": 6748,
                },
                "1": {
                    "path": "/sidecar/MOD13Q1/2.hdf_mvs.h5",
                    "offset": 138741082,
                    "length": 6709,
                },
                "2": {
                    "path": "/sidecar/MOD13Q1/3.hdf_mvs.h5",
                    "offset": 138747791,
                    "length": 6695,
                },
                "3": {
                    "path": "/sidecar/MOD13Q1/4.hdf_mvs.h5",
                    "offset": 138754486,
                    "length": 6495,
                },
                "4": {
                    "path": "/sidecar/MOD13Q1/5.hdf_mvs.h5",
                    "offset": 138760981,
                    "length": 4224,
                },
            },
        ),
        (
            DMRPPTest_file,
            "/data/air",
            {
                "0.0.0": {
                    "path": "TestGroupData.nc4.h5",
                    "offset": 30129,
                    "length": 2650,
                }
            },
        ),
        (
            DMRPPTest_file2,
            "/MODIS_Grid_16DAY_250m_500m_VI/eos_cf_projection",
            {
                "0": {
                    "path": "/sidecar/MOD13Q1/1.hdf_mvs.h5",
                    "offset": 8971,
                    "length": 1,
                }
            },
        ),
        (
            DMRPPTest_file3,
            "/data",
            {"entries": {}, "shape": ()},
        ),
    ],
)
def test_dmrpp_chunkmanifest_variable(file, var_path, expected):
    """Test that the chunk manifest matches the expected value. All variables have
    data that were created with single chunks.
    """
    dmrpp_instance = DMRPPParser(root=ET.fromstring(open(file).read()))
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
        ("/data/air", ["time", "lat", "lon"]),
        ("/SimpleGroup/Temperature", ["time", "Y", "X"]),
        ("/SimpleGroup/Salinity", ["time", "Y", "X"]),
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


def test_dmrpp_container_attributes():
    """Test tht the dmrpp flattens container attributes correctly at root and when a
    defined within variable.
    """
    dmrpp_instance = DMRPPParser(root=ET.fromstring(open(DMRPPTest_file3).read()))
    variables, attrs = dmrpp_instance._parse_dataset(dmrpp_instance.find_node_fqn("/"))
    assert "created" in attrs
    assert attrs["created"] == "2025-08-14T23:32:01Z"
    assert "long_name" in variables["data"]["attributes"]
    assert variables["data"]["attributes"]["long_name"] == "empty scalar data"


def test_compact_inline():
    dmrpp_file = (
        "http://test.opendap.org/opendap/data/dmrpp/" "compact_lowlevel.h5.dmrpp.file"
    )
    session = requests.Session()
    dmrpp = session.get(dmrpp_file).content.decode()
    dmrpp_instance = DMRPPParser(root=ET.fromstring(dmrpp))
    Vars, _ = dmrpp_instance._parse_dataset(dmrpp_instance.find_node_fqn("/"))
    inline_data = Vars["my_dataset"]["inline"]
    dtype = Vars["my_dataset"]["data_type"]
    np.testing.assert_array_equal(inline_data, np.arange(10, dtype=dtype))


def test_missingdata_inline():
    """Testing support for missingdata elements that contained inline values
    in a dmrpp
    """

    dmrpp = textwrap.dedent("""
        <Dataset xmlns="http://xml.opendap.org/ns/DAP/4.0#"
                 xmlns:dmrpp="http://xml.opendap.org/dap/dmrpp/1.0.0#"
                 dapVersion="4.0"
                 dmrVersion="1.0"
                name="file:///test.hdf"
                dmrpp:href="test.hdf"
                dmrpp:version="3.21.1">

            <Dimension name="Latitude" size="91"/>

            <Group name="Data">
                <Float64 name="Latitude">
                    <Dim name="/Latitude"/>

                    <Attribute name="units" type="String">
                        <Value>degrees_north</Value>
                    </Attribute>

                    <dmrpp:missingdata>
                        eJw1yTkKwmAUhdG3BEtLCwsLiyAiIhIS5znGIbVL+Zfm0hQ9uc3h40Z892qK+
                        I3pqZkemumumW6aqdZMV91a8cIzTzzywD133HLDNVdccsGSBXPOOeOUE445Ys
                        YhB+yzxy47jNZ2bz+77LHPAYfMOOKYE04545w5C5ZccMkV19xwyx33PPDIE8+
                        8sOL1b2LUmnHTjLtmPDTjqRmNbt4fWLdK1Q==
                    </dmrpp:missingdata>

                </Float64>
            </Group>
        </Dataset>
        """)
    dmrpp_instance = DMRPPParser(root=ET.fromstring(dmrpp))
    Vars, _ = dmrpp_instance._parse_dataset(dmrpp_instance.find_node_fqn("/Data"))
    inline_data = Vars["Latitude"]["inline"]
    dtype = Vars["Latitude"]["data_type"]
    expected = np.concatenate(
        (np.arange(-90, 90, 2, dtype=type), np.array([89.5], dtype=dtype)),
        axis=0,
    )
    np.testing.assert_array_equal(inline_data, expected[::-1])


def test_dmrpp_validation_issues_accumulation():
    dmrpp_xml_str = textwrap.dedent("""\
        <?xml version="1.0" encoding="ISO-8859-1"?>
        <Dataset xmlns="http://xml.opendap.org/ns/DAP/4.0#"
            xmlns:dmrpp="http://xml.opendap.org/dap/dmrpp/1.0.0#"
            dapVersion="4.0" dmrVersion="1.0" name="validation_test.nc"
            dmrpp:href="OPeNDAP_DMRpp_DATA_ACCESS_URL" dmrpp:version="3.21.1-451">
            <Dimension name="lat" size="25"/>
            <Float32 name="data">
                <Dim name="/lat"/>
                <Attribute type="Float32">
                    <Value>1.0</Value>
                </Attribute>
                <dmrpp:chunks fillValue="nan" byteOrder="LE">
                    <dmrpp:chunk offset="100" nBytes="100"/>
                </dmrpp:chunks>
            </Float32>
        </Dataset>
        """)
    parser = DMRPPParser(
        root=ET.fromstring(dmrpp_xml_str), data_filepath="file:///validation_test.nc"
    )
    parser._parse_dataset(parser.root)
    assert len(parser._validation_issues) > 0
    assert any(
        "Missing required attribute 'name'" in issue
        for issue in parser._validation_issues
    )


def test_dmrpp_get_attrib_with_missing_optional():
    dmrpp_xml_str = textwrap.dedent("""\
        <?xml version="1.0" encoding="ISO-8859-1"?>
        <Dataset xmlns="http://xml.opendap.org/ns/DAP/4.0#"
            xmlns:dmrpp="http://xml.opendap.org/dap/dmrpp/1.0.0#"
            dapVersion="4.0" dmrVersion="1.0" name="test.nc"
            dmrpp:href="OPeNDAP_DMRpp_DATA_ACCESS_URL" dmrpp:version="3.21.1-451">
            <Dimension name="lat" size="25"/>
        </Dataset>
        """)
    parser = DMRPPParser(root=ET.fromstring(dmrpp_xml_str))
    dimension = parser.root.find("dap:Dimension", parser._NS)
    result = parser._get_attrib(dimension, "nonexistent")
    assert result is None
    assert len(parser._validation_issues) == 1


def test_dmrpp_get_attrib_with_required_missing():
    dmrpp_xml_str = textwrap.dedent("""\
        <?xml version="1.0" encoding="ISO-8859-1"?>
        <Dataset xmlns="http://xml.opendap.org/ns/DAP/4.0#"
            xmlns:dmrpp="http://xml.opendap.org/dap/dmrpp/1.0.0#"
            dapVersion="4.0" dmrVersion="1.0" name="test.nc"
            dmrpp:href="OPeNDAP_DMRpp_DATA_ACCESS_URL" dmrpp:version="3.21.1-451">
            <Dimension name="lat" size="25"/>
        </Dataset>
        """)
    parser = DMRPPParser(root=ET.fromstring(dmrpp_xml_str))
    dimension = parser.root.find("dap:Dimension", parser._NS)
    with pytest.raises(ValueError, match="Missing required attribute 'nonexistent'"):
        parser._get_attrib(dimension, "nonexistent", required=True)


def test_dmrpp_mixed_named_and_unnamed_dimensions():
    dmrpp_xml_str = textwrap.dedent("""\
        <?xml version="1.0" encoding="ISO-8859-1"?>
        <Dataset xmlns="http://xml.opendap.org/ns/DAP/4.0#"
            xmlns:dmrpp="http://xml.opendap.org/dap/dmrpp/1.0.0#"
            dapVersion="4.0" dmrVersion="1.0" name="mixed_test.nc"
            dmrpp:href="OPeNDAP_DMRpp_DATA_ACCESS_URL" dmrpp:version="3.21.1-451">
            <Dimension name="time" size="10"/>
            <Dimension name="lat" size="30"/>
            <Float32 name="data">
                <Dim name="/time"/>
                <Dim size="20"/>
                <Dim name="/lat"/>
                <Attribute name="_FillValue" type="Float32">
                    <Value>NaN</Value>
                </Attribute>
                <dmrpp:chunks fillValue="nan" byteOrder="LE">
                    <dmrpp:chunk offset="100" nBytes="24000"/>
                </dmrpp:chunks>
            </Float32>
        </Dataset>
        """)
    parser = DMRPPParser(
        root=ET.fromstring(dmrpp_xml_str), data_filepath="file:///mixed_test.nc"
    )
    var = parser._parse_variable(parser.find_node_fqn("/data"))
    assert list(var["dimension_names"]) == ["time", "phony_dim_1", "lat"]
    assert var["shape"] == (10, 20, 30)


def test_dmrpp_phony_dim_naming():
    dmrpp_xml_str = textwrap.dedent("""\
        <?xml version="1.0" encoding="ISO-8859-1"?>
        <Dataset xmlns="http://xml.opendap.org/ns/DAP/4.0#"
            xmlns:dmrpp="http://xml.opendap.org/dap/dmrpp/1.0.0#"
            dapVersion="4.0" dmrVersion="1.0" name="phony_test.nc"
            dmrpp:href="OPeNDAP_DMRpp_DATA_ACCESS_URL" dmrpp:version="3.21.1-451">
            <Float32 name="data">
                <Dim size="10"/>
                <Dim size="20"/>
                <Attribute name="_FillValue" type="Float32">
                    <Value>NaN</Value>
                </Attribute>
                <dmrpp:chunks fillValue="nan" byteOrder="LE">
                    <dmrpp:chunk offset="100" nBytes="800"/>
                </dmrpp:chunks>
            </Float32>
        </Dataset>
        """)
    parser = DMRPPParser(
        root=ET.fromstring(dmrpp_xml_str), data_filepath="file:///phony_test.nc"
    )
    var = parser._parse_variable(parser.find_node_fqn("/data"))
    assert list(var["dimension_names"]) == ["phony_dim_0", "phony_dim_1"]
    assert var["shape"] == (10, 20)


@pytest.mark.parametrize(
    "fqn_path, expected_xpath",
    [
        ("/", "."),
        ("/air", "./*[@name='air']"),
    ],
)
def test_find_node_fqn_simple(fqn_path, expected_xpath):
    parser_instance = DMRPPParser(root=ET.fromstring(open(DMRPPTest_file4).read()))
    result = parser_instance.find_node_fqn(fqn_path)
    expected = parser_instance.root.find(expected_xpath, parser_instance._NS)
    assert result == expected


def test_find_node_fqn_grouped():
    parser_instance = DMRPPParser(root=ET.fromstring(open(DMRPPTest_file5).read()))
    result = parser_instance.find_node_fqn("/test/group/air")
    expected = parser_instance.root.find(
        "./*[@name='test']/*[@name='group']/*[@name='air']", parser_instance._NS
    )
    assert result == expected


@pytest.mark.parametrize(
    "group_path",
    [
        ("/"),
        ("/test"),
        ("/test/group"),
    ],
)
def test_split_groups(group_path):
    dmrpp_instance = DMRPPParser(root=ET.fromstring(open(DMRPPTest_file5).read()))

    # get all tags in a dataset (so all tags excluding nested groups)
    def dataset_tags(x):
        return [
            d for d in x if d.tag != "{" + dmrpp_instance._NS["dap"] + "}" + "Group"
        ]

    # check that contents of the split groups dataset match contents of the original
    #  dataset
    result_tags = dataset_tags(
        dmrpp_instance._split_groups(dmrpp_instance.root)[Path(group_path)]
    )
    expected_tags = dataset_tags(dmrpp_instance.find_node_fqn(group_path))
    assert result_tags == expected_tags


def test_parse_variable():
    parser = DMRPPParser(root=ET.fromstring(open(DMRPPTest_file4).read()))

    var = parser._parse_variable(parser.find_node_fqn("/air"))
    assert var["data_type"] == "int16"
    assert var["dimension_names"] == ["time", "lat", "lon"]
    assert var["shape"] == (2920, 25, 53)
    assert var["chunk_shape"] == (2920, 25, 53)
    # _FillValue is encoded for array dtype
    assert var["attributes"]["scale_factor"] == 0.01
    assert (
        var["attributes"]["long_name"] == "4xDaily Air temperature at sigma level 995"
    )


@pytest.mark.parametrize(
    "attr_path, expected",
    [
        ("air/long_name", {"long_name": "4xDaily Air temperature at sigma level 995"}),
        ("air/scale_factor", {"scale_factor": 0.01}),
    ],
)
def test_parse_attribute(attr_path, expected):
    parser = DMRPPParser(root=ET.fromstring(open(DMRPPTest_file4).read()))

    result = parser._parse_attribute(parser.find_node_fqn(attr_path))
    assert result == expected
