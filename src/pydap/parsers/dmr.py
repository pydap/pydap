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

    # Create and fill in the pydap data model.
    name = doc.getElementsByTagName('Dataset')[0].getAttribute('name')
    dataset = DatasetType(name)

    # Handle each variable of atomic type.
    dmr_atomic_types = ('Int8', 'UInt8', 'Byte', 'Char', 'Int16', 'UInt16', 'Int32', 'UInt32',
                        'Int64', 'UInt64', 'Float32', 'Float64')

    # Parse Dimensions
    dsizes = {}
    for dim in doc.getElementsByTagName("Dimension"):
        size = int(dim.getAttribute("size"))
        name = dim.getAttribute("name")
        dsizes[name] = size

    for atomic_type in dmr_atomic_types:
        for dmr_var in doc.getElementsByTagName(atomic_type):
            name = dmr_var.getAttribute("name")
            parser_dtype = DAP4_parser_typemap(atomic_type)
            if name in dsizes.keys():
                dim_data = DummyData(parser_dtype, shape=(dsizes[name],))
                var = BaseType(name, dim_data)
                dataset[var.name] = var

    for atomic_type in dmr_atomic_types:
        for dmr_var in doc.getElementsByTagName(atomic_type):
            name = dmr_var.getAttribute("name")
            parser_dtype = DAP4_parser_typemap(atomic_type)
            if name in dsizes.keys():
                # Skip dimensions
                continue

            dimensions = []
            shape = []
            for var_dim in dmr_var.getElementsByTagName("Dim"):
                var_dim_name = var_dim.getAttribute("name")[var_dim.getAttribute("name").rindex("/") + 1:]
                dimensions.append(var_dim_name)
                shape.append(dsizes[var_dim_name])

            data = DummyData(parser_dtype, shape)
            var = GridType(name)
            var[name] = BaseType(name, data, dimensions=dimensions)
            for var_dim in dmr_var.getElementsByTagName("Dim"):
                var_dim_name = var_dim.getAttribute("name")[var_dim.getAttribute("name").rindex("/") + 1:]
                var[var_dim_name] = dataset[var_dim_name]
            for var_att in dmr_var.getElementsByTagName("Attribute"):
                value = var_att.getElementsByTagName("Value")[0].childNodes[0].nodeValue
                var.attributes[var_att.getAttribute("name")] = value
            dataset[var.name] = var            

    return dataset


class DummyData(object):
    def __init__(self, dtype, shape):
        self.dtype = dtype
        self.shape = shape
