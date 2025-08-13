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
    session = create_session(use_cache=True, cache_kwargs={"cache_name": "debug"})
    session.cache.clear()  # Clear cache before testing

    url = "http://test.opendap.org/opendap/dap4/SimpleGroup.nc4.h5"
    ds = open_url(url, session=session, protocol="dap4", checksums=True)
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

    # check that the data is correct
    assert np.mean(salt) == 30.0

    # check that cached urls are correct

    # Check that there is only 1 URL cached: the DMR. The DAP url us no longer cached
    assert len(session.cache.urls()) == 2

    # # check dap url (assume it is the 0th one of the cached urls)
    # cached_dap_url_query = session.cache.urls()[0].split("?dap4.ce=")[1]

    # # Checksum query parameter was set to False (default)
    # # but the currently always set to `checksum=true` when batching
    # # this will change later

    # data_requests, checksum_query = cached_dap_url_query.split("&")

    # assert checksum_query == "dap4.checksum=true"

    # Now take the rest, and check that the two variable data requests are correct

    # # expected:
    # expected_CE_temp = (
    #     "%2FSimpleGroup%2FTemperature%5B0%3A1%3A0%5D%5B0%3A1%3A39%5D%5B0%3A1%3A39%5D"
    # )
    # expected_CE_salt = (
    #     "%2FSimpleGroup%2FSalinity%5B0%3A1%3A0%5D%5B0%3A1%3A39%5D%5B0%3A1%3A39%5D"
    # )

    # observed_CEs = data_requests.split("%3B")  # `;` scaped is %3B

    # assert set(observed_CEs) == set([expected_CE_temp, expected_CE_salt])


if __name__ == "__main__":
    test_maps()
