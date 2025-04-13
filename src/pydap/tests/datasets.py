"""Datasets for testing.

This module defines a few datasets for testing, covering the whole DAP data
model.

"""

import os
from collections import OrderedDict

import numpy as np

from pydap.client import open_file
from pydap.handlers.lib import IterData
from pydap.model import BaseType, DatasetType, GridType

# Note that DAP2 does not support signed bytes (signed 8bits integers).

# A very simple sequence: flat and with no strings. This sequence can be mapped
# directly to a Numpy structured array, and can be easily encoded and decoded
# in the DAP spec.
VerySimpleSequence = DatasetType("VerySimpleSequence")
VerySimpleSequence.createSequence("/sequence")
VerySimpleSequence.createVariable("/sequence.byte")
VerySimpleSequence.createVariable("/sequence.int")
VerySimpleSequence.createVariable("/sequence.float")
VerySimpleSequence["/sequence"].data = np.array(
    [
        (0, 1, 10.0),
        (1, 2, 20.0),
        (2, 3, 30.0),
        (3, 4, 40.0),
        (4, 5, 50.0),
        (5, 6, 60.0),
        (6, 7, 70.0),
        (7, 8, 80.0),
    ],
    dtype=[("byte", np.ubyte), ("int", "i4"), ("float", "f4")],
)


# A nested sequence.
NestedSequence = DatasetType("NestedSequence")
NestedSequence.createSequence("/location")
NestedSequence.createVariable("/location.lat")
NestedSequence.createVariable("/location.lon")
NestedSequence.createVariable("/location.elev")
NestedSequence.createSequence("/location.time_series")
NestedSequence.createVariable("/location.time_series.time")
NestedSequence.createVariable("/location.time_series.slp")
NestedSequence.createVariable("/location.time_series.wind")
NestedSequence["/location"].data = IterData(
    [
        (1, 1, 1, [(10, 11, 12), (21, 22, 23)]),
        (2, 4, 4, [(15, 16, 17)]),
        (3, 6, 9, []),
        (4, 8, 16, [(31, 32, 33), (41, 42, 43), (51, 52, 53), (61, 62, 63)]),
    ],
    NestedSequence.location,
)


# A simple array with bytes, strings and shorts. These types require special
# encoding for the DODS response.
SimpleArray = DatasetType("SimpleArray")
SimpleArray.createVariable("byte", data=np.arange(5, dtype=np.ubyte))
SimpleArray.createVariable("string", data=np.array(["one", "two"]))
SimpleArray.createVariable("short", data=np.array(1, dtype="h"))


DODS = os.path.join(os.path.dirname(__file__), "data/rainfall_time_malaysia.cdp.dods")
DAS = os.path.join(os.path.dirname(__file__), "data/rainfall_time_malaysia.cdp.das")
dapper = open_file(DODS, DAS)


# dataset from http://test.opendap.org:8080/dods/dts/D1.asc
D1 = DatasetType("EOSDB.DBO", type="Drifters")
D1.createSequence("/Drifters")
D1.createVariable("/Drifters.instrument_id")
D1.createVariable("/Drifters.location")
D1.createVariable("/Drifters.latitude")
D1.createVariable("/Drifters.longitude")
D1.Drifters.data = np.array(
    np.rec.fromrecords(
        list(
            zip(
                [
                    "This is a data test string (pass {0}).".format(1 + i * 2)
                    for i in range(5)
                ],
                [
                    "This is a data test string (pass {0}).".format(i * 2)
                    for i in range(5)
                ],
                [1000.0, 999.95, 999.80, 999.55, 999.20],
                [999.95, 999.55, 998.75, 997.55, 995.95],
            )
        ),
        names=list(D1.Drifters.keys()),
    )
)


# testing structures
SimpleStructure = DatasetType("SimpleStructure")
SimpleStructure.createStructure(
    name="/types",
    key="value",
    nested=OrderedDict(
        [
            ("string", "bar"),
            ("list", [42, 43]),
            ("array", np.array(1)),
            ("float", 1000.0),
        ]
    ),
)
SimpleStructure.createVariable(name="/types.b", data=np.array(-10, np.byte))
SimpleStructure.createVariable(name="/types.ub", data=np.array(10, np.ubyte))
SimpleStructure.createVariable(name="/types.i32", data=np.array(-10, np.int32))
SimpleStructure.createVariable(name="/types.ui32", data=np.array(10, np.uint32))
SimpleStructure.createVariable(name="/types.i16", data=np.array(-10, np.int16))
SimpleStructure.createVariable(name="/types.ui16", data=np.array(10, np.uint16))
SimpleStructure.createVariable(name="/types.f32", data=np.array(100.0, np.float32))
SimpleStructure.createVariable(name="/types.f64", data=np.array(1000.0, np.float64))
SimpleStructure.createVariable(
    name="/types.s", data=np.array("This is a data test string (pass 0).")
)
SimpleStructure.createVariable(name="/types.u", data=np.array("http://www.dods.org"))
SimpleStructure.createVariable(name="/types.U", data=np.array("test unicode", str))


# test grid
rain = DatasetType("test")
rain["rain"] = GridType("rain")
rain["rain"]["rain"] = BaseType("rain", np.arange(6).reshape(2, 3), dims=("y", "x"))
rain["rain"]["x"] = BaseType("x", np.arange(3), units="degrees_east")
rain["rain"]["y"] = BaseType("y", np.arange(2), units="degrees_north")


# test for ``bounds`` function
bounds = DatasetType("test")
bounds.createSequence("/sequence")
bounds.createVariable("/sequence.lon", axis="X")
bounds.createVariable("/sequence.lat", axis="Y")
bounds.createVariable("/sequence.depth", axis="Z")
bounds.createVariable("/sequence.time", axis="T", units="days since 1970-01-01")
bounds["sequence"]["measurement"] = BaseType("measurement")
bounds.sequence.data = np.array(
    np.rec.fromrecords(
        [
            (100, -10, 0, -1, 42),
            (200, 10, 500, 1, 43),
        ],
        names=list(bounds.sequence.keys()),
    )
)


# test for density
ctd = DatasetType("ctd")
ctd.createSequence("cast")
ctd.createVariable("/cast.temperature")
ctd.createVariable("/cast.salinity")
ctd.createVariable("/cast.pressure")

ctd.cast.data = np.array(
    np.rec.fromrecords(
        [
            (21, 35, 0),
            (15, 35, 100),
        ],
        names=list(ctd.cast.keys()),
    )
)

# a simple sequence, simulating a CTD profile
SimpleSequence = DatasetType(
    "SimpleSequence", description="A simple sequence for testing.", nested={"value": 42}
)
SimpleSequence.createSequence("/cast")
SimpleSequence.createVariable("/cast.id")
SimpleSequence.createVariable("/cast.lon", axis="X")
SimpleSequence.createVariable("/cast.lat", axis="Y")
SimpleSequence.createVariable("/cast.depth", axis="Z")
SimpleSequence.createVariable("/cast.time", axis="T", units="days since 1970-01-01")
SimpleSequence.createVariable("/cast.temperature")
SimpleSequence.createVariable("/cast.salinity")
SimpleSequence.createVariable("/cast.pressure")

SimpleSequence["cast"].data = np.array(
    np.rec.fromrecords(
        [
            ("1", 100, -10, 0, -1, 21, 35, 0),
            ("2", 200, 10, 500, 1, 15, 35, 100),
        ],
        names=list(SimpleSequence["cast"].keys()),
    )
)
# SimpleSequence["cast"].data = IterData([
#     ("1", 100, -10,   0, -1, 21, 35,   0),
#     ("2", 200,  10, 500,  1, 15, 35, 100),
# ], SimpleSequence.cast)

# a simple grid
SimpleGrid = DatasetType("SimpleGrid", description="A simple grid for testing.")
SimpleGrid["SimpleGrid"] = GridType("SimpleGrid")
SimpleGrid["SimpleGrid"]["SimpleGrid"] = BaseType(
    "SimpleGrid", np.arange(6).reshape(2, 3), dims=("y", "x")
)
SimpleGrid["x"] = SimpleGrid["SimpleGrid"]["x"] = BaseType(
    "x", np.arange(3), axis="X", units="degrees_east"
)
SimpleGrid["y"] = SimpleGrid["SimpleGrid"]["y"] = BaseType(
    "y", np.arange(2), axis="Y", units="degrees_north"
)

SimpleGroup = DatasetType(
    "example dataset",
    Description="A simple group for testing.",
    dimensions={"time": 1, "nv": 2},
)
SimpleGroup.createGroup(
    "SimpleGroup",
    dimensions={"Y": 4, "X": 4},
    Description="Test group with numerical data",
)
SimpleGroup.createVariable(
    name="/SimpleGroup/Temperature",
    data=np.arange(10, 26, 1, dtype="f4").reshape(1, 4, 4),
    units="degrees_celsius",
    dims=("/time", "/SimpleGroup/Y", "/SimpleGroup/X"),
    _FillValue=np.inf,
    ValidRange=[-10, 100],
)
SimpleGroup.createVariable(
    name="/SimpleGroup/Salinity",
    data=30 * np.ones(16, dtype="f4").reshape(1, 4, 4),
    units="psu",
    dims=("/time", "/SimpleGroup/Y", "/SimpleGroup/X"),
    _FillValue=np.nan,
    ValidRange=[0.0, 50.0],
)
SimpleGroup.createVariable(
    name="/SimpleGroup/Y", data=np.arange(4, dtype="i2"), dims=("/SimpleGroup/Y",)
)
SimpleGroup.createVariable(
    name="/SimpleGroup/X", data=np.arange(4, dtype="i2"), dims=("/SimpleGroup/X",)
)
SimpleGroup.createVariable(
    name="/time",
    data=np.array(0.5, dtype="f4"),
    dims=("/time",),
    attributes={
        "standard_name": "time",
        "bounds": "time_bnds",
    },
)
SimpleGroup.createVariable(
    name="/time_bnds", data=np.arange(2, dtype="f4"), dims=("/time", "/nv")
)


# a faulty grid
FaultyGrid = DatasetType("FaultyGrid", description="A faulty grid for testing.")
FaultyGrid["FaultyGrid"] = GridType("FaultyGrid")
FaultyGrid["FaultyGrid"]["FaultyGrid"] = BaseType(
    "FaultyGrid", np.arange(6).reshape(2, 3), dims=("y", "x")
)
FaultyGrid["x"] = FaultyGrid["FaultyGrid"]["x"] = BaseType(
    "x", np.arange(3), axis="X", code=1
)
FaultyGrid["y"] = FaultyGrid["FaultyGrid"]["y"] = BaseType(
    "y", np.arange(2), axis="Y", code=np.int32([])
)
