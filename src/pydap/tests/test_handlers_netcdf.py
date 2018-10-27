"""Test the DAP handler, which forms the core of the client."""

import numpy as np
from six.moves import zip
from pydap.handlers.dap import DAPHandler
import pytest


@pytest.fixture(scope='module')
def simple_data():
    data = [(10, 15.2, 'Diamond_St'),
            (11, 13.1, 'Blacktail_Loop'),
            (12, 13.3, 'Platinum_St'),
            (13, 12.1, 'Kodiak_Trail')]
    return data


@pytest.fixture(scope='module')
def simple_nc_file(simple_data, tmpdir_factory):
    from netCDF4 import Dataset
    file_name = str(tmpdir_factory.mktemp('nc').join('simple.nc'))
    with Dataset(file_name, 'w') as output:
        output.createDimension('index', None)
        temp = output.createVariable('index', '<i4', ('index',))
        split_data = zip(*simple_data)
        temp[:] = next(split_data)
        temp = output.createVariable('temperature', '<f8', ('index',))
        temp[:] = next(split_data)
        temp = output.createVariable('station', 'S40', ('index',))
        for item_id, item in enumerate(next(split_data)):
            temp[item_id] = item
    return file_name


@pytest.fixture(scope='module')
def simple_handler(simple_nc_file):
    from pydap.handlers.netcdf import NetCDFHandler
    return NetCDFHandler(simple_nc_file)


def test_handler(simple_data, simple_handler):
    """Test that dataset has the correct data proxies for grids."""
    dataset = simple_handler.dataset
    dtype = [('index', '<i4'),
             ('temperature', '<f8'),
             ('station', 'S40')]
    retrieved_data = list(zip(dataset['index'][:],
                              dataset['temperature'].array[:],
                              dataset['station'].array[:]))
    np.testing.assert_array_equal(np.array(retrieved_data, dtype=dtype),
                                  np.array(simple_data, dtype=dtype))


@pytest.fixture(scope='module')
def simple_application(simple_handler):
    from pydap.wsgi.ssf import ServerSideFunctions
    return ServerSideFunctions(simple_handler)


def test_open(simple_data, simple_application):
    """Test that NetCDFHandler can be read through open_url."""
    dataset = DAPHandler("http://localhost:8001/", simple_application).dataset
    dtype = [('index', '<i4'),
             ('temperature', '<f8'),
             ('station', 'S40')]
    retrieved_data = list(zip(dataset['index'][:],
                              dataset['temperature'].array[:],
                              dataset['station'].array[:]))
    np.testing.assert_array_equal(np.array(retrieved_data, dtype=dtype),
                                  np.array(simple_data, dtype=dtype))
