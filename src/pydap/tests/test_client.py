"""Test the pydap client."""

import datetime as dt
import os

import numpy as np
import pytest
import requests

from ..client import (
    compute_base_url_prefix,
    consolidate_metadata,
    get_cmr_urls,
    open_dmr,
    open_dods_url,
    open_file,
    open_url,
    patch_session_for_shared_dap_cache,
)
from ..handlers.lib import BaseHandler
from ..lib import _quote
from ..model import BaseType, DatasetType, GridType
from ..net import create_session
from .datasets import SimpleGrid, SimpleSequence, SimpleStructure

DODS = os.path.join(os.path.dirname(__file__), "data/test.01.dods")
DAS = os.path.join(os.path.dirname(__file__), "data/test.01.das")
SimpleGroupdmr = os.path.join(os.path.dirname(__file__), "data/dmrs/SimpleGroup.dmr")


@pytest.fixture
def sequence_app():
    return BaseHandler(SimpleSequence)


@pytest.fixture
def structure_app():
    return BaseHandler(SimpleStructure)


@pytest.mark.client
def test_open_url(sequence_app):
    """Open an URL and check dataset keys."""
    dataset = open_url("http://localhost:8001/", sequence_app)
    assert list(dataset.keys()) == ["cast"]
    assert isinstance(dataset.session, requests.Session)


@pytest.fixture
def remote_url():
    return "http://test.opendap.org/opendap/hyrax/data/"


def test_open_url_dap4(remote_url):
    base_url = remote_url + "nc/test.nc"
    data_original = open_url(base_url)

    # test single data point
    constrain1 = "dap4.ce=/s33[0][0]"
    data_dap4 = open_url(base_url + "?" + constrain1)
    assert np.asarray(data_dap4["s33"][:].data) == np.asarray(
        data_original["s33"][0, 0].data
    )

    # subset of vars by indexes
    var1 = "/s33[0:1:2][0:1:2];"
    var2 = "/br34[0:1:1][0:1:2][0:1:3];"
    var3 = "/s113[0:1:0][0:1:0][0:1:2]"
    Vars = [var1, var2, var3]

    url = base_url + "?dap4.ce=" + var1 + var2 + var3
    dataset = open_url(url)
    # check [vars1, vars2, vars3] only in dataset
    assert len(dataset.keys()) == len(Vars)


def test_open_url_dap4_shape():
    url = "http://test.opendap.org:8080/opendap/"
    filename = "netcdf/examples/200803061600_HFRadar_USEGC_6km_rtv_SIO.nc"
    CE = "?dap4.ce=/lon[100:1:199]"
    ds_ce = open_url(url + filename + CE)
    data = np.asarray(ds_ce["lon"][:].data)
    assert data.shape == (100,)


def test_open_url_seqCE(remote_url):
    seq_url = remote_url + "ff/gsodock.dat"
    data_original = open_url(seq_url)
    # get name of Sequence
    seq_name = [key for key in data_original.keys()][0]

    # add constraint expression
    Vars = ["Time", "Sea_Temp"]
    Value = 35234.1
    projection = "URI_GSO-Dock.Time,URI_GSO-Dock.Sea_Temp"
    selection = "URI_GSO-Dock.Time<" + str(Value)
    seq_url_CE = seq_url + "?" + projection + "&" + selection

    dsCE = open_url(seq_url_CE)

    # assert projection works within sequence
    assert set([var for var in dsCE[seq_name].keys()]) == set(Vars)

    # assert selection works within sequence

    assert max([var for var in dsCE[seq_name]["Time"]]) < Value
    assert len([var for var in dsCE[seq_name]["Time"]]) < len(
        [var for var in data_original[seq_name]["Time"]]
    )


@pytest.mark.parametrize(
    "output_grid",
    [False, True],
)
def test_output_grid(output_grid, remote_url):
    """tests the behavior of output_grid as argument to open_url"""
    url = remote_url + "nc/coads_climatology.nc"
    pyds = open_url(url, output_grid=output_grid, protocol="dap2")
    assert list(pyds.grids()) == ["SST", "AIRT", "UWND", "VWND"]
    sst = pyds["SST"][0, :, :]
    if output_grid:
        assert isinstance(sst, GridType)
    else:
        assert isinstance(sst, BaseType)


@pytest.mark.parametrize(
    "session",
    [None, requests.session()],
)
def test_session_client(session):
    """Test that session is passed correctly from user and no changes are made
    to it.
    """
    url = "http://test.opendap.org:8080/opendap/data/nc/123bears.nc"
    cache_kwargs = {
        "cache_name": "http_cache",
        "backend": "sqlite",
        "use_temp": True,
        "expire_after": 100,  # seconds
    }
    use_cache = False  # this triggers a user warning when cache_kwargs are
    # passed to create_session. However that only happens when session is None
    # provide a session.
    if not session:
        with pytest.warns(UserWarning):
            ds = open_url(
                url,
                session=session,
                protocol="dap2",
                use_cache=use_cache,
                cache_kwargs=cache_kwargs,
            )
    else:
        ds = open_url(
            url,
            session=session,
            protocol="dap2",
            use_cache=use_cache,
            cache_kwargs=cache_kwargs,
        )

    assert isinstance(ds, DatasetType)


@pytest.mark.client
def test_open_dods():
    """Open a file downloaded from the test server with the DAS."""
    dataset = open_file(DODS)

    # test data
    assert dataset.data == [
        0,
        1,
        0,
        0,
        0,
        0.0,
        1000.0,
        "This is a data test string (pass 0).",
        "http://www.dods.org",
    ]

    # test attributes
    assert dataset.attributes == {}
    assert dataset.i32.attributes == {}
    assert dataset.b.attributes == {}


@pytest.mark.client
def test_open_dods_das():
    """Open a file downloaded from the test server with the DAS."""
    dataset = open_file(DODS, DAS)

    # test data
    assert dataset.data == [
        0,
        1,
        0,
        0,
        0,
        0.0,
        1000.0,
        "This is a data test string (pass 0).",
        "http://www.dods.org",
    ]

    # test attributes
    assert dataset.i32.units == "unknown"
    assert dataset.i32.Description == "A 32 bit test server int"
    assert dataset.b.units == "unknown"
    assert dataset.b.Description == "A test byte"
    assert dataset.Facility["DataCenter"] == "COAS Environmental Computer Facility"
    assert dataset.Facility["PrincipleInvestigator"] == ["Mark Abbott", "Ph.D"]
    assert dataset.Facility["DrifterType"] == "MetOcean WOCE/OCM"


@pytest.mark.client
def test_open_dods_16bits(sequence_app):
    """Open the dods response from a server.

    Note that here we cannot simply compare ``dataset.data`` with the
    original data ``SimpleSequence.data``, because the original data
    contains int16 values which are transmitted as int32 in the DAP spec.

    """
    dataset = open_dods_url(".dods", application=sequence_app)
    assert list(dataset.data) == [
        [
            ("1", 100, -10, 0, -1, 21, 35, 0),
            ("2", 200, 10, 500, 1, 15, 35, 100),
        ]
    ]

    # attributes should be empty
    assert dataset.attributes == {}


@pytest.mark.client
def test_open_dods_with_attributes(sequence_app):
    """Open the dods response together with the das response."""
    dataset = open_dods_url(".dods", metadata=True, application=sequence_app)
    assert "NC_GLOBAL" not in dataset.attributes
    assert "DODS_EXTRA" not in dataset.attributes
    assert dataset.description == "A simple sequence for testing."
    assert dataset.cast.lon.axis == "X"
    assert dataset.cast.lat.axis == "Y"
    assert dataset.cast.depth.axis == "Z"
    assert dataset.cast.time.axis == "T"
    assert dataset.cast.time.units == "days since 1970-01-01"


@pytest.fixture(scope="session")
def ssf_app():
    """Test the local implementation of server-side functions.

    Calling server-side functions is implemented using a lazy mechanism where
    arbitrary names are mapped to remove calls. The resulting dataset is only
    evaluated when ``__getitem__`` or ``__getattr__`` are called, allowing
    nested calls to be evaluated only once.

    """
    from pydap.wsgi.ssf import ServerSideFunctions

    return ServerSideFunctions(BaseHandler(SimpleGrid))


def test_original(ssf_app):
    """Test an unmodified call, without function calls."""
    original = open_url("/", application=ssf_app)
    assert original.SimpleGrid.SimpleGrid.shape == (2, 3)


def test_first_axis(ssf_app):
    """Test mean over the first axis."""
    original = open_url("/", application=ssf_app)
    dataset = original.functions.mean(original.SimpleGrid, 0)
    assert dataset.SimpleGrid.SimpleGrid.shape == (3,)
    np.testing.assert_array_equal(
        dataset.SimpleGrid.SimpleGrid.data, np.array([1.5, 2.5, 3.5])
    )


def test_second_axis(ssf_app):
    """Test mean over the second axis."""
    original = open_url("/", application=ssf_app)
    dataset = original.functions.mean(original.SimpleGrid, 1)
    assert dataset.SimpleGrid.SimpleGrid.shape == (2,)
    np.testing.assert_array_equal(
        dataset.SimpleGrid.SimpleGrid.data, np.array([1.0, 4.0])
    )


def test_lazy_evaluation_getitem(ssf_app):
    """Test that the dataset is only loaded when accessed."""
    original = open_url("/", application=ssf_app)
    dataset = original.functions.mean(original.SimpleGrid, 0)
    assert dataset.dataset is None
    dataset["SimpleGrid"]
    assert dataset.dataset is not None


def test_lazy_evaluation_getattr(ssf_app):
    """Test that the dataset is only loaded when accessed."""
    original = open_url("/", application=ssf_app)
    dataset = original.functions.mean(original.SimpleGrid, 0)
    assert dataset.dataset is None
    dataset.SimpleGrid
    assert dataset.dataset is not None


def test_nested_call(ssf_app):
    """Test nested calls."""
    original = open_url("/", application=ssf_app)
    dataset = original.functions.mean(
        original.functions.mean(original.SimpleGrid, 0), 0
    )
    assert dataset["SimpleGrid"]["SimpleGrid"].shape == ()
    np.testing.assert_array_equal(dataset.SimpleGrid.SimpleGrid.data, np.array(2.5))


def test_axis_mean(ssf_app):
    """Test the mean over an axis, returning a scalar."""
    original = open_url("/", application=ssf_app)
    dataset = original.functions.mean(original.SimpleGrid.x)
    assert dataset.x.shape == ()
    np.testing.assert_array_equal(dataset.x.data, np.array(1.0))


@pytest.mark.client
def test_int16(structure_app):
    """Test that 16-bit values are represented correctly.

    Even though the DAP transfers int16 and uint16 as 32 bits, we want them to
    be represented locally using the correct type.

    Load an int16 -> should yield '>i2' type."""
    dataset = open_url("http://localhost:8001/", structure_app)
    assert dataset.types.i16.dtype == np.dtype(">i2")


@pytest.mark.client
def test_uint16(structure_app):
    """Test that 16-bit values are represented correctly.

    Even though the DAP transfers int16 and uint16 as 32 bits, we want them to
    be represented locally using the correct type.

    Load an uint16 -> should yield '>u2' type."""
    dataset = open_url("http://localhost:8001/", structure_app)
    assert dataset.types.ui16.dtype == np.dtype(">u2")


@pytest.mark.parametrize(
    "use_cache",
    [False, True],
)
def test_cache(use_cache):
    """Test that caching is passed from user correctly"""
    url = "http://test.opendap.org:8080/opendap/data/nc/123bears.nc"
    # cache_kwargs are being set, but only used when use_cache is True
    # thus - raise a warning if cache_kwargs are set and use_cache is False
    cache_kwargs = {
        "cache_name": "http_cache",
        "backend": "sqlite",
        "use_temp": True,
        "expire_after": 100,  # seconds
    }
    if not use_cache:
        with pytest.warns(UserWarning):
            open_url(
                url, protocol="dap2", use_cache=use_cache, cache_kwargs=cache_kwargs
            )
    else:
        ds = open_url(
            url, protocol="dap2", use_cache=use_cache, cache_kwargs=cache_kwargs
        )
        assert isinstance(ds, DatasetType)


@pytest.fixture
def cached_session():
    """Fixture to create a cached session."""
    return create_session(use_cache=True)


@pytest.mark.parametrize(
    "urls",
    ["not a list", ["A", "B", "C", 1], ["http://localhost:8001/"]],
)
def test_typerror_consolidate_metadata(urls, cached_session):
    """Test that TypeError is raised when `consolidate_metadata` takes an argument that
    is not a list, or a list of a single element.
    """
    cached_session.cache.clear()  # clears any existing cache
    with pytest.raises(TypeError):
        consolidate_metadata(urls, cached_session)


def test_warning_consolidate_metadata():
    """Test that there is a warning  when `consolidate_metadata` does not take a
    cached_session as a parameter.
    """
    urls = ["dap4://localhost:8001/", "dap4://localhost:8002/"]
    with pytest.warns(UserWarning):
        consolidate_metadata(urls, requests.Session())


@pytest.mark.parametrize(
    "urls",
    [
        ["dap4://localhost:8001/", "dap4://localhost:8002/", "http://localhost:8003/"],
        ["dap2://localhost:8001/", "dap4://localhost:8001/"],
    ],
)
def test_valueerror_consolidate_metadata(urls, cached_session):
    """Test that ValueError is raised when `consolidate_metadata` takes a list of
    urls that are not all the same type.
    """
    cached_session.cache.clear()
    with pytest.raises(ValueError):
        consolidate_metadata(urls, cached_session)


@pytest.mark.parametrize(
    "urls",
    [
        ["http://localhost:8001/", "http://localhost:8002/", "http://localhost:8003/"],
        ["dap2://localhost:8001/", "dap2://localhost:8002/", "dap2://localhost:8003/"],
    ],
)
def test_warning_nondap4urls_consolidate_metadata(urls, cached_session):
    """Test that a warning is raised when `consolidate_metadata` takes a list of urls
    that are do not have `dap4` as their scheme.
    """
    cached_session.cache.clear()
    with pytest.warns(UserWarning):
        consolidate_metadata(urls, cached_session)


ce1 = "?dap4.ce=/i;/j;/l;/bears"
ce2 = "?dap4.ce=/i;/j;/l;/order"


# @pytest.mark.skipif(
#     os.getenv("LOCAL_DEV") != "1", reason="This test only runs on local development"
# )
@pytest.mark.parametrize(
    "urls",
    [
        [
            "dap4://test.opendap.org/opendap/data/nc/123bears.nc",
            "dap4://test.opendap.org/opendap/data/nc/123bears.nc" + ce1,
            "dap4://test.opendap.org/opendap/data/nc/123bears.nc" + ce2,
        ],
    ],
)
@pytest.mark.parametrize("safe_mode", [True])
def test_cached_consolidate_metadata_matching_dims(urls, safe_mode):
    """Test the behavior of the chaching implemented in `consolidate_metadata`.
    the `safe_mode` parameter means that all dmr urls are cached, and
    the dimensions of each dmr_url are checked for consistency.

    when `safe_mode` is False, only the first dmr url is cached if
    all dmr urls CEs are identical. If the CEs are not identical,
    then a cache is created for each dmr url with different CEs.

    In both scenarios, the dap urls of the dimensions are cached
    """
    cached_session = create_session(use_cache=True, cache_kwargs={"backend": "memory"})
    cached_session.cache.clear()
    pyds = open_dmr(urls[0].replace("dap4", "http") + ".dmr")
    dims = sorted(list(pyds.dimensions))  # dimensions of full dataset
    consolidate_metadata(urls, session=cached_session, safe_mode=safe_mode)

    # check that the cached session has all the dmr urls and
    # caches the dap response of the dimensions only once
    # Single dap url for all dimensions downloaded
    assert len(cached_session.cache.urls()) == len(urls) + 1

    # THE FOLLOWING IS AN IMPORTANT CHECK. All dims are downloaded
    # within a single dap url. Make sure these appear in order. Order
    # matters when reusing cached urls.

    ce_dims = cached_session.cache.urls()[0].split("=")[1].split("&")[0].split("%3B")

    assert [item.split("%5B")[0] for item in ce_dims] == dims


ce1 = "?dap4.ce=/i;/j;/bears"
ce2 = "?dap4.ce=/i;/j;/order"


@pytest.mark.parametrize(
    "urls",
    [
        [
            "dap4://test.opendap.org/opendap/data/nc/123bears.nc",
            "dap4://test.opendap.org/opendap/data/nc/123bears.nc" + ce1,
            "dap4://test.opendap.org/opendap/data/nc/123bears.nc" + ce2,
        ],
    ],
)
@pytest.mark.parametrize("safe_mode", [True])
def test_cached_consolidate_metadata_inconsistent_dims(urls, safe_mode):
    """Test the behavior of the chaching implemented in `consolidate_metadata`.
    the `safe_mode` parameter means that all dmr urls are cached, and
    the dimensions of each dmr_url are checked for consistency.

    when `safe_mode` is False, only the first dmr url is cached if
    all dmr urls CEs are identical. If the CEs are not identical,
    then a cache is created for each dmr url with different CEs.

    In both scenarios, the dap urls of the dimensions are cached
    """
    cached_session = create_session(use_cache=True, cache_kwargs={"backend": "memory"})
    cached_session.cache.clear()
    pyds = open_dmr(urls[0].replace("dap4", "http") + ".dmr")
    dims = list(pyds.dimensions)  # here there are 3 dimensions
    if safe_mode:
        with pytest.warns(UserWarning):
            consolidate_metadata(urls, session=cached_session, safe_mode=safe_mode)
        assert len(cached_session.cache.urls()) == len(urls)
        # dmrs where cached, but not the dimensions
    else:
        consolidate_metadata(urls, session=cached_session, safe_mode=safe_mode)
        # caches all DMRs and caches the dap responses of the dimensions
        # of the first URL
        assert len(cached_session.cache.urls()) == len(urls) + len(dims)


# @pytest.mark.skipif(
#     os.getenv("LOCAL_DEV") != "1", reason="This test only runs on local development"
# )
@pytest.mark.parametrize(
    "urls",
    [
        [
            "dap4://test.opendap.org/opendap/hyrax/data/nc/coads_climatology.nc",
            "dap4://test.opendap.org/opendap/hyrax/data/nc/coads_climatology2.nc",
        ],
    ],
)
@pytest.mark.parametrize("concat_dim", [None, "TIME"])
def test_consolidate_metadata_concat_dim(urls, concat_dim):
    """Test the behavior of the chaching implemented in `consolidate_metadata`
    when there is a concat dimension, and (extra) this concat_dim may be an array
    of length >= 1.

    If `concat_dim` is None, only 1 dap response per dimension is cached (1 URL),
    and a special cache key is created for the rest of URLs. If `concat_dim` is set,
    then N dap responses for that dimension are cached, where N is the number of URLs.
    The rest of the (non-concat) dimensions behave the same as when `concat_dim` is
    None.

    """
    cached_session = create_session(use_cache=True, cache_kwargs={"backend": "memory"})
    cached_session.cache.clear()
    # download all dmr for testing - not most performant
    consolidate_metadata(
        urls, session=cached_session, safe_mode=True, concat_dim=concat_dim
    )

    N_dmr_urls = len(urls)  # Since `safe_mode=False`, only 1 DMR is downloaded

    if not concat_dim:
        # Without `concat_dim` set, only one dap response is downloaded per URL.
        assert (
            len(cached_session.cache.urls()) == N_dmr_urls + 1
        )  # all dims are batched together
    else:
        # concat dim is set. Must download N dap responses for the concat_dim.
        N_concat_dims = len(urls)  # see below !
        N_non_concat_dims = 1  # all dims are downloaded once, together.
        assert (
            len(cached_session.cache.urls())
            == N_dmr_urls + N_concat_dims + N_non_concat_dims
        )


@pytest.mark.parametrize(
    "urls",
    [
        ["http://localhost:8001/", 1, "http://localhost:8003/"],
        [
            "dap2://localhost:8001/",
            "dap2://localhost:8002/",
            "dap2://localhost:8003/",
        ],
        ["http://localhost:8001/"],
        [
            "http://localhost:8001/common/path/data.nc",
            "http://localhost:8001/common/path/data.nc",
            "http://localhost:8001/NO/COMMON/PATH/HERE/data.nc",
        ],
    ],
)
def test_ValueErrors_compute_base_url_prefix(urls):
    """Tests that ValueError is raised wuen urls
    is not a `uniform` list of https urls belonging to the same
    data cube. That is, URLS MUST be valid, and have a common path
    """
    with pytest.raises(ValueError):
        compute_base_url_prefix(urls)


cloud_common = "/providers/POCLOUD/collections/granules"
cloud_urls = "https://opendap.earthdata.nasa.gov"
posix_urls = "http://localhost:8001"
posix_common = "/common/path"


@pytest.mark.parametrize(
    "urls, common_path",
    [
        (
            [
                posix_urls + posix_common + "/data.nc",
                posix_urls + posix_common + "/data.nc",
                posix_urls + posix_common + "/data.nc",
            ],
            posix_urls + posix_common,
        ),
        (
            [
                cloud_urls + cloud_common + "/fileA.nc",
                cloud_urls + cloud_common + "/fileC.nc",
                cloud_urls + cloud_common + "/fileB.nc",
            ],
            cloud_urls + cloud_common,
        ),
    ],
)
def test_compute_base_url_prefix(urls, common_path):
    """Tests that compute_base_url_prefix returns the correct common path
    for a list of urls. The urls must be valid and have a common path.
    """
    base_url = compute_base_url_prefix(urls)
    assert base_url == common_path


@pytest.mark.parametrize(
    "url, expected",
    [
        [None, None],
        ["FileNotFound", None],
        [
            "http://test.opendap.org/opendap/data/nc/coads_climatology.nc.dmr",
            DatasetType,
        ],
        [
            SimpleGroupdmr,
            DatasetType,
        ],
    ],
)
def test_open_dmr(url, expected):
    """Test `open_dmr` for various urls"""
    pyds = open_dmr(url)
    if expected:
        assert isinstance(pyds, expected)
    else:
        assert pyds == expected


@pytest.mark.parametrize(
    "urls",
    [
        [
            "http://test.opendap.org/opendap/data/nc/123bears.nc",
            "http://test.opendap.org/opendap/data/nc/124bears.nc",
            "http://test.opendap.org/opendap/data/nc/125bears.nc",
        ],
    ],
)
def test_patch_session_for_shared_dap_cache(urls, cached_session):
    """Test that the session is patched correctly for shared dap cache."""
    # Clear any existing cache
    cached_session.cache.clear()
    # Create custom cache key for each of the dimensions
    dimensions = ["i[0:1:1]", "j[0:1:2]", "l[0:1:2]"]

    patch_session_for_shared_dap_cache(
        cached_session, shared_vars=dimensions, concat_dim=None, known_url_list=urls
    )
    assert len(cached_session.cache.urls()) == 0

    # construct urls to create cache keys
    test_urls = [urls[0] + ".dap?dap4.ce=" + dim for dim in dimensions]
    # create cache keys for the urls - discard the list
    _ = [cached_session.get(url) for url in test_urls]

    # make sure that the urls are cached for each dimension
    assert len(cached_session.cache.urls()) == len(dimensions)

    for dim in dimensions:
        test_url2 = urls[1] + ".dap?dap4.ce=" + dim
        test_url3 = urls[2] + ".dap?dap4.ce=" + dim

        # test that the urls are being cached
        r2 = cached_session.get(test_url2)
        r3 = cached_session.get(test_url3)

        # assert that data was cached - otherwise 404 (Non-existent URLS!)
        assert r2.from_cache
        assert r3.from_cache

    # assert that there is no new cached key
    assert len(cached_session.cache.urls()) == len(dimensions)


ccid = "concept_id=C2076114664-LPCLOUD"
start_date = dt.datetime(2020, 1, 1)
end_date = dt.datetime(2020, 1, 31)
dt_format = "%Y-%m-%dT%H:%M:%SZ"
bbox1 = "bounding_box%5B%5D=-10%2C-5%2C10%2C5"
bbox2 = "bounding_box%5B%5D=-11%2C-6%2C11%2C6"


@pytest.mark.skipif(
    os.getenv("LOCAL_DEV") != "1", reason="This test only runs on local development"
)
@pytest.mark.parametrize(
    "param, expected",
    [
        [{"doi": "10.5067/ECL5M-OTS44"}, "concept_id=C1991543728-POCLOUD&page_size=50"],
        [
            {
                "ccid": ccid.split("=")[-1],
                "time_range": [start_date, end_date],
            },
            ccid + "&temporal=2020-01-01T00%3A00%3A00Z%2C2020-01-31T00%3A00%3A00Z",
        ],
        [
            {
                "ccid": ccid.split("=")[-1],
                "time_range": [
                    start_date.strftime(dt_format),
                    end_date.strftime(dt_format),
                ],
            },
            ccid + "&temporal=2020-01-01T00%3A00%3A00Z%2C2020-01-31T00%3A00%3A00Z",
        ],
        [
            {
                "ccid": ccid.split("=")[-1],
                "bounding_box": list((-130.8, 41, -124, 45)),
            },
            ccid + "&bounding_box%5B%5D=-130.8%2C41%2C-124%2C45",
        ],
        [
            {
                "ccid": ccid.split("=")[-1],
                "bounding_box": {
                    "key1": list((-10, -5, 10, 5)),
                    "key2": list((-11, -6, 11, 6)),
                },
            },
            ccid + "&" + bbox1 + "&" + bbox2,
        ],
        [
            {
                "ccid": ccid.split("=")[-1],
                "bounding_box": {
                    "key1": list((-10, -5, 10, 5)),
                    "key2": list((-11, -6, 11, 6)),
                    "Union": True,
                },
            },
            ccid
            + "&"
            + bbox1
            + "&"
            + bbox2
            + "&options%5Bbounding_box%5D%5Bor%5D=true",
        ],
        [
            {
                "ccid": ccid.split("=")[-1],
                "point": [100, 20],
            },
            ccid + "&point%5B%5D=100%2C20",
        ],
        [
            {
                "ccid": "C1991543728-POCLOUD",
                "point": {"point1": [100, 20], "point2": [80, 20]},
            },
            "concept_id=C1991543728-POCLOUD"
            + "&point%5B%5D=100%2C20&point%5B%5D=80%2C20",
        ],
        [
            {
                "ccid": "C1991543728-POCLOUD",
                "point": {"point1": [100, 20], "point2": [80, 20], "Union": True},
            },
            "concept_id=C1991543728-POCLOUD"
            + "&point%5B%5D=100%2C20&point%5B%5D=80%2C20"
            + "&options%5Bpoint%5D%5Bor%5D=true",
        ],
        [
            {
                "ccid": "C1991543728-POCLOUD",
                "polygon": [10, 10, 30, 10, 30, 20, 10, 20, 10, 10],
            },
            "concept_id=C1991543728-POCLOUD"
            + "&polygon%5B%5D=10%2C10%2C30%2C10%2C30%2C20%2C10%2C20%2C10%2C10",
        ],
        [
            {
                "ccid": "C1991543728-POCLOUD",
                "polygon": {
                    "p1": [10, 10, 30, 10, 30, 20, 10, 20, 10, 10],
                    "p2": [11, 11, 31, 11, 31, 21, 11, 21, 11, 11],
                },
            },
            "concept_id=C1991543728-POCLOUD"
            + "&polygon%5B%5D=10%2C10%2C30%2C10%2C30%2C20%2C10%2C20%2C10%2C10"
            + "&polygon%5B%5D=11%2C11%2C31%2C11%2C31%2C21%2C11%2C21%2C11%2C11",
        ],
        [
            {
                "ccid": "C1991543728-POCLOUD",
                "polygon": {
                    "p1": [10, 10, 30, 10, 30, 20, 10, 20, 10, 10],
                    "p2": [11, 11, 31, 11, 31, 21, 11, 21, 11, 11],
                    "Union": True,
                },
            },
            "concept_id=C1991543728-POCLOUD"
            + "&polygon%5B%5D=10%2C10%2C30%2C10%2C30%2C20%2C10%2C20%2C10%2C10"
            + "&polygon%5B%5D=11%2C11%2C31%2C11%2C31%2C21%2C11%2C21%2C11%2C11"
            + "&options%5Bpolygon%5D%5Bor%5D=true",
        ],
        [
            {
                "ccid": ccid.split("=")[-1],
                "line": [-0.37, -14.07, 4.75, 1.27, 25.13, -15.51],
            },
            ccid + "&line%5B%5D=-0.37%2C-14.07%2C4.75%2C1.27%2C25.13%2C-15.51",
        ],
        [
            {
                "ccid": ccid.split("=")[-1],
                "line": {
                    "line1": [-0.37, -14.07, 4.75, 1.27, 25.13, -15.51],
                    "line2": [-1.37, -15.07, 5.75, 2.27, 26.13, -16.51],
                },
            },
            ccid
            + "&line%5B%5D=-0.37%2C-14.07%2C4.75%2C1.27%2C25.13%2C-15.51"
            + "&line%5B%5D=-1.37%2C-15.07%2C5.75%2C2.27%2C26.13%2C-16.51",
        ],
        [
            {
                "ccid": ccid.split("=")[-1],
                "line": {
                    "line1": [-0.37, -14.07, 4.75, 1.27, 25.13, -15.51],
                    "line2": [-1.37, -15.07, 5.75, 2.27, 26.13, -16.51],
                    "Union": True,
                },
            },
            ccid
            + "&line%5B%5D=-0.37%2C-14.07%2C4.75%2C1.27%2C25.13%2C-15.51"
            + "&line%5B%5D=-1.37%2C-15.07%2C5.75%2C2.27%2C26.13%2C-16.51"
            + "&options%5Bline%5D%5Bor%5D=true",
        ],
        [
            {
                "ccid": ccid.split("=")[-1],
                "circle": [-87.629717, 41.878112, 1000],
            },
            ccid + "&circle%5B%5D=-87.629717%2C41.878112%2C1000",
        ],
        [
            {
                "ccid": "C1991543728-POCLOUD",
                "circle": {
                    "c1": [-87.629717, 41.878112, 1000],
                    "c2": [-75, 41.878112, 1000],
                },
            },
            "concept_id=C1991543728-POCLOUD"
            + "&circle%5B%5D=-87.629717%2C41.878112%2C1000"
            + "&circle%5B%5D=-75%2C41.878112%2C1000",
        ],
        [
            {
                "ccid": "C1991543728-POCLOUD",
                "circle": {
                    "c1": [-87.629717, 41.878112, 1000],
                    "c2": [-75, 41.878112, 1000],
                    "Union": True,
                },
            },
            "concept_id=C1991543728-POCLOUD"
            + "&circle%5B%5D=-87.629717%2C41.878112%2C1000"
            + "&circle%5B%5D=-75%2C41.878112%2C1000"
            + "&options%5Bcircle%5D%5Bor%5D=true",
        ],
    ],
)
def test_get_cmr_urls(param, expected):
    """Test that get_cmr_urls returns the correct urls."""
    session = create_session(use_cache=True, cache_kwargs={"backend": "memory"})
    cmr_urls = get_cmr_urls(**param, session=session)
    assert isinstance(cmr_urls, list)
    assert len(cmr_urls) > 0
    cmr_url = "https://cmr.earthdata.nasa.gov/search/"
    cached_urls = session.cache.urls()
    if "doi" in param.keys():
        # when searching by doi, first pydap searches for the concept_collection id
        # and then searches for granules using that id.
        # the first url is the collection search
        url = cmr_url + "collections.json?doi="
        doi_query = _quote(param["doi"]).replace("/", "%2F").replace("%2E", ".")
        assert url + doi_query == cached_urls[0]
        cached_urls = cached_urls[1:]  # remove the first url
    cached_urls = cached_urls[0].split("?")[-1]  # get only the query part of the url
    if "limit" not in param.keys():
        # if page_size is not specified, it defaults to 50
        expected += "&page_size=50"
    assert set(expected.split("&")) == set(cached_urls.split("&"))
