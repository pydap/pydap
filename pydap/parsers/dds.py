import re
from urllib import unquote

from pydap.parsers import SimpleParser
from pydap.model import *

atomic_types = ('byte', 'int', 'uint', 'int16', 'uint16', 'int32', 
        'uint32', 'float32', 'float64', 'string', 'url')
constructors = ('grid', 'sequence', 'structure')

name_regexp = '[' + '\w%!~"\'\*-' + ']+'  # regular expression for name

class DDSParser(SimpleParser):
    def __init__(self, dds):
        SimpleParser.__init__(self, dds, re.IGNORECASE)
        self.dds = dds

    def consume(self, regexp):
        token = SimpleParser.consume(self, regexp)
        self.buffer = self.buffer.lstrip()
        return token

    def _dataset(self):
        dataset = DatasetType()

        self.consume('dataset')
        self.consume('{')
        while self.peek('\w+').lower() in atomic_types + constructors:
            var = self._declaration()
            dataset[var.name] = var
        self.consume('}')

        dataset.name = unquote(self.consume('[^;]+'))
        dataset._set_id()
        self.consume(';')

        return dataset

    parse = _dataset

    def _declaration(self):
        token = self.peek('\w+')

        map = {'grid': self._grid,
               'sequence': self._sequence,
               'structure': self._structure}
        method = map.get(token.lower(), self._base_declaration)

        return method()

    def _base_declaration(self):
        type_ = self.consume('\w+')
        type_ = typemap[type_.lower()]
        name = unquote(self.consume('[^;\[]+'))

        shape, dimensions = self._dimensions()
        self.consume(';')

        var = BaseType(name=name, shape=shape,
                dimensions=dimensions, type=type_)
        return var

    def _dimensions(self):
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

    def _sequence(self):
        sequence = SequenceType()
        self.consume('sequence')
        self.consume('{')

        while not self.peek('}'):
            var = self._declaration()
            sequence[var.name] = var
        self.consume('}')

        sequence.name = unquote(self.consume('[^;]+'))
        self.consume(';')
        return sequence

    def _structure(self):
        structure = StructureType()
        self.consume('structure')
        self.consume('{')

        while not self.peek('}'):
            var = self._declaration()
            structure[var.name] = var
        self.consume('}')

        structure.name = unquote(self.consume('[^;]+'))
        self.consume(';')
        return structure

    def _grid(self):
        grid = GridType()
        self.consume('grid')
        self.consume('{')

        self.consume('array')
        self.consume(':')
        array = self._base_declaration()
        grid[array.name] = array

        self.consume('maps')
        self.consume(':')
        while not self.peek('}'):
            var = self._base_declaration()
            grid[var.name] = var
        self.consume('}')

        grid.name = unquote(self.consume('[^;]+'))
        self.consume(';')
        return grid
