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


def test_batch_mode_downloads():
    """
    Test that batch mode downloads data correctly.
    """
    session = create_session(use_cache=True)
    session.cache.clear()  # Clear cache before testing

    url = "http://test.opendap.org/opendap/dap4/SimpleGroup.nc4.h5"
    ds = open_url(url, session=session, protocol="dap4", checksum=False)
    ds.enable_batch_mode()

    # slash arrays to triger data download.
    # both salt and temp get downloaded with
    # same url request
    temp = ds["SimpleGroup/Temperature"][:].data
    salt = ds["SimpleGroup/Salinity"][:].data

    # unpack data into numpy arrays
    # step is necessary
    temp = np.asarray(temp)
    salt = np.asarray(salt)

    CE_temp = (
        "%2FSimpleGroup%2FTemperature%5B0%3A1%3A0%5D%5B0%3A1%3A39%5D%5B0%3A1%3A39%5D"
    )
    CE_salt = "%2FSimpleGroup%2FSalinity%5B0%3A1%3A0%5D%5B0%3A1%3A39%5D%5B0%3A1%3A39%5D"

    # Checksum query parameter was set to False (default)
    # but the server always returns checksum=True when batching
    checksum_url = "&dap4.checksum=true"

    single_dap_url = (
        url + ".dap?dap4.ce=" + ("%3B").join([CE_temp, CE_salt]) + checksum_url
    )

    # Check that the URL used for the request is as expected
    assert session.cache.urls()[0] == single_dap_url

    assert np.mean(salt) == 30.0


if __name__ == "__main__":
    test_maps()
