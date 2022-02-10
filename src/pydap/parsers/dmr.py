"""A DMR parser."""

import re

import numpy as np

from xml.dom import minidom

from ..model import (DatasetType, BaseType,
                     SequenceType, StructureType,
                     GridType)
from ..lib import (quote, DAP4_TO_NUMPY_PARSER_TYPEMAP)

constructors = ('grid', 'sequence', 'structure')
name_regexp = r'[\w%!~"\'\*-]+'


def DAP4_parser_typemap(type_string):
    """
    This function takes a numpy dtype object
    and returns a dtype object that is compatible with
    the DAP2 specification.
    """
    dtype_str = DAP4_TO_NUMPY_PARSER_TYPEMAP[type_string]
    return np.dtype(dtype_str)

class DMRParser():

    """A parser for the DMR."""

    def __init__(self, dmr):
        self.dmr = dmr

    # def consume(self, regexp):
    #     """Consume and return a token."""
    #     token = super(DMRParser, self).consume(regexp)
    #     self.buffer = self.buffer.lstrip()
    #     return token

    # def parse(self):
    #     """Parse the DAS, returning a dataset."""
    #     dataset = DatasetType('nameless')

    #     self.consume('dataset')
    #     self.consume('{')
    #     while not self.peek('}'):
    #         var = self.declaration()
    #         dataset[var.name] = var
    #     self.consume('}')

    #     dataset.name = quote(self.consume('[^;]+'))
    #     dataset._set_id(dataset.name)
    #     self.consume(';')

    #     return dataset

    # def declaration(self):
    #     """Parse and return a declaration."""
    #     token = self.peek(r'\w+').lower()

    #     map = {
    #         'grid':      self.grid,
    #         'sequence':  self.sequence,
    #         'structure': self.structure,
    #     }
    #     method = map.get(token, self.base)
    #     return method()

    # def base(self):
    #     """Parse a base variable, returning a ``BaseType``."""
    #     data_type_string = self.consume(r'\w+')

    #     parser_dtype = DAP2_parser_typemap(data_type_string)
    #     name = quote(self.consume(r'[^;\[]+'))

    #     shape, dimensions = self.dimensions()
    #     self.consume(r';')

    #     data = DummyData(parser_dtype, shape)
    #     var = BaseType(name, data, dimensions=dimensions)

    #     return var

    # def dimensions(self):
    #     """Parse variable dimensions, returning tuples of dimensions/names."""
    #     shape = []
    #     names = []
    #     while not self.peek(';'):
    #         self.consume(r'\[')
    #         token = self.consume(name_regexp)
    #         if self.peek('='):
    #             names.append(token)
    #             self.consume('=')
    #             token = self.consume(r'\d+')
    #         shape.append(int(token))
    #         self.consume(r'\]')
    #     return tuple(shape), tuple(names)

    # def sequence(self):
    #     """Parse a DAS sequence, returning a ``SequenceType``."""
    #     sequence = SequenceType('nameless')
    #     self.consume('sequence')
    #     self.consume('{')

    #     while not self.peek('}'):
    #         var = self.declaration()
    #         sequence[var.name] = var
    #     self.consume('}')

    #     sequence.name = quote(self.consume('[^;]+'))
    #     self.consume(';')
    #     return sequence

    # def structure(self):
    #     """Parse a DAP structure, returning a ``StructureType``."""
    #     structure = StructureType('nameless')
    #     self.consume('structure')
    #     self.consume('{')

    #     while not self.peek('}'):
    #         var = self.declaration()
    #         structure[var.name] = var
    #     self.consume('}')

    #     structure.name = quote(self.consume('[^;]+'))
    #     self.consume(';')

    #     return structure

    # def grid(self):
    #     """Parse a DAP grid, returning a ``GridType``."""
    #     grid = GridType('nameless')
    #     self.consume('grid')
    #     self.consume('{')

    #     self.consume('array')
    #     self.consume(':')
    #     array = self.base()
    #     grid[array.name] = array

    #     self.consume('maps')
    #     self.consume(':')
    #     while not self.peek('}'):
    #         var = self.base()
    #         grid[var.name] = var
    #     self.consume('}')

    #     grid.name = quote(self.consume('[^;]+'))
    #     self.consume(';')

    #     return grid


def build_dataset_dmr(dmr):
    """Return a dataset object from a DMR representation."""

    # Parse the DMR.
#    print(dmr)
    doc = minidom.parseString(dmr)
#    import pdb; pdb.set_trace()

    # Print out the metadata.
    dsizes = {}
    for dim in doc.getElementsByTagName("Dimension"):
        print("Dimension " + dim.getAttribute("name") + " size " + dim.getAttribute("size"))
        dsizes[dim.getAttribute("name")] = dim.getAttribute("size")
    for att in doc.getElementsByTagName("Attribute"):        
        print("\tAtt name " + att.getAttribute("name") + " type " + att.getAttribute("type"))
    for float64 in doc.getElementsByTagName("Float64"):
        print("Float64 var name " + float64.getAttribute("name"))
        for var_dim in float64.getElementsByTagName("Dim"):
            print("\tDim name " + var_dim.getAttribute("name") + " size " + var_dim.getAttribute("size"))
            for var_att in float64.getElementsByTagName("Attribute"):
                print("\tAtt name " + var_att.getAttribute("name") + " type " + var_att.getAttribute("type"))
                print("\tAtt value " + var_att.getElementsByTagName("Value")[0].childNodes[0].nodeValue)

    # Create and fill in the pydap data model.
    dataset = DatasetType('nameless')

    # Handle each variable of atomic type.
    dmr_atomic_types = ('Int8', 'UInt8', 'Byte', 'Char', 'Int16', 'UInt16', 'Int32', 'UInt32',
                        'Int64', 'UInt64', 'Float32', 'Float64')
    for atomic_type in dmr_atomic_types:
        for dmr_var in doc.getElementsByTagName(atomic_type):
            print("Handling var " + dmr_var.getAttribute("name"))
            grid = GridType('nameless')
            name = dmr_var.getAttribute("name")
            dimensions = []
            shape = []
            for var_dim in dmr_var.getElementsByTagName("Dim"):
                var_dim_name = var_dim.getAttribute("name")[var_dim.getAttribute("name").rindex("/") + 1:]
                dimensions.append(var_dim_name)
                shape.append(dsizes[var_dim_name])
            parser_dtype = DAP4_parser_typemap(atomic_type)
            data = DummyData(parser_dtype, shape)
            var = GridType(name)
            var[name] = BaseType(name, data, dimensions=dimensions)
            for var_dim in dmr_var.getElementsByTagName("Dim"):            
                var_dim_name = var_dim.getAttribute("name")[var_dim.getAttribute("name").rindex("/") + 1:]
                var[var_dim_name] = BaseType(var_dim_name, data)
            for var_att in dmr_var.getElementsByTagName("Attribute"):
                var.attributes[var_att.getAttribute("name")] = var_att.getElementsByTagName("Value")[0].childNodes[0].nodeValue
            dataset[var.name] = var            

#    ints = doc.getElementsByTagName("Int32")
#    var = BaseType(ints[0].getAttribute("name"))
#    dataset[var.name] = var

    return dataset


class DummyData(object):
    def __init__(self, dtype, shape):
        self.dtype = dtype
        self.shape = shape
