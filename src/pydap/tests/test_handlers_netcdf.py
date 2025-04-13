"""Test the DAP handler, which forms the core of the client."""

import numpy as np
import pytest
from netCDF4 import Dataset

from pydap.handlers.netcdf import NetCDFHandler


@pytest.fixture(scope="module")
def simple_data():
    data = [
        (10, 15.2, "Diamond_St"),
        (11, 13.1, "Blacktail_Loop"),
        (12, 13.3, "Platinum_St"),
        (13, 12.1, "Kodiak_Trail"),
    ]
    return data


@pytest.fixture(scope="module")
def simple_nc_file(simple_data, tmpdir_factory):
    file_name = str(tmpdir_factory.mktemp("nc").join("simple.nc"))
    with Dataset(file_name, "w") as output:
        output.createDimension("index", None)
        temp = output.createVariable("index", "<i4", ("index",))
        split_data = zip(*simple_data)
        temp[:] = next(split_data)
        temp = output.createVariable("temperature", "<f8", ("index",))
        temp[:] = next(split_data)
        temp = output.createVariable("station", "S40", ("index",))
        for item_id, item in enumerate(next(split_data)):
            temp[item_id] = item
    return file_name


@pytest.fixture(scope="module")
def simple_Group_data():
    data = np.arange(10, 26, 1, dtype="f4").reshape(1, 4, 4)
    return data


@pytest.fixture(scope="module")
def simple_group_array_file(simple_Group_data, tmpdir_factory):
    file_name = str(tmpdir_factory.mktemp("nc").join("Group_array.nc"))
    with Dataset(file_name, "w") as output:
        output.createDimension("time", None)  # unlimited dimension
        output.createDimension("nv", 2)  # unlimited dimension
        output.createVariable("time", "<f8", ("time",))
        output.createVariable("time_nbds", "<f8", ("time", "nv"))
        group = output.createGroup("Group")
        group.createDimension("X", 4)
        group.createDimension("Y", 4)
        group.createVariable("X", "<i4", ("X",))
        group.createVariable("Y", "<i4", ("Y",))
        group.createVariable("temperature", np.float32, ("time", "Y", "X"))
        group["temperature"][:] = simple_Group_data
    return file_name


@pytest.fixture(scope="module")
def nested_group_array_file(simple_Group_data, tmpdir_factory):
    file_name = str(tmpdir_factory.mktemp("nc").join("NestedGroup_array.nc"))
    with Dataset(file_name, "w") as output:
        output.createDimension("time", None)  # unlimited dimension
        output.createVariable("time", "<f8", ("time",))
        group1 = output.createGroup("Group")
        subgroup1 = group1.createGroup("SubGroup")
        subgroup1.createDimension("X", 4)
        subgroup1.createDimension("Y", 4)
        subgroup1.createVariable("X", "<i4", ("X",))
        subgroup1.createVariable("Y", "<i4", ("Y",))
        subgroup1.createVariable("temperature", np.float32, ("time", "Y", "X"))
        subgroup1["temperature"][:] = simple_Group_data
    return file_name


@pytest.fixture(scope="module")
def nested_group_repeatdims_file(tmpdir_factory):
    file_name = str(tmpdir_factory.mktemp("nc").join("unaligned_subgroups.nc"))
    with Dataset(file_name, "w", format="NETCDF4") as root_group:
        group_1 = root_group.createGroup("/Group1")
        subgroup_1 = group_1.createGroup("/subgroup1")

        root_group.createDimension("lat", 1)
        root_group.createDimension("lon", 2)
        root_group.createVariable("root_variable", np.float64, ("lat", "lon"))

        group_1_var = group_1.createVariable("group_1_var", np.float64, ("lat", "lon"))
        group_1_var[:] = np.array([[0.1, 0.2]])
        group_1_var.units = "K"
        group_1_var.long_name = "air_temperature"

        subgroup_1.createDimension("lat", 2)

        subgroup1_var = subgroup_1.createVariable(
            "subgroup1_var", np.float64, ("lat", "lon")
        )
        subgroup1_var[:] = np.array([[0.1, 0.2]])
    return file_name


@pytest.fixture(scope="module")
def simple_handler(simple_nc_file):
    return NetCDFHandler(simple_nc_file)


@pytest.fixture(scope="module")
def simple_handler2(simple_group_array_file):
    return NetCDFHandler(simple_group_array_file)


@pytest.fixture(scope="module")
def simple_handler3(nested_group_array_file):
    return NetCDFHandler(nested_group_array_file)


@pytest.fixture(scope="module")
def simple_handler4(nested_group_repeatdims_file):
    return NetCDFHandler(nested_group_repeatdims_file)


def test_handler(simple_data, simple_handler):
    """Test that dataset has the correct data proxies for grids."""
    dataset = simple_handler.dataset
    dtype = [("index", "<i4"), ("temperature", "<f8"), ("station", "S40")]
    retrieved_data = list(
        zip(
            dataset["index"][:],
            dataset["temperature"][:],
            dataset["station"][:],
        )
    )
    np.testing.assert_array_equal(
        np.array(retrieved_data, dtype=dtype), np.array(simple_data, dtype=dtype)
    )


def test_handler_array(simple_Group_data, simple_handler2):
    """Test that dataset has the correct data proxies for grids."""
    dataset = simple_handler2.dataset
    r_dims = dataset.dimensions
    g_dims = dataset["Group"].attributes["dimensions"]
    temp = dataset["/Group/temperature"][:]
    np.testing.assert_array_equal(temp.data, simple_Group_data)
    assert r_dims == {"time": 1, "nv": 2}
    assert g_dims == {"X": 4, "Y": 4}
    assert temp.dims == ["/time", "/Group/Y", "/Group/X"]


def test_handler_nested_Group_array(simple_Group_data, simple_handler3):
    """Test that dataset has the correct data proxies for grids."""
    dataset = simple_handler3.dataset
    r_dims = dataset.dimensions
    g_dims = dataset["Group"].attributes["dimensions"]
    sg_dims = dataset["/Group/SubGroup"].attributes["dimensions"]
    temp = dataset["/Group/SubGroup/temperature"][:]
    np.testing.assert_array_equal(temp.data, simple_Group_data)
    assert r_dims == {"time": 1}
    assert g_dims == {}
    assert sg_dims == {"X": 4, "Y": 4}
    assert temp.dims == ["/time", "/Group/SubGroup/Y", "/Group/SubGroup/X"]


def test_handler_repeatdims_Group_array(simple_handler4):
    """Test that dataset has the correct data proxies for grids."""
    dataset = simple_handler4.dataset
    r_dims = dataset.dimensions
    g_dims = dataset["Group1"].dimensions
    var_g1 = dataset["Group1/group_1_var"].dims
    sg_dims = dataset["Group1/subgroup1"].dimensions
    var_sg1 = dataset["Group1/subgroup1/subgroup1_var"].dims
    assert r_dims == {"lat": 1, "lon": 2}
    assert g_dims == {}
    assert sg_dims == {"lat": 2}
    assert var_g1 == ["/lat", "/lon"]
    assert var_sg1 == ["/Group1/subgroup1/lat", "/lon"]


@pytest.fixture(scope="module")
def simple_application(simple_handler):
    from pydap.wsgi.ssf import ServerSideFunctions

    return ServerSideFunctions(simple_handler)


# def test_open(simple_data, simple_application):
#     """Test that NetCDFHandler can be read through open_url."""
#     dataset = DAPHandler("http://localhost:8001/", simple_application).dataset
#     dtype = [("index", "<i4"), ("temperature", "<f8"), ("station", "S40")]
#     retrieved_data = list(
#         zip(
#             dataset["index"][:],
#             dataset["temperature"][:],
#             dataset["station"][:],
#         )
#     )
#     np.testing.assert_array_equal(
#         np.array(retrieved_data, dtype=dtype), np.array(simple_data, dtype=dtype)
#     )
