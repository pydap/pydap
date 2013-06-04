import re

import numpy as np

from pydap.parsers import SimpleParser
from pydap.model import *
from pydap.lib import quote


typemap = {
    'byte'    : 'B',
    'int'     : '>i',
    'uint'    : '>I',
    'int16'   : '>i',
    'uint16'  : '>I',
    'int32'   : '>i',
    'uint32'  : '>I',
    'float32' : '>f',
    'float64' : '>d',
    'string'  : '|S1',
    'url'     : '|S1',
    }
constructors = ('grid', 'sequence', 'structure')
name_regexp = '[\w%!~"\'\*-]+'


class DDSParser(SimpleParser):
    def __init__(self, dds):
        super(DDSParser, self).__init__(dds, re.IGNORECASE)
        self.dds = dds

    def consume(self, regexp):
        token = super(DDSParser, self).consume(regexp)
        self.buffer = self.buffer.lstrip()
        return token

    def parse(self):
        dataset = DatasetType('nameless')

        self.consume('dataset')
        self.consume('{')
        while not self.peek('}'):
            var = self.declaration()
            dataset[var.name] = var
        self.consume('}')

        dataset.name = quote(self.consume('[^;]+'))
        dataset._set_id(dataset.name)
        self.consume(';')

        dataset.descr = dataset.name, [c.descr for c in dataset.children()], ()

        return dataset

    def declaration(self):
        token = self.peek('\w+').lower()

        map = {
               'grid'      : self.grid,
               'sequence'  : self.sequence,
               'structure' : self.structure,
               }
        method = map.get(token, self.base)
        return method()

    def base(self):
        type = self.consume('\w+')

        dtype = typemap[type.lower()]
        name = quote(self.consume('[^;\[]+'))
        shape, dimensions = self.dimensions()
        self.consume(';')

        var = BaseType(name, dimensions=dimensions)
        var.descr = quote(name), dtype, shape

        return var

    def dimensions(self):
        shape = []
        names = []
        while not self.peek(';'):
            self.consume('\[')
            token = self.consume(name_regexp)
            if self.peek('='):
                names.append(token)
                self.consume('=')
                token = self.consume('\d+')
            shape.append(int(token))
            self.consume('\]')
        return tuple(shape), tuple(names)

    def sequence(self):
        sequence = SequenceType('nameless')
        self.consume('sequence')
        self.consume('{')

        while not self.peek('}'):
            var = self.declaration()
            sequence[var.name] = var
        self.consume('}')

        sequence.name = quote(self.consume('[^;]+'))
        self.consume(';')

        sequence.descr = sequence.name, [c.descr for c in sequence.children()], ()

        return sequence

    def structure(self):
        structure = StructureType('nameless')
        self.consume('structure')
        self.consume('{')

        while not self.peek('}'):
            var = self.declaration()
            structure[var.name] = var
        self.consume('}')

        structure.name = quote(self.consume('[^;]+'))
        self.consume(';')

        structure.descr = structure.name, [c.descr for c in structure.children()], ()

        return structure

    def grid(self):
        grid = GridType('nameless')
        self.consume('grid')
        self.consume('{')

        self.consume('array')
        self.consume(':')
        array = self.base()
        grid[array.name] = array

        self.consume('maps')
        self.consume(':')
        while not self.peek('}'):
            var = self.base()
            grid[var.name] = var
        self.consume('}')

        grid.name = quote(self.consume('[^;]+'))
        self.consume(';')

        grid.descr = grid.name, [c.descr for c in grid.children()], ()

        return grid


def build_dataset(dds):
    return DDSParser(dds).parse()


if __name__ == '__main__':
    dds = """Dataset {
    Sequence {
        Float32 lon;
        Float64 time;
        Float32 lat;
        Int32 _id;
        Sequence {
            Float32 NH3-N;
            Float32 SiO3-;
            Float32 PO4-P;
            Float32 NO2-N;
            Float32 NO3-N;
            Float32 depth;
        } profile;
        Structure {
            String CAST;
            String COORD_SYSTEM;
            String NODC-COUNTRYCODE;
            String Conventions;
            String INST_TYPE;
            String DATA_CMNT;
            String DATA_ORIGIN;
            String CREATION_DATE;
            String DATA_SUBTYPE;
            String DATA_TYPE;
            String OCL-STATION-NUM;
            String BOTTLE;
        } attributes;
        Structure {
            Structure {
                Float32 valid_range[2];
            } depth;
        } variable_attributes;
    } location;
    Structure {
        Float32 lon_range[2];
        Float32 lat_range[2];
        Float32 depth_range[2];
        Float64 time_range[2];
    } constrained_ranges;
} 200509KFHC_nutrient;"""

    print build_dataset(dds).location.descr

    import requests
    print build_dataset(requests.get('http://test.opendap.org:8080/dods/dts/test.07.dds').text.encode('utf-8')).types.descr
    print build_dataset(requests.get('http://sfbeams.sfsu.edu:8080/opendap/sfbeams/data_met/real-time/sfb_MET_PUF.dat.dds').text.encode('utf-8'))['MET-REALTIME_CSV'].descr
    print build_dataset(requests.get('http://test.opendap.org:8080/dods/dts/NestedSeq.dds').text.encode('utf-8')).person1.descr
