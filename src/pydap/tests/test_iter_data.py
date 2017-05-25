"""Test IterData, which makes iterables behave like Numpy structured arrays."""

import numpy as np
from pydap.handlers.lib import IterData
from pydap.model import DatasetType, SequenceType, BaseType
import pytest


@pytest.fixture
def simple_array():
    arr = np.array([
            (0, 1, 10.),
            (1, 2, 20.),
            (2, 3, 30.),
            (3, 4, 40.),
            (4, 5, 50.),
            (5, 6, 60.),
            (6, 7, 70.),
            (7, 8, 80.),
        ], dtype=[('byte', 'b'), ('int', 'i4'), ('float', 'f4')])
    return arr


@pytest.fixture
def simple_object(simple_array):
    # add sequence and children for each column
    name = 'nameless'
    dataset = DatasetType(name)
    seq = dataset['sequence'] = SequenceType('sequence')
    for var in simple_array.dtype.names:
        seq[var] = BaseType(var)

    obj = IterData([(0, 1, 10.),
                    (1, 2, 20.),
                    (2, 3, 30.),
                    (3, 4, 40.),
                    (4, 5, 50.),
                    (5, 6, 60.),
                    (6, 7, 70.),
                    (7, 8, 80.)],
                   seq)
    return obj


def test_iter(simple_array, simple_object):
    assert ([tuple(row)
             for row in simple_array] ==
            [(0, 1, 10.), (1, 2, 20.),
             (2, 3, 30.), (3, 4, 40.),
             (4, 5, 50.), (5, 6, 60.),
             (6, 7, 70.), (7, 8, 80.)])
    assert (list(simple_array["byte"]) ==
            [0, 1, 2, 3, 4, 5, 6, 7])

    assert ([tuple(row) for row in simple_object] ==
            [(0, 1, 10.), (1, 2, 20.),
             (2, 3, 30.), (3, 4, 40.),
             (4, 5, 50.), (5, 6, 60.),
             (6, 7, 70.), (7, 8, 80.)])
    assert (list(simple_object["byte"]) ==
            [0, 1, 2, 3, 4, 5, 6, 7])


def test_dtype(simple_array, simple_object):
    assert (
        simple_array.dtype ==
        np.dtype([('byte', 'i1'), ('int', '<i4'), ('float', '<f4')]))
    assert (simple_array["int"].dtype == "<i4")

    assert (
        simple_object.dtype ==
        np.dtype([('byte', '<i8'), ('int', '<i8'), ('float', '<f8')]))
    assert (simple_object["int"].dtype == "<i8")


def test_selection(simple_array, simple_object):
    selection = simple_array[simple_array["byte"] > 3]
    assert ([tuple(row) for row in selection] ==
            [(4, 5, 50.), (5, 6, 60.),
             (6, 7, 70.), (7, 8, 80.)])

    selection = simple_object[simple_object["byte"] > 3]
    assert ([tuple(row) for row in selection] ==
            [(4, 5, 50.), (5, 6, 60.),
             (6, 7, 70.), (7, 8, 80.)])


def test_projection(simple_array, simple_object):
    projection = simple_array[1::2]
    assert ([tuple(row) for row in projection] ==
            [(1, 2, 20.), (3, 4, 40.),
             (5, 6, 60.), (7, 8, 80.)])
    assert (
        list(simple_array["byte"][1::2]) == [1, 3, 5, 7])
    assert (
        list(simple_array[1::2]["byte"]) == [1, 3, 5, 7])

    projection = simple_object[1::2]
    assert ([tuple(row) for row in projection] ==
            [(1, 2, 20.), (3, 4, 40.),
             (5, 6, 60.), (7, 8, 80.)])
    assert (
        list(simple_object["byte"][1::2]) == [1, 3, 5, 7])
    assert (
        list(simple_object[1::2]["byte"]) == [1, 3, 5, 7])


def test_combined(simple_array, simple_object):
    filtered = simple_array[simple_array["byte"] > 1]
    filtered = filtered[filtered["byte"] < 6]
    filtered = filtered[::2]
    assert ([tuple(row) for row in filtered] ==
            [(2, 3, 30.), (4, 5, 50.)])

    filtered = simple_object[simple_object["byte"] > 1]
    filtered = filtered[filtered["byte"] < 6]
    filtered = filtered[::2]
    assert ([tuple(row) for row in filtered] ==
            [(2, 3, 30.), (4, 5, 50.)])


def test_combined_other(simple_array, simple_object):
    filtered = simple_array[['int', 'float']][simple_array["byte"] < 2]
    assert ([tuple(row) for row in filtered] ==
            [(1, 10.), (2, 20.)])

    filtered = simple_object[['int', 'float']][simple_object["byte"] < 2]
    assert ([tuple(row) for row in filtered] ==
            [(1, 10.), (2, 20.)])


@pytest.fixture
def nested_data():
        shallow_data = [(1, 1, 1), (2, 4, 4),
                        (3, 6, 9), (4, 8, 16)]
        deep_data = [[(10, 11, 12), (21, 22, 23)],
                     [(15, 16, 17)],
                     [],
                     [(31, 32, 33), (41, 42, 43),
                      (51, 52, 53), (61, 62, 63)]]
        nested = [x + (deep_data[x_id],)
                  for x_id, x
                  in enumerate(shallow_data)]
        return nested


@pytest.fixture
def nested_dtype():
        dtype = np.dtype([('a', '<i8'), ('b', '<i8'),
                          ('c', '<i8'),
                          ('d', np.dtype([('e', '<i8'),
                                          ('f', '<i8'),
                                          ('g', '<i8')]))])
        return dtype


@pytest.fixture
def nested_object(nested_data):
        name = 'nameless'
        dataset = DatasetType(name)
        seq = dataset['nested'] = SequenceType('nested')
        for var in ['a', 'b', 'c']:
            seq[var] = BaseType(var)
        seq['d'] = SequenceType('d')
        for var in ['e', 'f', 'g']:
            seq['d'][var] = BaseType(var)

        nested = IterData(nested_data, seq)
        return nested


def test_nested_iter(nested_data, nested_object):
    assert ([tuple(row) for row in nested_object] ==
            nested_data)


def test_nested_iter_child(nested_data, nested_object):
    expected = [row[0] for row in nested_data]
    assert list(nested_object["a"]) == expected


def test_nested_iter_nested_sequence(nested_data, nested_object):
    expected = [row[3] for row in nested_data]
    assert list(nested_object["d"]) == expected


def test_nested_iter_nested_deep_child(nested_data, nested_object):
    expected = [[col[0] for col in row[3]]
                for row in nested_data]
    assert list(nested_object['d']['e']) == expected


def test_nested_dtype(nested_dtype, nested_object):
    assert nested_object.dtype == nested_dtype


def test_nested_selection(nested_data, nested_object):
    selection = nested_object[nested_object["a"] > 2]
    expected = [tuple(row) for row in nested_data
                if row[0] > 2]
    assert [tuple(row) for row in selection] == expected


def test_nested_projection(nested_data, nested_object):
    projection = nested_data[1::2]
    expected = [tuple(row) for row_id, row
                in enumerate(nested_data)
                if row_id in range(1, len(nested_data), 2)]
    assert [tuple(row) for row in projection] == expected

    projection = nested_object[1::2]
    expected = [tuple(row) for row_id, row
                in enumerate(nested_data)
                if row_id in range(1, len(nested_data), 2)]
    assert [tuple(row) for row in projection] == expected


def test_nested_combined(nested_data, nested_object):
    filtered = [tuple(row) for row in nested_data
                if row[0] > 2]
    filtered = [tuple(row) for row in filtered
                if row[0] < 4]
    filtered = filtered[::2]
    assert ([tuple(row) for row in filtered] ==
            [(3, 6, 9, [])])

    filtered = nested_object[nested_object["a"] > 2]
    filtered = filtered[filtered["a"] < 4]
    filtered = filtered[::2]
    assert ([tuple(row) for row in filtered] ==
            [(3, 6, 9, [])])
