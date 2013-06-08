import re

import numpy as np

from pydap.parsers import SimpleParser
from pydap.model import *
from pydap.lib import quote, STRING


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
    'string'  : STRING,  # default is "|S128"
    'url'     : STRING,
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
