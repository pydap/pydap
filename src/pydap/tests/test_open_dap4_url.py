import numpy as np
import pytest

from pydap.client import open_url
from pydap.net import create_session

base_url = "dap4://test.opendap.org"


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
def test_dap4_slices(protocol):
    """Also tests dap2"""
    url = "https://test.opendap.org/opendap/netcdf/examples/tos_O1_2001-2002.nc"

    session = create_session(
        use_cache=True,
        cache_kwargs={"cache_name": "debug"},
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
    url = "dap4://test.opendap.org/opendap/dap4/unaligned_simple_datatree2.nc4.h5"
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


def test_batch_mode_downloads():
    """
    Test that batch mode downloads data correctly.
    """
    session = create_session(
        use_cache=True,
        cache_kwargs={"cache_name": "debug"},
    )
    session.cache.clear()  # Clear cache before testing

    url = "http://test.opendap.org/opendap/dap4/SimpleGroup.nc4.h5"
    ds = open_url(url, session=session, protocol="dap4", checksums=True, batch=True)

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


if __name__ == "__main__":
    test_maps()
