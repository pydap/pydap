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


class DMRParser:
    """A parser for the DMR."""
    def __init__(self, dmr):
        self.dmr = dmr


def build_dataset_dmr(dmr):
    """Return a dataset object from a DMR representation."""

    # Parse the DMR.
    doc = minidom.parseString(dmr)

    # Print out the metadata.
    dsizes = {}
    for dim in doc.getElementsByTagName("Dimension"):
        size_string = dim.getAttribute("size")
        dsizes[dim.getAttribute("name")] = int(size_string)

    # Create and fill in the pydap data model.
    name = doc.getElementsByTagName('Dataset')[0].getAttribute('name')
    dataset = DatasetType(name)

    # Handle each variable of atomic type.
    dmr_atomic_types = ('Int8', 'UInt8', 'Byte', 'Char', 'Int16', 'UInt16', 'Int32', 'UInt32',
                        'Int64', 'UInt64', 'Float32', 'Float64')

    for atomic_type in dmr_atomic_types:
        for dmr_var in doc.getElementsByTagName(atomic_type):
            name = dmr_var.getAttribute("name")
            if name in dsizes.keys():
                continue

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
                dim_data = DummyData(parser_dtype, shape=(dsizes[var_dim_name],))
                var[var_dim_name] = BaseType(var_dim_name, dim_data)
            for var_att in dmr_var.getElementsByTagName("Attribute"):
                var.attributes[var_att.getAttribute("name")] = var_att.getElementsByTagName("Value")[0].childNodes[0].nodeValue
            dataset[var.name] = var            

    return dataset


class DummyData(object):
    def __init__(self, dtype, shape):
        self.dtype = dtype
        self.shape = shape
