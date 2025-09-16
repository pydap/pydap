"""Test the basic DAP functions."""

import unittest
from sys import maxsize as MAXSIZE

import numpy as np
import pytest
from requests_cache import CachedSession

from pydap.client import consolidate_metadata, open_url
from pydap.exceptions import ConstraintExpressionError
from pydap.lib import (
    _quote,
    combine_slices,
    encode,
    fetch_batched,
    fetch_consolidated,
    fix_shorthand,
    fix_slice,
    get_batch_data,
    get_var,
    hyperslab,
    recover_missing_url,
    register_all_for_batch,
    tree,
    walk,
)
from pydap.model import BaseType, DatasetType, SequenceType, StructureType
from pydap.net import create_session


class TestQuote(unittest.TestCase):
    """Test quoting.

    According to the DAP 2 specification a variable name MUST contain only
    upper or lower case letters, numbers, or characters from the set

        _ ! ~ * ' - "

    All other characters must be escaped. This includes the period, which is
    normally not quoted by ``urllib.quote``.

    """

    def test_quoting(self):
        """Test a simple quoting."""
        self.assertEqual(_quote("White space"), "White%20space")

    def test_quoting_period(self):
        """Test if period is also quoted."""
        self.assertEqual(_quote("Period."), "Period%2E")


class TestEncode(unittest.TestCase):
    """Test encoding.

    According to the DAP 2 specification, numbers must be encoded using the C
    notation "%.6g". Other objects are encoded as escaped strings.

    """

    def test_integer(self):
        """Test integer encoding."""
        self.assertEqual(encode(1), "1")

    def test_float(self):
        """Test floating encoding."""
        self.assertEqual(encode(np.pi), "3.14159")

    def test_string(self):
        """Test string encoding."""
        self.assertEqual(encode("test"), '"test"')

    def test_string_with_quotation(self):
        """Test encoding a string with a quotation mark."""
        self.assertEqual(encode('this is a "test"'), '"this is a "test""')

    def test_unicode(self):
        """Unicode objects are encoded just like strings."""
        self.assertEqual(encode("test"), '"test"')

    def test_obj(self):
        """Other objects are encoded according to their ``repr``."""
        self.assertEqual(encode({}), '"{}"')

    def test_numpy_string(self):
        self.assertEqual(encode(np.array("1", dtype="<U1")), '"1"')

    def test_numpy_ndim_gt_0(self):
        # test a numpy array with ndim > 0
        # associated with Deprecation warning numpy > 1.25
        # see GH issue https://github.com/pydap/pydap/issues/319
        # also PR https://github.com/pydap/pydap/pull/343
        array = np.array([(2.300110099991, 4.0)])
        self.assertEqual(encode(array), '"[[2.300110 4.000000]]"')


class TestFixSlice(unittest.TestCase):
    """Test the ``fix_slice`` function."""

    def test_not_tuple(self):
        """Non tuples should be converted and handled correctly."""
        x = np.arange(10)

        slice1 = 0
        slice2 = fix_slice(slice1, x.shape)

        # ``fix_slice`` will convert to a tuple
        self.assertEqual(slice2, (0,))

        # assert that the slice is equivalent to the original
        np.testing.assert_array_equal(x[slice1], x[slice2])

    def test_ellipsis(self):
        """Expand Ellipsis to occupy the missing dimensions."""
        x = np.arange(6).reshape(2, 3, 1)

        slice1 = Ellipsis, 0
        slice2 = fix_slice(slice1, x.shape)

        # an Ellipsis is expanded to slice(None)
        self.assertEqual(slice2, ((slice(0, 2, 1), slice(0, 3, 1), 0)))
        np.testing.assert_array_equal(x[slice1], x[slice2])

    def test_negative_int(self):
        """Negative values are converted to positive."""
        x = np.arange(10)

        slice1 = -5
        slice2 = fix_slice(slice1, x.shape)

        self.assertEqual(slice2, (5,))
        np.testing.assert_array_equal(x[slice1], x[slice2])

    def test_negative_start(self):
        """Test for slices with a negative start."""
        x = np.arange(10)

        slice1 = slice(-8, 8)
        slice2 = fix_slice(slice1, x.shape)

        self.assertEqual(slice2, (slice(2, 8, 1),))
        np.testing.assert_array_equal(x[slice1], x[slice2])

    def test_negative_stop(self):
        """Test for slices with a negative stop."""
        x = np.arange(10)

        slice1 = slice(2, -2)
        slice2 = fix_slice(slice1, x.shape)

        self.assertEqual(slice2, (slice(2, 8, 1),))
        np.testing.assert_array_equal(x[slice1], x[slice2])

    def test_non_zero_slicestart(self):
        x = np.arange(0, 100)
        slice1 = slice(50, 100)
        slice2 = fix_slice(slice1, x.shape)
        self.assertEqual(slice2, (slice(50, 100, 1),))

    def test_non_zero_slicestart_projection(self):
        """test fix_slice with projection=True. This is used when
        CE includes projection (`[start:stop:step]) that results
        in a slice whose stop element is greater than the dimension size.
        """
        x = np.arange(0, 100)
        sub_x = x[:50]
        slice1 = slice(50, 100)
        slice2 = fix_slice(slice1, sub_x.shape, projection=True)
        self.assertEqual(slice2, (slice(50, 100, 1),))

    def test_last_index_slicestart(self):
        x = np.arange(0, 100)
        slice1 = slice(-1, None, None)
        slice2 = fix_slice(slice1, x.shape)
        self.assertEqual(slice2, (slice(99, 100, 1),))


class TestCombineSlices(unittest.TestCase):
    """Test the ``combine_slices`` function."""

    def test_not_tuple(self):
        """The function fails when one of the slices is not a tuple."""
        slice1 = 0
        slice2 = (0,)
        with self.assertRaises(TypeError):
            combine_slices(slice1, slice2)
        with self.assertRaises(TypeError):
            combine_slices(slice2, slice1)

    def test_integer(self):
        """Test slices that are just integers."""
        slice1 = (0,)
        slice2 = (1,)
        combined = combine_slices(slice1, slice2)
        self.assertEqual(combined, (slice(1, 1, 1),))

    def test_stops_none(self):
        """Test when both of the slices have ``None`` for stop."""
        x = np.arange(10)
        slice1 = (slice(0, None),)
        slice2 = (slice(5, None),)
        combined = combine_slices(slice1, slice2)
        self.assertEqual(combined, (slice(5, None, 1),))
        np.testing.assert_array_equal(x[combined], x[slice1][slice2])

    def test_first_stop_none(self):
        """Test when the first slice has ``None`` for stop."""
        x = np.arange(10)
        slice1 = (slice(5, None),)
        slice2 = (slice(0, 8),)
        combined = combine_slices(slice1, slice2)
        self.assertEqual(combined, (slice(5, 13, 1),))
        np.testing.assert_array_equal(x[combined], x[slice1][slice2])

    def test_second_stop_none(self):
        """Test when the second slice has ``None`` for stop."""
        x = np.arange(10)
        slice1 = (slice(0, 8),)
        slice2 = (slice(5, None),)
        combined = combine_slices(slice1, slice2)
        self.assertEqual(combined, (slice(5, 8, 1),))
        np.testing.assert_array_equal(x[combined], x[slice1][slice2])

    def test_all_values(self):
        """Test when start and stop are all integers."""
        x = np.arange(20)
        slice1 = (slice(0, 8),)
        slice2 = (slice(5, 6),)
        combined = combine_slices(slice1, slice2)
        self.assertEqual(combined, (slice(5, 6, 1),))
        np.testing.assert_array_equal(x[combined], x[slice1][slice2])


class TestHyperslab(unittest.TestCase):
    """Test hyperslab generation from Python slices."""

    def test_no_tuple(self):
        """Test that slices that are not tuples work."""
        slice_ = slice(0)
        self.assertEqual(hyperslab(slice_), "[0:1:%d]" % (MAXSIZE - 1))

    def test_remove(self):
        """Test that excess slices are removed."""
        slice_ = (slice(0), slice(None))
        self.assertEqual(hyperslab(slice_), "[0:1:%d]" % (MAXSIZE - 1))

    def test_ndimensional(self):
        """Test n-dimensions slices."""
        slice_ = (slice(1, 10, 1), slice(2, 10, 2))
        self.assertEqual(hyperslab(slice_), "[1:1:9][2:2:9]")


class TestWalk(unittest.TestCase):
    """Test the ``walk`` function to iterate over a dataset."""

    def setUp(self):
        """Create a basic dataset."""
        self.dataset = DatasetType("a")
        self.dataset["b"] = BaseType("b")
        self.dataset["c"] = StructureType("c")
        self.dataset["d"] = SequenceType("d")

    def test_walk(self):
        """Test that all variables are yielded."""
        self.assertEqual(
            list(walk(self.dataset)),
            [self.dataset, self.dataset.b, self.dataset.c, self.dataset.d],
        )

    def test_walk_type(self):
        """Test the filtering of variables yielded."""
        self.assertEqual(list(walk(self.dataset, BaseType)), [self.dataset.b])
        self.assertEqual(list(walk(self.dataset, SequenceType)), [self.dataset.d])


class TestTree(unittest.TestCase):
    """Test the ``tree`` func"""

    def setUp(self):
        self.dataset = DatasetType("name")
        self.dataset["a"] = BaseType("a")
        self.dataset.createGroup("Group1")
        self.dataset.createSequence("/Group1/Seq1")
        self.dataset.createVariable("/Group1/Seq1/b")
        self.dataset.createVariable("/Group1/Seq1/c")
        self.dataset["d"] = StructureType("d")
        self.dataset["e"] = SequenceType("e")

    def test_tree_repr(self):
        self.assertEqual(self.dataset.tree(), tree(self.dataset))
        self.assertEqual(self.dataset["Group1"].tree(), tree(self.dataset["Group1"]))


class TestFixShorthand(unittest.TestCase):
    """Test the ``fix_shorthand`` function."""

    def test_fix_projection(self):
        """Test a dataset that can use the shorthand notation."""
        dataset = DatasetType("a")
        dataset["b"] = StructureType("b")
        dataset["b"]["c"] = BaseType("c")

        projection = [[("c", ())]]
        self.assertEqual(fix_shorthand(projection, dataset), [[("b", ()), ("c", ())]])

    def test_conflict(self):
        """Test a dataset with conflicting short names."""
        dataset = DatasetType("a")
        dataset["b"] = StructureType("b")
        dataset["b"]["c"] = BaseType("c")
        dataset["d"] = StructureType("d")
        dataset["d"]["c"] = BaseType("c")

        projection = [[("c", ())]]
        with self.assertRaises(ConstraintExpressionError):
            fix_shorthand(projection, dataset)


class TestGetVar(unittest.TestCase):
    """Test the ``get_var`` function."""

    def test_get_var(self):
        """Test that the id is returned properly."""
        dataset = DatasetType("a")
        dataset["b"] = StructureType("b")
        dataset["b"]["c"] = BaseType("c")

        self.assertEqual(get_var(dataset, "b.c"), dataset["b"]["c"])


url1 = "http://test.opendap.org/opendap/hyrax/data/nc/coads_climatology.nc"
url2 = "http://test.opendap.org/opendap/hyrax/data/nc/coads_climatology2.nc"


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
@pytest.mark.parametrize("baseurl", [url1, url2])
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


# prep a consolidated session for the next test
urls = [
    "dap4://test.opendap.org/opendap/hyrax/data/nc/coads_climatology.nc",
    "dap4://test.opendap.org/opendap/hyrax/data/nc/coads_climatology2.nc",
]
session = CachedSession()
session.cache.clear()
consolidate_metadata(urls, session=session, concat_dim="TIME")


@pytest.mark.parametrize("url", [urls[0], urls[1]])
def test_fetch_consolidated(url, session=session):
    """Test that fetch_consolidated works as expected."""
    pyds = open_url(url, session=session)
    fetch_consolidated(pyds)
    for name in ["TIME", "COADSX", "COADSY"]:
        var = pyds[name]
        assert isinstance(var, BaseType)
        assert hasattr(var, "ndim")
        assert hasattr(var, "dtype")
        assert isinstance(var.data, np.ndarray)


@pytest.mark.parametrize("group", ["/", "/SimpleGroup"])
def test_fetched_batched(group):
    url = "dap4://test.opendap.org/opendap/dap4/SimpleGroup.nc4.h5"
    session = create_session(use_cache=True, cache_kwargs={"cache_name": "debug"})
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


@pytest.mark.parametrize("dims", [True, False])
@pytest.mark.parametrize("group", ["/", "/SimpleGroup"])
def test_get_batch_data(dims, group):
    """
    Test that `get_batch_data` works as expected.
    """
    url = "dap4://test.opendap.org/opendap/dap4/SimpleGroup.nc4.h5"
    session = create_session(use_cache=True, cache_kwargs={"cache_name": "debug"})
    session.cache.clear()
    pyds = open_url(url, session=session, batch=True)
    session.cache.clear()
    if dims:
        var_name = list(pyds[group].dimensions)[0]
    else:
        variables = [
            var for var in pyds[group].variables() if var not in pyds[group].dimensions
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


url1 = "http://test.opendap.org/opendap/dap4/SimpleGroup.nc4.h5"
url2 = "http://test.opendap.org/opendap/hyrax/data/nc/coads_climatology.nc"
url3 = (
    "http://"
    + "test.opendap.org/opendap/hyrax/NSIDC/ATL08_20181016124656_02730110_002_01.h5?"
    + "dap4.ce=/gt1l/land_segments/delta_time;/gt1l/land_segments/delta_time;"
    + "/gt1l/land_segments/latitude;/gt1l/land_segments/longitude"
)


@pytest.mark.parametrize(
    "url, group, var, key, expected_ce, expected_shape",
    [
        (
            url1,
            "/",
            "/Pressure",
            slice(0, 500, None),
            "/Z=[0:1:499];/Pressure;/time_bnds",
            (500,),
        ),
        (
            url2,
            "/",
            "/SST",
            (0, slice(0, 10, None), slice(10, 20, 2)),
            "/TIME=[0:1:0];/COADSY=[0:1:9];/COADSX=[10:2:19];/AIRT;/SST;/UWND;/VWND",
            (1, 10, 5),
        ),
        (
            url3,
            "/gt1l/land_segments",
            "/gt1l/land_segments/latitude",
            slice(0, 50, None),
            "/gt1l/land_segments/delta_time=[0:1:49];"
            + "/gt1l/land_segments/latitude;/gt1l/land_segments/longitude",
            (50,),
        ),
        (
            url1 + "?dap4.ce=/time;/SimpleGroup/Y;/SimpleGroup/X;/SimpleGroup/Salinity",
            "/SimpleGroup",
            "/SimpleGroup/Salinity",
            (0, slice(0, 10, None), slice(10, 20, None)),
            "/SimpleGroup/Salinity[0:1:0][0:1:39][0:1:39]",
            (1, 40, 40),  # <------- check this. I think there should be a warning.
        ),
    ],
)
def test_get_batch_data_sliced_nondims(
    url, group, var, key, expected_ce, expected_shape
):
    """
    Test that when passing a slice to `get_batch_data`, the correct
    CE is generated.
    """
    session = create_session(use_cache=True, cache_kwargs={"cache_name": "debug"})
    session.cache.clear()
    pyds = open_url(url, protocol="dap4", session=session, batch=True)
    session.cache.clear()

    # get all non-dim variables
    variables = [
        pyds[group][var].id
        for var in sorted(pyds[group].variables())
        if var not in list(pyds[group].dimensions)
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
