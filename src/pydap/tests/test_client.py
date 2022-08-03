"""Test the pydap client."""

import os
import numpy as np
from pydap.handlers.lib import BaseHandler
from pydap.client import open_url, open_dods_url, open_file
from pydap.tests.datasets import SimpleSequence, SimpleGrid, SimpleStructure
import pytest


DODS = os.path.join(os.path.dirname(__file__), 'data/test.01.dods')
DAS = os.path.join(os.path.dirname(__file__), 'data/test.01.das')


@pytest.fixture
def sequence_app():
    return BaseHandler(SimpleSequence)


@pytest.fixture
def structure_app():
    return BaseHandler(SimpleStructure)


@pytest.mark.client
def test_open_url(sequence_app):
    """Open an URL and check dataset keys."""
    dataset = open_url('http://localhost:8001/', sequence_app)
    assert list(dataset.keys()) == ["cast"]


@pytest.mark.client
def test_open_dods():
    """Open a file downloaded from the test server with the DAS."""
    dataset = open_file(DODS)

    # test data
    assert dataset.data == [
        0, 1, 0, 0, 0, 0.0, 1000.0,
        'This is a data test string (pass 0).',
        'http://www.dods.org',
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
        0, 1, 0, 0, 0, 0.0, 1000.0,
        'This is a data test string (pass 0).',
        'http://www.dods.org',
    ]

    # test attributes
    assert (dataset.i32.units == 'unknown')
    assert (dataset.i32.Description == 'A 32 bit test server int')
    assert (dataset.b.units == 'unknown')
    assert (dataset.b.Description == 'A test byte')
    assert (
        dataset.Facility['DataCenter'] ==
        "COAS Environmental Computer Facility")
    assert (
        dataset.Facility['PrincipleInvestigator'] ==
        ['Mark Abbott', 'Ph.D'])
    assert (
        dataset.Facility['DrifterType'] ==
        "MetOcean WOCE/OCM")


@pytest.mark.client
def test_open_dods_16bits(sequence_app):
    """Open the dods response from a server.

    Note that here we cannot simply compare ``dataset.data`` with the
    original data ``SimpleSequence.data``, because the original data
    contains int16 values which are transmitted as int32 in the DAP spec.

    """
    dataset = open_dods_url('.dods', application=sequence_app)
    assert (
        list(dataset.data) == [[
            ('1', 100, -10, 0, -1, 21, 35, 0),
            ('2', 200, 10, 500, 1, 15, 35, 100),
        ]])

    # attributes should be empty
    assert dataset.attributes == {}


@pytest.mark.client
def test_open_dods_with_attributes(sequence_app):
    """Open the dods response together with the das response."""
    dataset = open_dods_url('.dods', metadata=True, application=sequence_app)
    assert (dataset.NC_GLOBAL == {})
    assert (dataset.DODS_EXTRA == {})
    assert (
        dataset.description == "A simple sequence for testing.")
    assert (dataset.cast.lon.axis == 'X')
    assert (dataset.cast.lat.axis == 'Y')
    assert (dataset.cast.depth.axis == 'Z')
    assert (dataset.cast.time.axis == 'T')
    assert (
        dataset.cast.time.units == "days since 1970-01-01")


@pytest.fixture(scope='session')
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
    original = open_url('/', application=ssf_app)
    assert (original.SimpleGrid.SimpleGrid.shape == (2, 3))


def test_first_axis(ssf_app):
    """Test mean over the first axis."""
    original = open_url('/', application=ssf_app)
    dataset = original.functions.mean(original.SimpleGrid, 0)
    assert (dataset.SimpleGrid.SimpleGrid.shape == (3,))
    np.testing.assert_array_equal(
        dataset.SimpleGrid.SimpleGrid.data,
        np.array([1.5, 2.5, 3.5]))


def test_second_axis(ssf_app):
    """Test mean over the second axis."""
    original = open_url('/', application=ssf_app)
    dataset = original.functions.mean(original.SimpleGrid, 1)
    assert (dataset.SimpleGrid.SimpleGrid.shape == (2,))
    np.testing.assert_array_equal(
        dataset.SimpleGrid.SimpleGrid.data,
        np.array([1.0, 4.0]))


def test_lazy_evaluation_getitem(ssf_app):
    """Test that the dataset is only loaded when accessed."""
    original = open_url('/', application=ssf_app)
    dataset = original.functions.mean(original.SimpleGrid, 0)
    assert dataset.dataset is None
    dataset['SimpleGrid']
    assert dataset.dataset is not None


def test_lazy_evaluation_getattr(ssf_app):
    """Test that the dataset is only loaded when accessed."""
    original = open_url('/', application=ssf_app)
    dataset = original.functions.mean(original.SimpleGrid, 0)
    assert dataset.dataset is None
    dataset.SimpleGrid
    assert dataset.dataset is not None


def test_nested_call(ssf_app):
    """Test nested calls."""
    original = open_url('/', application=ssf_app)
    dataset = original.functions.mean(
        original.functions.mean(original.SimpleGrid, 0), 0)
    assert (dataset['SimpleGrid']['SimpleGrid'].shape == ())
    np.testing.assert_array_equal(
        dataset.SimpleGrid.SimpleGrid.data,
        np.array(2.5))


def test_axis_mean(ssf_app):
    """Test the mean over an axis, returning a scalar."""
    original = open_url('/', application=ssf_app)
    dataset = original.functions.mean(original.SimpleGrid.x)
    assert (dataset.x.shape == ())
    np.testing.assert_array_equal(
        dataset.x.data,
        np.array(1.0))


@pytest.mark.client
def test_int16(structure_app):
    """Test that 16-bit values are represented correctly.

    Even though the DAP transfers int16 and uint16 as 32 bits, we want them to
    be represented locally using the correct type.

    Load an int16 -> should yield '>i2' type."""
    dataset = open_url("http://localhost:8001/", structure_app)
    assert (dataset.types.i16.dtype == np.dtype(">i2"))


@pytest.mark.client
def test_uint16(structure_app):
    """Test that 16-bit values are represented correctly.

    Even though the DAP transfers int16 and uint16 as 32 bits, we want them to
    be represented locally using the correct type.

    Load an uint16 -> should yield '>u2' type."""
    dataset = open_url("http://localhost:8001/", structure_app)
    assert (dataset.types.ui16.dtype == np.dtype(">u2"))
