"""Test the pydap client."""

import datetime as dt
import os

import numpy as np
import pytest
import requests
from requests_cache import CachedSession

from ..client import (
    compute_base_url_prefix,
    consolidate_metadata,
    data_check,
    fetch_batched,
    fetch_consolidated,
    get_batch_data,
    get_cmr_urls,
    open_dmr,
    open_dods_url,
    open_file,
    open_url,
    patch_session_for_shared_dap_cache,
    recover_missing_url,
    register_all_for_batch,
)
from ..handlers.lib import BaseHandler
from ..lib import _quote
from ..model import BaseType, DatasetType, GridType
from ..net import create_session
from .datasets import SimpleGrid, SimpleSequence, SimpleStructure

DODS = os.path.join(os.path.dirname(__file__), "data/test.01.dods")
DAS = os.path.join(os.path.dirname(__file__), "data/test.01.das")
SimpleGroupdmr = os.path.join(os.path.dirname(__file__), "data/dmrs/SimpleGroup.dmr")
sqlite_db = os.path.join(os.path.dirname(__file__), "data/climatology_test")


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


def test_open_url_batch_dap2_raises():
    url = "dap2://test.opendap.org/opendap/"
    filename = "netcdf/examples/200803061600_HFRadar_USEGC_6km_rtv_SIO.nc"
    with pytest.raises(RuntimeError):
        open_url(url + filename, batch=True)


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
def test_session_client(cache_tmp_dir, session):
    """Test that session is passed correctly from user and no changes are made
    to it.
    """
    url = "http://test.opendap.org:8080/opendap/data/nc/123bears.nc"
    cache_kwargs = {
        "cache_name": cache_tmp_dir / "http_cache",
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
def test_cache(cache_tmp_dir, use_cache):
    """Test that caching is passed from user correctly"""
    url = "http://test.opendap.org:8080/opendap/data/nc/123bears.nc"
    # cache_kwargs are being set, but only used when use_cache is True
    # thus - raise a warning if cache_kwargs are set and use_cache is False
    cache_kwargs = {
        "cache_name": cache_tmp_dir / "http_cache",
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


@pytest.mark.parametrize(
    "urls",
    ["not a list", ["A", "B", "C", 1], ["http://localhost:8001/"]],
)
def test_typerror_consolidate_metadata(cache_tmp_dir, urls):
    """Test that TypeError is raised when `consolidate_metadata` takes an argument that
    is not a list, or a list of a single element.
    """
    cached_session = create_session(
        use_cache=True, cache_kwargs={"cache_name": cache_tmp_dir / "test"}
    )
    cached_session.cache.clear()  # clears any existing cache
    with pytest.raises(TypeError):
        consolidate_metadata(urls, cached_session)
    cached_session.cache.clear()


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
def test_valueerror_consolidate_metadata(cache_tmp_dir, urls):
    """Test that ValueError is raised when `consolidate_metadata` takes a list of
    urls that are not all the same type.
    """
    cached_session = create_session(
        use_cache=True, cache_kwargs={"cache_name": cache_tmp_dir / "test2"}
    )
    cached_session.cache.clear()
    with pytest.raises(ValueError):
        consolidate_metadata(urls, cached_session)
    cached_session.cache.clear()


@pytest.mark.parametrize(
    "urls",
    [
        ["http://localhost:8001/", "http://localhost:8002/", "http://localhost:8003/"],
        ["dap2://localhost:8001/", "dap2://localhost:8002/", "dap2://localhost:8003/"],
    ],
)
def test_warning_nondap4urls_consolidate_metadata(cache_tmp_dir, urls):
    """Test that a warning is raised when `consolidate_metadata` takes a list of urls
    that are do not have `dap4` as their scheme.
    """
    cached_session = create_session(
        use_cache=True, cache_kwargs={"cache_name": cache_tmp_dir / "test3"}
    )
    cached_session.cache.clear()
    with pytest.warns(UserWarning):
        consolidate_metadata(urls, cached_session)
    cached_session.cache.clear()


# @pytest.mark.skipif(
#     os.getenv("LOCAL_DEV") != "1", reason="This test only runs on local development"
# )
@pytest.mark.parametrize("batch", [True])
@pytest.mark.parametrize(
    "urls",
    [
        [
            "dap4://test.opendap.org/opendap/data/nc/123bears.nc",
            "dap4://test.opendap.org/opendap/data/nc/123bears.nc"
            + "?dap4.ce=/i;/j;/l;/bears",
            "dap4://test.opendap.org/opendap/data/nc/123bears.nc"
            + "?dap4.ce=/i;/j;/l;/order",
        ],
    ],
)
@pytest.mark.parametrize("safe_mode", [True])
def test_cached_consolidate_metadata_matching_dims(
    cache_tmp_dir, urls, safe_mode, batch
):
    """Test the behavior of the chaching implemented in `consolidate_metadata`.
    the `safe_mode` parameter means that all dmr urls are cached, and
    the dimensions of each dmr_url are checked for consistency.

    when `safe_mode` is False, only the first dmr url is cached if
    all dmr urls CEs are identical. If the CEs are not identical,
    then a cache is created for each dmr url with different CEs.

    In both scenarios, the dap urls of the dimensions are cached
    """
    cached_session = create_session(
        use_cache=True,
        cache_kwargs={"cache_name": cache_tmp_dir / "test3"},
    )
    cached_session.cache.clear()
    pyds = open_dmr(urls[0].replace("dap4", "http") + ".dmr")
    dims = sorted(list(pyds.dimensions))  # dimensions of full dataset
    consolidate_metadata(urls, session=cached_session, safe_mode=safe_mode, batch=batch)

    # check that the cached session has all the dmr urls and
    # caches the dap response of the dimensions only once
    # Single dap url for all dimensions downloaded
    assert len(cached_session.cache.urls()) == len(urls) + 1

    # THE FOLLOWING IS AN IMPORTANT CHECK. All dims are downloaded
    # within a single dap url. Make sure these appear in order. Order
    # matters when reusing cached urls.

    ce_dims = cached_session.cache.urls()[0].split("=")[1].split("&")[0].split("%3B")

    assert [item.split("%5B")[0] for item in ce_dims] == dims
    cached_session.cache.clear()


@pytest.mark.parametrize("batch", [True])
@pytest.mark.parametrize(
    "urls",
    [
        [
            "dap4://test.opendap.org/opendap/data/nc/123bears.nc",
            "dap4://test.opendap.org/opendap/data/nc/123bears.nc"
            + "?dap4.ce=/i;/j;/bears",
            "dap4://test.opendap.org/opendap/data/nc/123bears.nc"
            + "?dap4.ce=/i;/j;/order",
        ],
    ],
)
@pytest.mark.parametrize("safe_mode", [True])
def test_cached_consolidate_metadata_inconsistent_dims(
    cache_tmp_dir, urls, safe_mode, batch
):
    """Test the behavior of the chaching implemented in `consolidate_metadata`.
    the `safe_mode` parameter means that all dmr urls are cached, and
    the dimensions of each dmr_url are checked for consistency.

    when `safe_mode` is False, only the first dmr url is cached if
    all dmr urls CEs are identical. If the CEs are not identical,
    then a cache is created for each dmr url with different CEs.

    In both scenarios, the dap urls of the dimensions are cached
    """
    cached_session = create_session(
        use_cache=True,
        cache_kwargs={"cache_name": cache_tmp_dir / "test4"},
    )
    cached_session.cache.clear()
    pyds = open_dmr(urls[0].replace("dap4", "http") + ".dmr")
    dims = list(pyds.dimensions)  # here there are 3 dimensions
    if safe_mode:
        with pytest.warns(UserWarning):
            consolidate_metadata(
                urls, session=cached_session, safe_mode=safe_mode, batch=batch
            )
        assert len(cached_session.cache.urls()) == len(urls)
        # dmrs where cached, but not the dimensions
    else:
        consolidate_metadata(
            urls, session=cached_session, safe_mode=safe_mode, batch=batch
        )
        # caches all DMRs and caches the dap responses of the dimensions
        # of the first URL
        assert len(cached_session.cache.urls()) == len(urls) + len(dims)
    cached_session.cache.clear()


# @pytest.mark.skipif(
#     os.getenv("LOCAL_DEV") != "1", reason="This test only runs on local development"
# )
@pytest.mark.parametrize("batch", [True])
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
def test_consolidate_metadata_concat_dim(cache_tmp_dir, urls, concat_dim, batch):
    """Test the behavior of the chaching implemented in `consolidate_metadata`
    when there is a concat dimension, and (extra) this concat_dim may be an array
    of length >= 1.

    If `concat_dim` is None, only 1 dap response per dimension is cached (1 URL),
    and a special cache key is created for the rest of URLs. If `concat_dim` is set,
    then N dap responses for that dimension are cached, where N is the number of URLs.
    The rest of the (non-concat) dimensions behave the same as when `concat_dim` is
    None.

    """
    cached_session = create_session(
        use_cache=True,
        cache_kwargs={"cache_name": cache_tmp_dir / "test5"},
    )
    cached_session.cache.clear()
    # download all dmr for testing - not most performant
    consolidate_metadata(
        urls,
        session=cached_session,
        safe_mode=True,
        concat_dim=concat_dim,
        batch=batch,
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
    cached_session.cache.clear()


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


@pytest.mark.parametrize(
    "urls, common_path",
    [
        (
            [
                "http://localhost:8001/common/path/data.nc",
                "http://localhost:8001/common/path/data.nc",
                "http://localhost:8001/common/path/data.nc",
            ],
            "http://localhost:8001/common/path",
        ),
        (
            [
                "https://opendap.earthdata.nasa.gov"
                + "/providers/POCLOUD/collections/granules"
                + "/fileA.nc",
                "https://opendap.earthdata.nasa.gov"
                + "/providers/POCLOUD/collections/granules"
                + "/fileC.nc",
                "https://opendap.earthdata.nasa.gov"
                + "/providers/POCLOUD/collections/granules"
                + "/fileB.nc",
            ],
            "https://opendap.earthdata.nasa.gov"
            + "/providers/POCLOUD/collections/granules",
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
def test_patch_session_for_shared_dap_cache(cache_tmp_dir, urls):
    """Test that the session is patched correctly for shared dap cache."""
    # Clear any existing cache
    my_session = create_session(
        use_cache=True,
        cache_kwargs={"cache_name": cache_tmp_dir / "test_debug"},
    )
    my_session.cache.clear()
    # Create custom cache key for each of the dimensions
    dimensions = ["i[0:1:1]", "j[0:1:2]", "l[0:1:2]"]

    patch_session_for_shared_dap_cache(
        my_session, shared_vars=dimensions, concat_dim=None, known_url_list=urls
    )
    assert len(my_session.cache.urls()) == 0

    # construct urls to create cache keys
    test_urls = [urls[0] + ".dap?dap4.ce=" + dim for dim in dimensions]
    # create cache keys for the urls - discard the list
    _ = [my_session.get(url) for url in test_urls]

    # make sure that the urls are cached for each dimension
    assert len(my_session.cache.urls()) == len(dimensions)

    for dim in dimensions:
        test_url2 = urls[1] + ".dap?dap4.ce=" + dim
        test_url3 = urls[2] + ".dap?dap4.ce=" + dim

        # test that the urls are being cached
        r2 = my_session.get(test_url2)
        r3 = my_session.get(test_url3)

        # assert that data was cached - otherwise 404 (Non-existent URLS!)
        assert r2.from_cache
        assert r3.from_cache

    # assert that there is no new cached key
    assert len(my_session.cache.urls()) == len(dimensions)


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
def test_get_cmr_urls(cache_tmp_dir, param, expected):
    """Test that get_cmr_urls returns the correct urls."""
    session = create_session(
        use_cache=True,
        cache_kwargs={"cache_name": cache_tmp_dir / "debug_get_cmr_urls"},
    )
    session.cache.clear()
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
    session.cache.clear()


@pytest.mark.parametrize("var", ["SST"])
@pytest.mark.parametrize(
    "slice, expected",
    [
        (None, None),
        (
            (0, slice(None), slice(None)),
            {"/TIME": "[0:1:0]", "/COADSY": "[0:1:89]", "/COADSX": "[0:1:179]"},
        ),
        (
            (2, slice(0, 10, None), slice(None)),
            {"/TIME": "[2:1:2]", "/COADSY": "[0:1:9]", "/COADSX": "[0:1:179]"},
        ),
    ],
)
def test_register_dim_slices(var, slice, expected):
    """Test that dim slices are registered correctly."""
    url = "http://test.opendap.org/opendap/data/nc/coads_climatology.nc"
    session = requests.Session()
    pyds = open_url(url, session=session, protocol="dap4", batch=True)
    pyds.register_dim_slices(pyds[var], key=slice)
    assert pyds._slices == expected

    # reset registered slices and check
    pyds.register_dim_slices(pyds[var], key=None)
    assert pyds._slices is None

    pyds.clear_dim_slices()
    assert pyds._slices is None


@pytest.mark.parametrize("var", ["/SimpleGroup/Salinity"])
@pytest.mark.parametrize(
    "slice_, expected",
    [
        (None, None),
        ((0, slice(0, 10, None), slice(0, 10, None)), None),
    ],
)
def test_register_dim_slices_dimension_different_hierarchy(var, slice_, expected):
    """
    Test for an edge case in which one of the dimension lies on a different hierarchy.
    This makes sure the slice is handled properly.
    """
    url = "dap4://test.opendap.org/opendap/dap4/SimpleGroup.nc4.h5"
    session = requests.Session()
    pyds = open_url(url, session=session, batch=True)
    pyds.register_dim_slices(pyds[var], key=slice_)
    slices = pyds._slices
    assert slices == expected


@pytest.mark.parametrize(
    "queries",
    [
        [
            ".dap?dap4.ce="
            + "COADSX%5B0%3A1%3A179%5D%3BCOADSY%5B0%3A1%3A89%5D&dap4.checksum=true",
            ".dap?dap4.ce=" + "TIME%5B0%3A1%3A11%5D&dap4.checksum=true",
            ".dmr",
        ],
    ],
)
@pytest.mark.parametrize(
    "baseurl",
    [
        "http://test.opendap.org/opendap/hyrax/data/nc/coads_climatology.nc",
        "http://test.opendap.org/opendap/hyrax/data/nc/coads_climatology2.nc",
    ],
)
def test_recover_missing_url(queries, baseurl):
    """
    This test requires emulating the behavior of `consolidate_metadata` with
    `concat_dim=TIME", for the present list composed of [url1, url2].
    `consolidate_metadata` caches/creates a list of dap responses one per granule
    of array `TIME`, but only downloads/caches the response of one of the url
    for the rest of the dimensions. The function tested recovers the reused dap url
    for any given `baseurl`, and returns both that reusable dap url, and any present
    dap url that matches the `baseurl` (e.g. that of `TIME`).

    """

    url1 = "http://test.opendap.org/opendap/hyrax/data/nc/coads_climatology.nc"
    url2 = "http://test.opendap.org/opendap/hyrax/data/nc/coads_climatology2.nc"

    # the following 4 urls are typically expected:
    urls1 = [
        url1 + query for query in queries if not query.startswith(".dap?dap4.ce=COADSX")
    ]
    urls2 = [
        url2 + query for query in queries if not query.startswith(".dap?dap4.ce=COADSX")
    ]
    cached_urls = urls1 + urls2

    # we add the dap url that is cached and test that we can recover ir from the
    # baseurl that is not cached
    if baseurl == url1:
        # add url2 to the cached list, with the correct query parameters
        cached_dap = [
            url2 + query for query in queries if query.startswith(".dap?dap4.ce=COADSX")
        ]
    elif baseurl == url2:
        # add url1 to the cached list, with the correct query parameters
        cached_dap = [
            url1 + query for query in queries if query.startswith(".dap?dap4.ce=COADSX")
        ]

    cached_urls += cached_dap

    miss_url, current_dap = recover_missing_url(cached_urls, baseurl)

    # assert that simply from base url I can recored the correct cached dap url
    assert miss_url == cached_dap


@pytest.mark.parametrize(
    "url",
    [
        "dap4://test.opendap.org/opendap/hyrax/data/nc/coads_climatology.nc",
        "dap4://test.opendap.org/opendap/hyrax/data/nc/coads_climatology2.nc",
    ],
)
def test_fetch_consolidated(url):
    """Test that fetch_consolidated works as expected."""
    db_session = CachedSession(cache_name=sqlite_db)
    assert len(db_session.cache.urls()) == 5
    pyds = open_url(url, session=db_session)
    fetch_consolidated(pyds)
    for name in ["TIME", "COADSX", "COADSY"]:
        var = pyds[name]
        assert isinstance(var, BaseType)
        assert hasattr(var, "ndim")
        assert hasattr(var, "dtype")
        assert isinstance(var.data, np.ndarray)


@pytest.mark.parametrize("group", ["/", "/SimpleGroup"])
def test_fetched_batched(cache_tmp_dir, group):
    url = "dap4://test.opendap.org/opendap/dap4/SimpleGroup.nc4.h5"
    session = create_session(
        use_cache=True,
        cache_kwargs={"cache_name": cache_tmp_dir / "debug_fetched_batched"},
    )
    session.cache.clear()
    pyds = open_url(url, session=session, batch=True)
    session.cache.clear()

    # batch dimensions with fully qualifying names
    dims = [
        pyds[group][name].id
        for name in pyds[group].dimensions
        if name in pyds[group].keys() and isinstance(pyds[group][name], BaseType)
    ]

    pyds.register_dim_slices(pyds[dims[0]], key=None)
    register_all_for_batch(pyds, dims)
    # assign data to variables
    fetch_batched(pyds, dims)
    # checks
    for var in dims:
        assert isinstance(pyds[var].data, np.ndarray)
    assert len(session.cache.urls()) == 1  # single dap url
    session.cache.clear()


@pytest.mark.parametrize("dims", [True, False])
@pytest.mark.parametrize("group", ["/", "/SimpleGroup"])
def test_get_batch_data(cache_tmp_dir, dims, group):
    """
    Test that `get_batch_data` works as expected.
    """
    url = "dap4://test.opendap.org/opendap/dap4/SimpleGroup.nc4.h5"
    session = create_session(
        use_cache=True,
        cache_kwargs={"cache_name": cache_tmp_dir / "debug_get_batch_data"},
    )
    session.cache.clear()
    pyds = open_url(url, session=session, batch=True)
    session.cache.clear()
    if dims:
        var_name = list(pyds[group].dimensions)[0]
    else:
        variables = [
            var
            for var in pyds[group].variables()
            if isinstance(pyds[group][var], BaseType)
            and var not in pyds[group].dimensions
        ]
        var_name = variables[0]

    get_batch_data(pyds[group][var_name], checksums=True)
    assert len(session.cache.urls()) == 1  # single dap url

    if dims:
        for name in pyds[group].dimensions:
            if name in pyds[group].keys() and isinstance(pyds[group][name], BaseType):
                assert pyds[group][name]._is_data_loaded()
    else:
        for name in pyds[group].variables():
            if name not in pyds[group].dimensions and isinstance(
                pyds[group][name], BaseType
            ):
                assert pyds[group][name]._is_data_loaded()
    session.cache.clear()


@pytest.mark.parametrize(
    "url, group, var, skip_var, key, expected_ce, expected_shape",
    [
        (
            "http://test.opendap.org/opendap/dap4/SimpleGroup.nc4.h5",
            "/",
            "/Pressure",
            "",
            slice(0, 500, None),
            "/Z=[0:1:499];/Pressure;/time_bnds",
            (500,),
        ),
        (
            "http://test.opendap.org/opendap/hyrax/data/nc/coads_climatology.nc",
            "/",
            "/SST",
            "",
            (0, slice(0, 10, None), slice(10, 20, 2)),
            "/TIME=[0:1:0];/COADSY=[0:1:9];/COADSX=[10:2:19];/AIRT;/SST;/UWND;/VWND",
            (1, 10, 5),
        ),
        (
            (
                "http://test.opendap.org/opendap/hyrax/"
                + "NSIDC/ATL08_20181016124656_02730110_002_01.h5?dap4.ce="
                + "/gt1l/land_segments/delta_time;/gt1l/land_segments/delta_time;"
                + "/gt1l/land_segments/latitude;/gt1l/land_segments/longitude"
            ),
            "/gt1l/land_segments",
            "/gt1l/land_segments/latitude",
            "",
            slice(0, 50, None),
            "/gt1l/land_segments/delta_time=[0:1:49];"
            + "/gt1l/land_segments/latitude;/gt1l/land_segments/longitude",
            (50,),
        ),
        (
            "http://test.opendap.org/opendap/dap4/SimpleGroup.nc4.h5",
            "/SimpleGroup",
            "/SimpleGroup/Salinity",
            "Temperature",
            (0, slice(0, 10, None), slice(10, 20, None)),
            "/SimpleGroup/Salinity[0:1:0][0:1:39][0:1:39]",
            (1, 40, 40),  # <------- check this. I think there should be a warning.
        ),
    ],
)
def test_get_batch_data_sliced_nondims(
    cache_tmp_dir, url, group, var, skip_var, key, expected_ce, expected_shape
):
    """
    Test that when passing a slice to `get_batch_data`, the correct
    CE is generated.
    """
    session = create_session(
        use_cache=True,
        cache_kwargs={
            "cache_name": cache_tmp_dir / "debug_get_batch_data_sliced_nondims"
        },
    )
    session.cache.clear()
    pyds = open_url(url, protocol="dap4", session=session, batch=True)
    session.cache.clear()

    # get all non-dim variables
    variables = [
        pyds[group][var].id
        for var in sorted(pyds[group].variables())
        if isinstance(pyds[group][var], BaseType)
        and var not in list(pyds[group].dimensions) + [skip_var]
    ]
    assert var in variables
    # register the slice for the variable
    pyds.register_dim_slices(pyds[variables[0]], key=key)
    register_all_for_batch(pyds, variables)
    fetch_batched(pyds, variables)

    assert pyds[var].shape == expected_shape

    query = session.cache.urls()[-1].split("dap4.ce=")[1].split("&")[0]
    query = query.replace("%3D", "=").replace("%3B", ";").replace("%2F", "/")
    assert (
        query.replace("%5B", "[").replace("%5D", "]").replace("%3A", ":") == expected_ce
    )
    session.cache.clear()


@pytest.mark.parametrize(
    "var_batch, key_batch, var_name, var_key, expected_shape",
    [
        (
            "Eta",
            (slice(None, 1, None), slice(10, 20, None), slice(10, 20, None)),
            "U",
            (slice(None, 1, None), slice(10, 20, None), slice(10, 21, None)),
            (1, 10, 11),
        ),
        (
            "Eta",
            (slice(None, 1, None), 2, slice(10, 20, None)),
            "U",
            (slice(None, 1, None), 2, slice(10, 21, None)),
            (1, 11),
        ),
        (
            "Eta",
            (slice(None, 1, None), slice(10, 20, None), slice(10, 20, None)),
            "V",
            (slice(None, 1, None), slice(10, 21, None), slice(10, 20, None)),
            (1, 11, 10),
        ),
        (
            "Eta",
            (0, slice(10, 20, None), 10),
            "V",
            (0, slice(10, 21, None), 10),
            (11,),
        ),
    ],
)
def test_data_check(var_batch, key_batch, var_name, var_key, expected_shape):
    """
    Tests that
    """
    url = "dap4://test.opendap.org/opendap/dap4/StaggeredGrid.nc4"
    pyds = open_url(url, batch=True)

    # eagerly download data using a shared dimensions contraint expression
    # the CE only makes use of dimensions in ``ETA``. Other variables
    # with dimensions NOT shared with ETA are not sliced.
    get_batch_data(pyds[var_batch], key=key_batch)

    # check data needs to be sliced
    assert pyds[var_name].shape != expected_shape

    var = np.asarray(pyds[var_name].data)
    data = data_check(var, var_key)

    assert data.shape == expected_shape


def test_consolidate_metadata_non_batch(cache_tmp_dir):
    """Test that consolidate_metadata raises an error when batch=False"""
    urls = [
        "dap4://test.opendap.org/opendap/hyrax/data/nc/coads_climatology.nc",
        "dap4://test.opendap.org/opendap/hyrax/data/nc/coads_climatology2.nc",
    ]
    cache_name = cache_tmp_dir / "test_consolidate_metadata_non_batch"
    cached_session = create_session(
        use_cache=True,
        cache_kwargs={"cache_name": cache_name},
    )
    cached_session.cache.clear()
    consolidate_metadata(
        urls,
        session=cached_session,
        concat_dim="TIME",
        batch=False,
    )

    assert cached_session.settings.key_fn._concat_dim == ["TIME"]
    assert cached_session.settings.key_fn._collapse_vars == {"COADSX", "COADSY"}

    N = len(urls)  # N of DMRS
    N_non_concat_dims = 2  # COADSX, COADSY
    N_concat_dims = 3 * len(urls)  # TIME
    assert len(cached_session.cache.urls()) == N + N_non_concat_dims + N_concat_dims

    # check that all URLS from COADSX and COADSY are cached, even when only 1 of each
    # was downloaded
    map1 = _quote("/COADSX[0:1:179]").replace("/", "%2F")
    map2 = _quote("/COADSY[0:1:89]").replace("/", "%2F")

    dap_urls = [
        url.replace("dap4", "http") + ".dap?dap4.ce=" + map1 + "&dap4.checksum=true"
        for url in urls
    ]
    dap_urls += [
        url.replace("dap4", "http") + ".dap?dap4.ce=" + map2 + "&dap4.checksum=true"
        for url in urls
    ]

    for url in dap_urls:
        if url not in cached_session.cache.urls():
            r = cached_session.get(url)
            assert r.from_cache


def test_consolidate_non_matching_dims(cache_tmp_dir):
    """Test that consolidate warns when dmrs have non matching dimensions"""
    urls = [
        "dap4://test.opendap.org/opendap/hyrax/data/nc/coads_climatology.nc",
        "dap4://test.opendap.org/opendap/dap4/SimpleGroup.nc4.h5",
    ]
    cache_name = cache_tmp_dir / "test_consolidate_non_matching_dims"
    cached_session = create_session(
        use_cache=True,
        cache_kwargs={"cache_name": cache_name},
    )
    cached_session.cache.clear()
    with pytest.warns(
        UserWarning,
        match="The dimensions of the datasets are not identical across all datasets",
    ):
        consolidate_metadata(
            urls,
            session=cached_session,
            concat_dim="TIME",
        )
    assert "consolidated" not in cached_session.headers
    cached_session.cache.clear()
