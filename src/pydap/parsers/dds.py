"""A DDS parser."""

import re

import numpy as np
from six import text_type

from . import SimpleParser
from ..model import (DatasetType, BaseType,
                     SequenceType, StructureType,
                     GridType)
from ..lib import quote, STRING

typemap = {
    'byte':    np.dtype("B"),
    'int':     np.dtype(">i4"),
    'uint':    np.dtype(">u4"),
    'int16':   np.dtype(">i4"),
    'uint16':  np.dtype(">u4"),
    'int32':   np.dtype(">i4"),
    'uint32':  np.dtype(">u4"),
    'float32': np.dtype(">f4"),
    'float64': np.dtype(">f8"),
    'string':  np.dtype(STRING),  # default is "|S128"
    'url':     np.dtype(STRING),
    }
constructors = ('grid', 'sequence', 'structure')
name_regexp = '[\w%!~"\'\*-]+'


class DDSParser(SimpleParser):

    """A parser for the DDS."""

    def __init__(self, dds, data=None):
        super(DDSParser, self).__init__(dds, re.IGNORECASE)
        self.dds = dds
        self.data = data

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
        token = self.peek('\w+').lower()

        map = {
            'grid':      self.grid,
            'sequence':  self.sequence,
            'structure': self.structure,
        }
        method = map.get(token, self.base)
        return method()

    def base(self):
        """Parse a base variable, returning a ``BaseType``."""
        type = self.consume('\w+')

        dtype = typemap[type.lower()]
        name = quote(self.consume('[^;\[]+'))
        shape, dimensions = self.dimensions()
        self.consume(';')

        data = DummyData(dtype, shape)
        if self.data is not None:
            data, self.data = convert_data_to_array(self.data, shape,
                                                    dtype, name)
        var = BaseType(name, data, dimensions=dimensions)

        return var

    def dimensions(self):
        """Parse variable dimensions, returning tuples of dimensions/names."""
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


def build_dataset(dds, data=None):
    """Return a dataset object from a DDS representation."""
    return DDSParser(dds, data=data).parse()


class DummyData(object):
    def __init__(self, dtype, shape):
        self.dtype = dtype
        self.shape = shape


def convert_data_to_array(data, shape, dtype, id):
    if len(shape) > 0:
        if dtype.char in 'SU':
            data = data[4:]
        else:
            data = data[8:]

    # calculate array size
    size = 1
    if len(shape) > 0:
        size = int(np.prod(shape))

    nitems = dtype.itemsize * size

    if dtype == np.byte:
        return np.fromstring(data[:nitems], 'B').reshape(shape), data[nitems:]
    elif dtype.char in 'SU':
        out = []
        for word in range(size):
            n = np.asscalar(np.fromstring(data[:4], '>I'))  # read itemsize
            data = data[4:]
            out.append(data[:n])
            data = data[n + (-n % 4):]
        return np.array([text_type(x.decode('ascii'))
                         for x in out], 'S').reshape(shape), data
    else:
        try:
            return (np.fromstring(data[:nitems], dtype).reshape(shape),
                    data[nitems:])
        except ValueError as e:
            if str(e) == 'total size of new array must be unchanged':
                # server-side failure.
                # it is expected that the user should be mindful of this:
                raise RuntimeError(
                            ('variable {0} could not be properly '
                             'retrieved. To avoid this '
                             'error consider using open_url(..., '
                             'output_grid=False).').format(quote(id)))
            else:
                raise
