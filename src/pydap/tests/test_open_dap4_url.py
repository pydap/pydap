import os

import numpy as np
import pytest

from pydap.client import open_url
from pydap.model import SequenceType, StructureType
from pydap.net import create_session

base_url = "dap4://test.opendap.org"

TestGroupdmrpp = os.path.join(
    os.path.dirname(__file__), "data/dmrs/TestGroupData.nc4.dmrpp"
)


def test_coads():
    url = base_url + "/opendap/hyrax/data/nc/coads_climatology.nc"
    pydap_ds = open_url(url)
    pydap_ds["COADSX"][10:12:1]


def test_groups():
    url = base_url + "/opendap/dmrpp_test_files/"
    pydap_ds = open_url(url + "ATL03_20181228015957_13810110_003_01.2var.h5.dmrpp")
    pydap_ds["/gt1r/bckgrd_atlas/bckgrd_int_height"][0:10]


@pytest.mark.skip(reason="Grids are no longer part of the DAP4")
def test_maps():
    url = base_url + "/opendap/hyrax/data/nc/coads_climatology.nc"
    pydap_ds = open_url(url)  # False is default now
    data = pydap_ds["SST"][0:2:1, 40:42:1, 1:10:1]
    print(data.array[:].data)


@pytest.mark.parametrize("protocol", ["dap4", "dap2"])
def test_dap4_slices(cache_tmp_dir, protocol):
    """Also tests dap2"""
    url = "https://test.opendap.org/opendap/netcdf/examples/tos_O1_2001-2002.nc"
    cache_name = cache_tmp_dir / "debug_dap4_slices"
    session = create_session(
        use_cache=True,
        cache_kwargs={"cache_name": cache_name},
    )
    pyds = open_url(url, protocol=protocol, session=session)
    session.cache.clear()  # Clear cache before testing
    lon = np.asarray(pyds["lon"][-1:].data)
    assert lon.shape == (1,)

    query_string = (
        session.cache.urls()[0].split("lon")[-1].split("%5B")[1].split("%5D")[0]
    )
    assert query_string.replace("%3A", ":") == "179:1:179"
    session.cache.clear()


def test_dap4_unaligned_check_dims_tds():
    """ """
    url = (
        "dap4://thredds-test.unidata.ucar.edu/thredds/dap4/dev/d4icomp/"
        + "unaligned_simple_datatree.nc.h5"
    )
    session = create_session()

    pyds = open_url(url, session=session)
    assert pyds.dimensions == {"lat": 1, "lon": 2}
    assert pyds["Group1"].dimensions == {"lat": 1, "lon": 2}
    assert pyds["Group1/subgroup1"].dimensions == {"lat": 2, "lon": 2}
    assert pyds["root_variable"].dims == ["/lat", "/lon"]
    assert pyds["/Group1/group_1_var"].dims == ["/Group1/lat", "/Group1/lon"]
    assert pyds["/Group1/subgroup1/subgroup1_var"].dims == [
        "/Group1/subgroup1/lat",
        "/Group1/subgroup1/lon",
    ]


def test_dap4_unaligned_check_dims():
    """ """
    url = "dap4://test.opendap.org/opendap/dap4/unaligned_simple_datatree.nc.h5"
    session = create_session()

    pyds = open_url(url, session=session)
    assert pyds.dimensions == {"lat": 1, "lon": 2}
    assert pyds["Group1"].dimensions == {"lat": 1, "lon": 2}
    assert pyds["Group1/subgroup1"].dimensions == {"lat": 2, "lon": 2}
    assert pyds["root_variable"].dims == ["/lat", "/lon"]
    assert pyds["/Group1/group_1_var"].dims == ["/lat", "/lon"]
    assert pyds["/Group1/subgroup1/subgroup1_var"].dims == [
        "/Group1/subgroup1/lat",
        "/Group1/subgroup1/lon",
    ]


def test_dap4_unaligned2_check_dims():
    """ """
    url = "dap4://test.opendap.org/opendap/dap4/unaligned_simple_datatree2.nc.h5"
    session = create_session()
    pyds = open_url(url, session=session)

    assert pyds.dimensions == {"lat": 1, "lon": 1}
    assert pyds["Group1"].dimensions == {"lat": 1, "lon": 2}
    assert pyds["Group1/SubGroup1"].dimensions == {"lat": 2, "lon": 2}
    assert pyds["Group1/SubGroup2"].dimensions == {"lat": 3, "lon": 3}
    assert pyds["Group2"].dimensions == {"lat": 2, "lon": 2}
    assert pyds["Group2/SubGroup3"].dimensions == {"X": 1, "Y": 1}
    assert pyds["Group2/SubGroup4"].dimensions == {"X": 2, "Y": 2}

    assert pyds["root_variable"].dims == ["/lat", "/lon"]
    assert pyds["/Group1/group_1_var"].dims == ["/Group1/lat", "/Group1/lon"]
    assert pyds["/Group1/SubGroup1/subgroup1_var"].dims == [
        "/Group1/SubGroup1/lat",
        "/Group1/SubGroup1/lon",
    ]
    assert pyds["/Group1/SubGroup2/subgroup2_var"].dims == [
        "/Group1/SubGroup2/lat",
        "/Group1/SubGroup2/lon",
    ]
    assert pyds["/Group2/group_2_var"].dims == ["/Group2/lat", "/Group2/lon"]
    assert pyds["/Group2/SubGroup3/subgroup3_var"].dims == [
        "/Group2/SubGroup3/Y",
        "/Group2/SubGroup3/X",
    ]
    assert pyds["/Group2/SubGroup4/subgroup4_var"].dims == [
        "/Group2/SubGroup4/Y",
        "/Group2/SubGroup4/X",
    ]


@pytest.mark.parametrize(
    "url",
    [
        "dap4://thredds-test.unidata.ucar.edu/thredds/dap4/dev/d4icomp/SimpleGroup.nc4",
        "dap4://test.opendap.org/opendap/dap4/SimpleGroup.nc4.h5",
    ],
)
def test_batch_mode_downloads(cache_tmp_dir, url):
    """
    Test that batch mode downloads data correctly.
    """
    cache_name = cache_tmp_dir / "debug_batch_mode_downloads"
    session = create_session(
        use_cache=True,
        cache_kwargs={"cache_name": cache_name},
    )
    session.cache.clear()  # Clear cache before testing

    ds = open_url(url, session=session, checksums=True, batch=True)

    # slash arrays to triger data download.
    # both salt and temp get downloaded with
    # same url request
    temp = ds["SimpleGroup/Temperature"][:].data
    salt = ds["SimpleGroup/Salinity"][:].data

    # unpack data into numpy arrays
    # step is necessary
    temp = np.asarray(temp)
    salt = np.asarray(salt)

    # check that the data is correct
    assert np.mean(salt) == 30.0

    # Check that there is only 1 URL cached: the DMR. The DAP url us no longer cached
    assert len(session.cache.urls()) == 2
    session.cache.clear()


def test_dmrpp_open_dataset():
    file_url = TestGroupdmrpp
    pyds = open_url(file_url)
    root_vars = {
        "time": {"dtype": np.dtype("float32"), "shape": (1,), "dims": ["/time"]}
    }
    SimpleGroup_vars = {
        "Y": {"dtype": np.dtype("int16"), "shape": (40,), "dims": ["/SimpleGroup/Y"]},
        "X": {"dtype": np.dtype("int16"), "shape": (40,), "dims": ["/SimpleGroup/X"]},
        "Temperature": {
            "dtype": np.dtype("float32"),
            "shape": (1, 40, 40),
            "dims": ["/time", "/SimpleGroup/Y", "/SimpleGroup/X"],
        },
        "Salinity": {
            "dtype": np.dtype("float32"),
            "shape": (1, 40, 40),
            "dims": ["/time", "/SimpleGroup/Y", "/SimpleGroup/X"],
        },
    }
    Data_vars = {
        "air": {
            "dtype": np.dtype("int16"),
            "shape": (1, 25, 53),
            "dims": ["/time", "/data/lat", "/data/lon"],
        },
        "lat": {"dtype": np.dtype("float32"), "shape": (25,), "dims": ["/data/lat"]},
        "lon": {"dtype": np.dtype("float32"), "shape": (53,), "dims": ["/data/lon"]},
    }
    assert pyds.variables() == root_vars
    assert pyds["SimpleGroup"].variables() == SimpleGroup_vars
    assert pyds["data"].variables() == Data_vars

    np.testing.assert_array_equal(pyds["SimpleGroup/X"][:].data, np.arange(40))
    np.testing.assert_array_equal(
        np.mean(pyds["SimpleGroup/Salinity"][:].data), np.array([30])
    )


@pytest.mark.parametrize(
    "url,var, expected_value",
    [
        (
            "dap4://test.opendap.org/opendap/dap4/d4ts/test_struct1.nc.h5",
            "s.x",
            np.array(1, np.int32),
        ),
        (
            "dap4://test.opendap.org/opendap/data/ff/avhrr.dat",
            "URI_Avhrr.day",
            np.array(31472, np.int32),
        ),
    ],
)
def test_structs_and_sequences_warns(url, var, expected_value):
    with pytest.warns(UserWarning):
        pyds = open_url(url)
        np.testing.assert_array_equal(pyds[var][:].data, expected_value)


@pytest.mark.parametrize(
    "url, var, ContainerType, val",
    [
        (
            "dap4://test.opendap.org/opendap/dap4/d4ts/test_struct1.nc.h5",
            "s.x",
            StructureType,
            np.array(1, np.int32),
        ),
        (
            "dap4://test.opendap.org/opendap/data/ff/avhrr.dat",
            "URI_Avhrr.day",
            SequenceType,
            np.nan,
        ),
    ],
)
def test_structs_and_sequences_unflat(url, var, ContainerType, val):
    pyds = open_url(url, flat=False)
    assert isinstance(pyds[var].parent, ContainerType)
    if not isinstance(pyds[var].parent, SequenceType):
        assert pyds[var][:].data == val


def test_sequence_warns():
    url = "dap4://test.opendap.org/opendap/data/ff/avhrr.dat"
    with pytest.warns(UserWarning):
        open_url(url, flat=False)


def tests_structure_unflatted_unescaped(capsys):
    """Test that repr remains escaped when data access is flatted (default)
    for structures, but that `DatasetType.variables()` returns unescaped names.
    This is necessary for improved interoperatbility with Xarray
    """
    url = "dap4://test.opendap.org/opendap/dap4/d4ts/test_struct1.nc.h5"
    with pytest.warns(UserWarning):
        pyds = open_url(url)
    # assert flattened access
    assert repr(pyds) == "<DatasetType with children 's%2Ex', 's%2Ey'>"
    assert pyds.variables() == {
        "s.x": {"dtype": np.dtype("int32"), "shape": (), "dims": []},
        "s.y": {"dtype": np.dtype("int32"), "shape": (), "dims": []},
    }
    np.testing.assert_equal(np.asarray(pyds["s.x"].data[:]), 1)

    # now unflattened and unescaped in tree representation
    pyds.tree()
    out = capsys.readouterr().out
    expected = ".test_struct1.nc.h5\n├──s.x\n└──s.y\n"
    assert out == expected


if __name__ == "__main__":
    test_maps()
