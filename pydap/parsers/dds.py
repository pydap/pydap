"""A DDS parser."""

import re

import numpy as np

from . import SimpleParser
from ..model import (DatasetType, BaseType,
                     SequenceType, StructureType,
                     GridType)
from ..lib import (quote, LOWER_DAP2_TO_NUMPY_PARSER_TYPEMAP)

constructors = ('grid', 'sequence', 'structure')
name_regexp = r'[\w%!~"\'\*-]+'


def DAP2_parser_typemap(type_string):
    """
    This function takes a numpy dtype object
    and returns a dtype object that is compatible with
    the DAP2 specification.
    """
    dtype_str = LOWER_DAP2_TO_NUMPY_PARSER_TYPEMAP[type_string.lower()]
    return np.dtype(dtype_str)


class DDSParser(SimpleParser):

    """A parser for the DDS."""

    def __init__(self, dds):
        super(DDSParser, self).__init__(dds, re.IGNORECASE)
        self.dds = dds

    def consume(self, regexp):
        """Consume and return a token."""
        token = super(DDSParser, self).consume(regexp)
        self.buffer = self.buffer.lstrip()
        return token

    def parse(self):
        """Parse the DAS, returning a dataset."""
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

        return dataset

    def declaration(self):
        """Parse and return a declaration."""
        token = self.peek(r'\w+').lower()

        map = {
            'grid':      self.grid,
            'sequence':  self.sequence,
            'structure': self.structure,
        }
        method = map.get(token, self.base)
        return method()

    def base(self):
        """Parse a base variable, returning a ``BaseType``."""
        data_type_string = self.consume('\w+')

        parser_dtype = DAP2_parser_typemap(data_type_string)
        name = quote(self.consume('[^;\[]+'))

        shape, dimensions = self.dimensions()
        self.consume(';')

        data = DummyData(parser_dtype, shape)
        var = BaseType(name, data, dimensions=dimensions)

        return var

    def dimensions(self):
        """Parse variable dimensions, returning tuples of dimensions/names."""
        shape = []
        names = []
        while not self.peek(';'):
            self.consume(r'\[')
            token = self.consume(name_regexp)
            if self.peek('='):
                names.append(token)
                self.consume('=')
                token = self.consume(r'\d+')
            shape.append(int(token))
            self.consume(r'\]')
        return tuple(shape), tuple(names)

    def sequence(self):
        """Parse a DAS sequence, returning a ``SequenceType``."""
        sequence = SequenceType('nameless')
        self.consume('sequence')
        self.consume('{')

        while not self.peek('}'):
            var = self.declaration()
            sequence[var.name] = var
        self.consume('}')

        sequence.name = quote(self.consume('[^;]+'))
        self.consume(';')
        return sequence

    def structure(self):
        """Parse a DAP structure, returning a ``StructureType``."""
        structure = StructureType('nameless')
        self.consume('structure')
        self.consume('{')

        while not self.peek('}'):
            var = self.declaration()
            structure[var.name] = var
        self.consume('}')

        structure.name = quote(self.consume('[^;]+'))
        self.consume(';')

        return structure

    def grid(self):
        """Parse a DAP grid, returning a ``GridType``."""
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

        return grid


def build_dataset(dds):
    """Return a dataset object from a DDS representation."""
    return DDSParser(dds).parse()


class DummyData(object):
    def __init__(self, dtype, shape):
        self.dtype = dtype
        self.shape = shape
