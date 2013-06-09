import os

import numpy as np

from pydap.model import *
from pydap.client import open_file


DODS = os.path.join(os.path.dirname(__file__), 'rainfall_time_malaysia.cdp.dods')
DAS = os.path.join(os.path.dirname(__file__), 'rainfall_time_malaysia.cdp.das')
#dapper = open_file(DODS, DAS)


# dataset from http://test.opendap.org:8080/dods/dts/D1.asc
D1 = DatasetType('EOSDB.DBO', type='Drifters')
D1['Drifters'] = SequenceType('Drifters')
D1['Drifters']['instrument_id'] = BaseType('instrument_id')
D1['Drifters']['location'] = BaseType('location')
D1['Drifters']['latitude'] = BaseType('latitude')
D1['Drifters']['longitude'] = BaseType('longitude')
D1.Drifters.data = np.rec.fromrecords(zip(
    [("This is a data test string (pass %d)." % (1+i*2)) for i in range(5)],
    [("This is a data test string (pass %d)." % (i*2)) for i in range(5)],
    [1000.0, 999.95, 999.80, 999.55, 999.20],
    [999.95, 999.55, 998.75, 997.55, 995.95]), names=D1.Drifters.keys())


# testing structures
SimpleStructure = DatasetType('SimpleStructure')
SimpleStructure['types'] = StructureType('types', key="value",
        nested={ 
            "string": "bar", 
            "list": [42, 43], 
            "array": np.array(1),
            "float": 1000.0,
        })
SimpleStructure['types']['b'] = BaseType('b', np.array(0, np.byte))
SimpleStructure['types']['i32'] = BaseType('i32', np.array(1, np.int32))
SimpleStructure['types']['ui32'] = BaseType('ui32', np.array(0, np.uint32))
SimpleStructure['types']['i16'] = BaseType('i16', np.array(0, np.int16))
SimpleStructure['types']['ui16'] = BaseType('ui16', np.array(0, np.uint16))
SimpleStructure['types']['f32'] = BaseType('f32', np.array(0.0, np.float32))
SimpleStructure['types']['f64'] = BaseType('f64', np.array(1000., np.float64))
SimpleStructure['types']['s'] = BaseType('s',
        np.array("This is a data test string (pass 0)."))
SimpleStructure['types']['u'] = BaseType('u', np.array("http://www.dods.org"))


# test grid
rain = DatasetType('test')                                           
rain['rain'] = GridType('rain')                               
rain['rain']['rain'] = BaseType('rain', np.arange(6).reshape(2, 3),
    dimensions=('y', 'x'))
rain['rain']['x'] = BaseType('x', np.arange(3), units='degrees_east')           
rain['rain']['y'] = BaseType('y', np.arange(2), units='degrees_north')


# test for `bounds` function
bounds = DatasetType('test')
bounds['sequence'] = SequenceType('sequence')
bounds['sequence']['lon'] = BaseType('lon', axis='X')
bounds['sequence']['lat'] = BaseType('lat', axis='Y')
bounds['sequence']['depth'] = BaseType('depth', axis='Z')
bounds['sequence']['time'] = BaseType('time', axis='T', 
        units="days since 1970-01-01")
bounds['sequence']['measurement'] = BaseType('measurement')
bounds.sequence.data = np.rec.fromrecords([
    (100, -10, 0, -1, 42),
    (200, 10, 500, 1, 43),
    ], names=bounds.sequence.keys())


# test for density
ctd = DatasetType('ctd')
ctd['cast'] = SequenceType('cast')
ctd['cast']['temperature'] = BaseType('temperature')
ctd['cast']['salinity'] = BaseType('salinity')
ctd['cast']['pressure'] = BaseType('pressure')
ctd.cast.data = np.rec.fromrecords([
    (21, 35, 0),
    (15, 35, 100),
    ], names=ctd.cast.keys())
