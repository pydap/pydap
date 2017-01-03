"""Datasets for testing.

This module defines a few datasets for testing, covering the whole DAP data
model.

"""
import os

import numpy as np

from pydap.model import (DatasetType, BaseType,
                         SequenceType, GridType, StructureType)
from pydap.handlers.lib import IterData
from pydap.client import open_file

from collections import OrderedDict


# A very simple sequence: flat and with no strings. This sequence can be mapped
# directly to a Numpy structured array, and can be easily encoded and decoded
# in the DAP spec.
VerySimpleSequence = DatasetType("VerySimpleSequence")
VerySimpleSequence["sequence"] = SequenceType("sequence")
VerySimpleSequence["sequence"]["byte"] = BaseType("byte")
VerySimpleSequence["sequence"]["int"] = BaseType("int")
VerySimpleSequence["sequence"]["float"] = BaseType("float")
VerySimpleSequence["sequence"].data = np.array([
    (0, 1, 10.),
    (1, 2, 20.),
    (2, 3, 30.),
    (3, 4, 40.),
    (4, 5, 50.),
    (5, 6, 60.),
    (6, 7, 70.),
    (7, 8, 80.),
    ], dtype=[('byte', 'b'), ('int', 'i4'), ('float', 'f4')])


# A nested sequence.
NestedSequence = DatasetType("NestedSequence")
NestedSequence["location"] = SequenceType("location")
NestedSequence["location"]["lat"] = BaseType("lat")
NestedSequence["location"]["lon"] = BaseType("lon")
NestedSequence["location"]["elev"] = BaseType("elev")
NestedSequence["location"]["time_series"] = SequenceType("time_series")
NestedSequence["location"]["time_series"]["time"] = BaseType("time")
NestedSequence["location"]["time_series"]["slp"] = BaseType("slp")
NestedSequence["location"]["time_series"]["wind"] = BaseType("wind")
NestedSequence["location"].data = IterData([
    (1, 1, 1, [(10, 11, 12), (21, 22, 23)]),
    (2, 4, 4, [(15, 16, 17)]),
    (3, 6, 9, []),
    (4, 8, 16, [(31, 32, 33), (41, 42, 43), (51, 52, 53), (61, 62, 63)]),
    ], NestedSequence.location)


# A simple array with bytes, strings and shorts. These types require special
# encoding for the DODS response.
SimpleArray = DatasetType("SimpleArray")
SimpleArray["byte"] = BaseType("byte", np.arange(5, dtype="b"))
SimpleArray["string"] = BaseType("string", np.array(["one", "two"]))
SimpleArray["short"] = BaseType("short", np.array(1, dtype="h"))


DODS = os.path.join(
    os.path.dirname(__file__), 'rainfall_time_malaysia.cdp.dods')
DAS = os.path.join(os.path.dirname(__file__), 'rainfall_time_malaysia.cdp.das')
dapper = open_file(DODS, DAS)


# dataset from http://test.opendap.org:8080/dods/dts/D1.asc
D1 = DatasetType('EOSDB.DBO', type='Drifters')
D1['Drifters'] = SequenceType('Drifters')
D1['Drifters']['instrument_id'] = BaseType('instrument_id')
D1['Drifters']['location'] = BaseType('location')
D1['Drifters']['latitude'] = BaseType('latitude')
D1['Drifters']['longitude'] = BaseType('longitude')
D1.Drifters.data = np.array(np.rec.fromrecords(list(zip(
    [u"This is a data test string (pass {0}).".format(1+i*2)
     for i in range(5)],
    [u"This is a data test string (pass {0}).".format(i*2) for i in range(5)],
    [1000.0, 999.95, 999.80, 999.55, 999.20],
    [999.95, 999.55, 998.75, 997.55, 995.95])),
    names=D1.Drifters.keys()))


# testing structures
SimpleStructure = DatasetType('SimpleStructure')
SimpleStructure['types'] = StructureType(
    name='types',
    key="value",
    nested=OrderedDict([
        ("string", "bar"),
        ("list", [42, 43]),
        ("array", np.array(1)),
        ("float", 1000.0),
    ]))
SimpleStructure['types']['b'] = BaseType('b', np.array(0, np.byte))
SimpleStructure['types']['i32'] = BaseType('i32', np.array(1, np.int32))
SimpleStructure['types']['ui32'] = BaseType('ui32', np.array(0, np.uint32))
SimpleStructure['types']['i16'] = BaseType('i16', np.array(0, np.int16))
SimpleStructure['types']['ui16'] = BaseType('ui16', np.array(0, np.uint16))
SimpleStructure['types']['f32'] = BaseType('f32', np.array(0.0, np.float32))
SimpleStructure['types']['f64'] = BaseType('f64', np.array(1000., np.float64))
SimpleStructure['types']['s'] = BaseType(
    's', np.array("This is a data test string (pass 0)."))
SimpleStructure['types']['u'] = BaseType('u', np.array("http://www.dods.org"))


# test grid
rain = DatasetType('test')
rain['rain'] = GridType('rain')
rain['rain']['rain'] = BaseType(
    'rain', np.arange(6).reshape(2, 3), dimensions=('y', 'x'))
rain['rain']['x'] = BaseType('x', np.arange(3), units='degrees_east')
rain['rain']['y'] = BaseType('y', np.arange(2), units='degrees_north')


# test for ``bounds`` function
bounds = DatasetType('test')
bounds['sequence'] = SequenceType('sequence')
bounds['sequence']['lon'] = BaseType('lon', axis='X')
bounds['sequence']['lat'] = BaseType('lat', axis='Y')
bounds['sequence']['depth'] = BaseType('depth', axis='Z')
bounds['sequence']['time'] = BaseType(
    'time', axis='T', units="days since 1970-01-01")
bounds['sequence']['measurement'] = BaseType('measurement')
bounds.sequence.data = np.array(np.rec.fromrecords([
    (100, -10, 0, -1, 42),
    (200, 10, 500, 1, 43),
], names=bounds.sequence.keys()))


# test for density
ctd = DatasetType('ctd')
ctd['cast'] = SequenceType('cast')
ctd['cast']['temperature'] = BaseType('temperature')
ctd['cast']['salinity'] = BaseType('salinity')
ctd['cast']['pressure'] = BaseType('pressure')
ctd.cast.data = np.array(np.rec.fromrecords([
    (21, 35, 0),
    (15, 35, 100),
], names=ctd.cast.keys()))

# a simple sequence, simulating a CTD profile
SimpleSequence = DatasetType(
    "SimpleSequence", description="A simple sequence for testing.",
    nested={"value": 42})
SimpleSequence["cast"] = SequenceType("cast")
SimpleSequence["cast"]["id"] = BaseType("id")
SimpleSequence["cast"]["lon"] = BaseType("lon", axis="X")
SimpleSequence["cast"]["lat"] = BaseType("lat", axis="Y")
SimpleSequence["cast"]["depth"] = BaseType("depth", axis="Z")
SimpleSequence["cast"]["time"] = BaseType(
    "time", axis="T", units="days since 1970-01-01")
SimpleSequence["cast"]["temperature"] = BaseType("temperature")
SimpleSequence["cast"]["salinity"] = BaseType("salinity")
SimpleSequence["cast"]["pressure"] = BaseType("pressure")
SimpleSequence["cast"].data = np.array(np.rec.fromrecords([
    ("1", 100, -10,   0, -1, 21, 35,   0),
    ("2", 200,  10, 500,  1, 15, 35, 100),
], names=SimpleSequence['cast'].keys()))
# SimpleSequence["cast"].data = IterData([
#     ("1", 100, -10,   0, -1, 21, 35,   0),
#     ("2", 200,  10, 500,  1, 15, 35, 100),
# ], SimpleSequence.cast)

# a simple grid
SimpleGrid = DatasetType(
    "SimpleGrid", description="A simple grid for testing.")
SimpleGrid["SimpleGrid"] = GridType("SimpleGrid")
SimpleGrid["SimpleGrid"]["SimpleGrid"] = BaseType(
    "SimpleGrid", np.arange(6).reshape(2, 3), dimensions=("y", "x"))
SimpleGrid["x"] = SimpleGrid["SimpleGrid"]["x"] = BaseType(
    "x", np.arange(3), axis="X", units="degrees_east")
SimpleGrid["y"] = SimpleGrid["SimpleGrid"]["y"] = BaseType(
    "y", np.arange(2), axis="Y", units="degrees_north")
