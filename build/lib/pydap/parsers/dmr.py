"""A DMR parser."""

import numpy as np
from xml.etree import ElementTree as ET
import pydap.model
import pydap.lib
import re
import copy
import collections

constructors = ('grid', 'sequence', 'structure')
name_regexp = r'[\w%!~"\'\*-]+'
dmr_atomic_types = ('Int8', 'UInt8', 'Byte', 'Char', 'Int16', 'UInt16', 'Int32', 'UInt32',
                    'Int64', 'UInt64', 'Float32', 'Float64')

namespace = {'': "http://xml.opendap.org/ns/DAP/4.0#"}


def dap4_to_numpy_typemap(type_string):
    """
    This function takes a numpy dtype object
    and returns a dtype object that is compatible with
    the DAP2 specification.
    """
    dtype_str = pydap.lib.DAP4_TO_NUMPY_PARSER_TYPEMAP[type_string]
    return np.dtype(dtype_str)


def get_variables(node, prefix=''):
    variables = collections.OrderedDict()
    group_name = node.get('name')
    if group_name is None:
        return variables
    if node.tag != 'Dataset':
        prefix = prefix + '/' + group_name
    for subnode in node:
        if subnode.tag in dmr_atomic_types:
            name = subnode.get('name')
            if prefix != '':
                name = prefix + '/' + name
            variables[name] = {'element': subnode}
        variables.update(get_variables(subnode, prefix))
    return variables


def get_named_dimensions(node, prefix=''):
    dimensions = {}
    group_name = node.get('name')
    if group_name is None:
        return dimensions
    if node.tag != 'Dataset':
        prefix = prefix + '/' + group_name
    for subnode in node:
        if subnode.tag == 'Dimension':
            name = subnode.get('name')
            if prefix != '':
                name = prefix + '/' + name
            dimensions[name] = int(subnode.attrib['size'])
        dimensions.update(get_named_dimensions(subnode, prefix))
    return dimensions


def get_dtype(element):
    dtype = element.tag
    dtype = dap4_to_numpy_typemap(dtype)
    return dtype


def get_attributes(element):
    attributes = {}
    attribute_elements = element.findall('Attribute')
    for attribute_element in attribute_elements:
        name = attribute_element.get('name')
        value = attribute_element.find('Value').text
        attributes[name] = value
    return attributes


def get_dim_names(element):
    n_unnamed = 0
    # Not to be confused with dimensions
    dimension_elements = element.findall('Dim')
    dimensions = []
    for dimension_element in dimension_elements:
        name = dimension_element.get('name')
        if name is None:
            # We might have unnamed dimensions
            return dimensions
        if name.find('/', 1) == -1:
            # If this is a root Dimension, we remove the leading slash
            name = name.replace('/', '')
        dimensions.append(name)
    return dimensions


def get_dim_sizes(element):
    dimension_elements = element.findall('Dim')
    dimension_sizes = ()
    for dimension_element in dimension_elements:
        name = dimension_element.get('name')
        if name is None:
            size = int(dimension_element.get('size'))
            dimension_sizes += (size,)
    return dimension_sizes


def has_map(element):
    maps = element.findall('Map')
    if len(maps) > 0:
        return True
    else:
        return False


def dmr_to_dataset(dmr):
    """Return a dataset object from a DMR representation."""

    # Parse the DMR. First dropping the namespace
    dmr = re.sub(' xmlns="[^"]+"', '', dmr, count=1)
    dom_et = ET.fromstring(dmr)

    variables = get_variables(dom_et)
    named_dimensions = get_named_dimensions(dom_et)

    # Add size entry for dimension variables
    for name, size in named_dimensions.items():
        if name in variables:
            variables[name]['size'] = size

    # Bootstrap variables
    for name, variable in variables.items():
        variable['name'] = name
        variable['attributes'] = get_attributes(variable['element'])
        variable['dtype'] = get_dtype(variable['element'])
        variable['dims'] = get_dim_names(variable['element'])
        variable['has_map'] = has_map(variable['element'])
        variable['shape'] = get_dim_sizes(variable['element'])

    # Add size entry for dimension variables
    for name, size in named_dimensions.items():
        if name not in variables:
            # We might have dimensions that only have a declaration, so we need to add them to the variables
            variables[name] = {'name': name, 'size': size, 'dims': [name],
                               'dtype': 'int', 'has_map': False, 'attributes': {}, 'shape': ()}

    # Add shape element to variables
    for name, variable in variables.items():
        for dim in variable['dims']:
            variable['shape'] += (variables[dim]['size'],)

    # Convert the ordered dictionary to dataset
    dataset_name = dom_et.attrib['name']
    dataset = pydap.model.DatasetType(dataset_name)
    for name, variable in variables.items():
        data = DummyData(dtype=variable['dtype'], shape=variable['shape'])
        array = pydap.model.BaseType(name=variable['name'], data=data, dimensions=variable['dims'])
        if variable['has_map']:
            var = pydap.model.GridType(name=variable['name'])
            var[name] = array
            for dim in variable['dims']:
                var[dim] = copy.copy(dataset[dim])
        else:
            var = array
        var.attributes = variable['attributes']
        dataset[var.name] = var

    return dataset


class DMRParser:
    """A parser for the DMR."""

    def __init__(self, dmr):
        self.dmr = dmr


class DummyData(object):
    def __init__(self, dtype, shape):
        self.dtype = dtype
        self.shape = shape
