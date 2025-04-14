"""Test the pydap client."""

import os

import numpy as np
import pytest
import requests

from ..client import (
    compute_base_url_prefix,
    consolidate_metadata,
    open_dmr,
    open_dods_url,
    open_file,
    open_url,
    patch_session_for_shared_dap_cache,
)
from ..handlers.lib import BaseHandler
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
    assert data_dap4["s33"][:].data == data_original["s33"][0, 0].data

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
    data = ds_ce["lon"][:]
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
    with pytest.warns(Warning):
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
    with pytest.warns(Warning):
        consolidate_metadata(urls, cached_session)


ce1 = "?dap4.ce=/i[0:1:1];/j[0:1:2];/bears[0:1:1][0:1:2];/l[0:1:2]"


@pytest.mark.parametrize(
    "urls",
    [
        [
            "dap4://test.opendap.org/opendap/data/nc/123bears.nc",
            "dap4://test.opendap.org/opendap/data/nc/123bears.nc" + ce1,
        ],
    ],
)
def test_cached_consolidate_metadata(urls, cached_session):
    """Test that `consolidate_metadata` effectively caches the dmr of the urls, along
    with the dap4 urls of the dimensions
    """
    cached_session.cache.clear()
    pyds = open_dmr(urls[0].replace("dap4", "http") + ".dmr")
    dims = list(pyds.dimensions)  # dimensions of full dataset

    consolidate_metadata(urls, cached_session)
    # check that the cached session has all the dmr urls and
    # caches the dap response of the dimensions only once
    assert len(cached_session.cache.urls()) == len(urls) + len(dims)
    # THE FOLLOWING IS AN IMPORTANT CHECK. THE EXTRA CACHED URLS
    # ARE THE DAP RESPONSES OF EACH DIMENSION. AND THESE ARE THE LAST
    # TO CACHE. MEANING THE FIRST ELEMENTS OF THE LIST OF CACHED URLS.
    dap_urls = [url.replace("dap4", "http") for url in urls]
    dim_dap_urls = [dap_urls[0] + ".dap?dap4.ce=" + dim for dim in dims]
    N = len(dims)  # should be 3 for this dataset.
    for n in range(N):
        assert cached_session.cache.urls()[n].split("%")[0] == dim_dap_urls[n]


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
        cached_session, shared_vars=dimensions, known_url_list=urls
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
