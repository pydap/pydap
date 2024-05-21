import pytest

from pydap.client import open_url

base_url = "dap4://test.opendap.org"


def test_coads():
    url = base_url + "/opendap/hyrax/data/nc/coads_climatology.nc"
    pydap_ds = open_url(url)
    pydap_ds["COADSX"][10:12:1]


def test_groups():
    url = base_url + ":8080/opendap/dmrpp_test_files/"
    pydap_ds = open_url(url + "ATL03_20181228015957_13810110_003_01.2var.h5.dmrpp")
    pydap_ds["/gt1r/bckgrd_atlas/bckgrd_int_height"][0:10]


@pytest.mark.skip(reason="bug in testserver")
def test_maps():
    url = base_url + ":8080/opendap/hyrax/data/nc/coads_climatology.nc"
    pydap_ds = open_url(url)
    data = pydap_ds["SST"][0:2:1, 40:42:1, 1:10:1]
    print(data.array[:].data)


if __name__ == "__main__":
    test_maps()
