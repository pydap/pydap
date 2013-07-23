"""Test the DAP handlers, which forms the core of the client."""

import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest

from webtest import TestApp
import requests
import numpy as np

from pydap.model import StructureType, GridType
from pydap.handlers.lib import BaseHandler, ConstraintExpression
from pydap.handlers.dap import DAPHandler, BaseProxy, SequenceProxy
from pydap.tests.datasets import SimpleSequence, SimpleGrid
from pydap.tests import requests_intercept


class TestDapHandler(unittest.TestCase):

    """Test that the handler creates the correct dataset from a URL."""

    def setUp(self):
        """Create WSGI apps and monkeypatch ``requests`` for direct access."""
        self.app1 = TestApp(BaseHandler(SimpleGrid))
        self.app2 = TestApp(BaseHandler(SimpleSequence))
        self.requests_get = requests.get

    def tearDown(self):
        """Return method to its original version."""
        requests.get = self.requests_get

    def test_grid(self):
        """Test that dataset has the correct data proxies for grids."""
        requests.get = requests_intercept(self.app1, "http://localhost:8001/")
        dataset = DAPHandler("http://localhost:8001/").dataset

        self.assertEqual(dataset.keys(), ["SimpleGrid", "x", "y"])
        self.assertEqual(
            dataset.SimpleGrid.keys(), ["SimpleGrid", "x", "y"])

        # test one of the axis
        self.assertIsInstance(dataset.SimpleGrid.x.data, BaseProxy)
        self.assertEqual(
            dataset.SimpleGrid.x.data.baseurl, "http://localhost:8001/")
        self.assertEqual(dataset.SimpleGrid.x.data.id, "SimpleGrid.x")
        self.assertEqual(dataset.SimpleGrid.x.data.dtype, np.dtype('>i4'))
        self.assertEqual(dataset.SimpleGrid.x.data.shape, (3,))
        self.assertEqual(
            dataset.SimpleGrid.x.data.slice, (slice(None),))

        # test the grid
        self.assertIsInstance(dataset.SimpleGrid.SimpleGrid.data, BaseProxy)
        self.assertEqual(
            dataset.SimpleGrid.SimpleGrid.data.baseurl,
            "http://localhost:8001/")
        self.assertEqual(
            dataset.SimpleGrid.SimpleGrid.data.id, "SimpleGrid.SimpleGrid")
        self.assertEqual(
            dataset.SimpleGrid.SimpleGrid.data.dtype, np.dtype('>i4'))
        self.assertEqual(dataset.SimpleGrid.SimpleGrid.data.shape, (2, 3))
        self.assertEqual(
            dataset.SimpleGrid.SimpleGrid.data.slice,
            (slice(None), slice(None)))

    def test_grid_with_projection(self):
        """Test that a sliced proxy can be created for grids."""
        requests.get = requests_intercept(self.app1, "http://localhost:8001/")
        dataset = DAPHandler("http://localhost:8001/?SimpleGrid[0]").dataset

        self.assertEqual(dataset.SimpleGrid.x.data.shape, (1,))
        self.assertEqual(dataset.SimpleGrid.x.data.slice, (slice(0, 1, 1),))
        self.assertEqual(dataset.SimpleGrid.y.data.shape, (2,))
        self.assertEqual(dataset.SimpleGrid.y.data.slice, (slice(0, 3, 1),))
        self.assertEqual(dataset.SimpleGrid.SimpleGrid.data.shape, (1, 3))
        self.assertEqual(
            dataset.SimpleGrid.SimpleGrid.data.slice,
            (slice(0, 1, 1), slice(0, 3, 1)))

    def test_base_type_with_projection(self):
        """Test that a sliced proxy can be created for a base type."""
        requests.get = requests_intercept(self.app1, "http://localhost:8001/")
        dataset = DAPHandler("http://localhost:8001/?x[1:1:2]").dataset

        self.assertEqual(dataset.x.data.shape, (2,))
        self.assertEqual(dataset.x.data.slice, (slice(1, 3, 1),))

    def test_grid_array_with_projection(self):
        """Test that a grid array can be properly pre sliced."""
        requests.get = requests_intercept(self.app1, "http://localhost:8001/")
        dataset = DAPHandler(
            "http://localhost:8001/?SimpleGrid.SimpleGrid[0]").dataset

        # object should be a structure, not a grid
        self.assertEqual(dataset.keys(), ["SimpleGrid"])
        self.assertNotIsInstance(dataset.SimpleGrid, GridType)
        self.assertIsInstance(dataset.SimpleGrid, StructureType)

        self.assertEqual(dataset.SimpleGrid.SimpleGrid.data.shape, (1, 3))
        self.assertEqual(
            dataset.SimpleGrid.SimpleGrid.data.slice,
            (slice(0, 1, 1), slice(0, 3, 1)))

    def test_grid_map_with_projection(self):
        """Test that a grid map can be properly pre sliced."""
        requests.get = requests_intercept(self.app1, "http://localhost:8001/")
        dataset = DAPHandler("http://localhost:8001/?SimpleGrid.x[0]").dataset

        self.assertEqual(dataset.SimpleGrid.x.data.shape, (1,))
        self.assertEqual(
            dataset.SimpleGrid.x.data.slice,
            (slice(0, 1, 1),))

    def test_sequence(self):
        """Test that dataset has the correct data proxies for sequences."""
        requests.get = requests_intercept(self.app2, "http://localhost:8001/")
        dataset = DAPHandler("http://localhost:8001/").dataset

        self.assertEqual(dataset.keys(), ["cast"])
        self.assertEqual(
            dataset.cast.keys(), [
                'id', 'lon', 'lat', 'depth', 'time', 'temperature', 'salinity',
                'pressure'])

        # check the sequence
        self.assertIsInstance(dataset.cast.data, SequenceProxy)
        self.assertEqual(
            dataset.cast.data.baseurl, "http://localhost:8001/")
        self.assertEqual(dataset.cast.data.id, "cast")
        self.assertEqual(
            dataset.cast.data.descr,  (
                'cast', 
                [
                    ('id', '|S128', ()), 
                    ('lon', '>i', ()), 
                    ('lat', '>i', ()), 
                    ('depth', '>i', ()), 
                    ('time', '>i', ()), 
                    ('temperature', '>i', ()), 
                    ('salinity', '>i', ()), 
                    ('pressure', '>i', ())],
                ()))
        self.assertEqual(
            dataset.cast.data.dtype,
            np.dtype([
                ('id', 'S128'),
                ('lon', '>i4'),
                ('lat', '>i4'),
                ('depth', '>i4'),
                ('time', '>i4'),
                ('temperature', '>i4'),
                ('salinity', '>i4'),
                ('pressure', '>i4')]))
        self.assertEqual(dataset.cast.data.shape, ())
        self.assertEqual(dataset.cast.data.selection, [])
        self.assertEqual(dataset.cast.data.slice, (slice(None),))

        # check a child
        self.assertIsInstance(dataset.cast.lon.data, SequenceProxy)
        self.assertEqual(
            dataset.cast.lon.data.baseurl, "http://localhost:8001/")
        self.assertEqual(dataset.cast.lon.data.id, "cast.lon")
        self.assertEqual(
            dataset.cast.lon.data.descr, ('cast', ('lon', '>i', ()), ()))
        self.assertEqual(dataset.cast.lon.data.dtype, np.dtype(">i4"))
        self.assertEqual(dataset.cast.lon.data.selection, [])
        self.assertEqual(dataset.cast.lon.data.slice, (slice(None),))

    def test_sequence_with_projection(self):
        """Test projections applied to sequences."""
        requests.get = requests_intercept(self.app2, "http://localhost:8001/")
        dataset = DAPHandler(
            "http://localhost:8001/?cast[1]").dataset

        self.assertEqual(dataset.cast.data.slice, (slice(1, 2, 1),))
        #self.assertEqual(
        #    [tuple(row) for row in dataset.cast], [
        #        ('2', 200, 10, 500, 1, 15, 35, 100)])


class TestSequenceProxy(unittest.TestCase):

    """Test that a ``SequenceProxy`` behaves like a Numpy structured array."""

    def setUp(self):
        """Create a WSGI app and monkeypatch ``requests`` for direct access."""
        app = TestApp(BaseHandler(SimpleSequence))
        self.local = SimpleSequence.cast.data

        self.requests_get = requests.get
        requests.get = requests_intercept(app, "http://localhost:8001/")
        dataset = DAPHandler("http://localhost:8001/").dataset
        self.remote = dataset.cast.data

    def tearDown(self):
        """Return method to its original version."""
        requests.get = self.requests_get

    def test_dtype(self):
        """Test dtype."""
        self.assertEqual(
            self.local.dtype,
            np.dtype([
                ('id', 'S1'),
                ('lon', '<i8'),
                ('lat', '<i8'),
                ('depth', '<i8'),
                ('time', '<i8'),
                ('temperature', '<i8'),
                ('salinity', '<i8'),
                ('pressure', '<i8')]))

        # dtype is different because of strings, integers and endianess
        self.assertEqual(
            self.remote.dtype,
            np.dtype([
                ('id', 'S128'),
                ('lon', '>i4'),
                ('lat', '>i4'),
                ('depth', '>i4'),
                ('time', '>i4'),
                ('temperature', '>i4'),
                ('salinity', '>i4'),
                ('pressure', '>i4')]))

    def test_dtype_child(self):
        """Test dtype of children."""
        self.assertEqual(self.local['time'].dtype, "<i8")
        self.assertEqual(self.remote['time'].dtype, ">i4")

    def test_iter(self):
        """Test iteration."""
        self.assertEqual(
            [tuple(row) for row in self.local], [
                ('1', 100, -10, 0, -1, 21, 35, 0),
                ('2', 200, 10, 500, 1, 15, 35, 100)]) 

        self.assertEqual(
            [tuple(row) for row in self.remote], [
                ('1', 100, -10, 0, -1, 21, 35, 0), 
                ('2', 200, 10, 500, 1, 15, 35, 100)])

    def test_projection(self):
        """Test if we can select only a few variables."""
        filtered = self.local[["salinity", "depth"]]
        self.assertEqual(
            filtered.dtype, np.dtype([('salinity', '<i8'), ('depth', '<i8')]))
        self.assertEqual(
            [tuple(row) for row in filtered], [(35, 0), (35, 500)])

        filtered = self.remote[["salinity", "depth"]]
        self.assertEqual(
            filtered.dtype, np.dtype([('salinity', '>i4'), ('depth', '>i4')]))
        self.assertEqual(
            [tuple(row) for row in filtered], [(35, 0), (35, 500)])

    def test_iter_child(self):
        """Test iteration over a child."""
        child = self.local["salinity"]
        self.assertEqual(list(child), [35, 35])

        child = self.remote["salinity"]
        self.assertEqual(list(child), [35, 35])

    def test_filtering(self):
        """Test filtering of data."""
        filtered = self.local[self.local["lon"] > 100]
        self.assertEqual(
            [tuple(row) for row in filtered], [
                ('2', 200, 10, 500, 1, 15, 35, 100)]) 

        filtered = self.remote[self.remote["lon"] > 100]
        self.assertEqual(
            [tuple(row) for row in filtered], [
                ('2', 200, 10, 500, 1, 15, 35, 100)]) 

        # filtering works because we store comparisons as lazy objects
        self.assertIsInstance(self.remote["lon"] > 100, ConstraintExpression)
        self.assertEqual(filtered.selection, ['cast.lon>100'])
