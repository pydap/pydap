"""A DMR parser."""

import numpy as np
from xml.etree import ElementTree as ET
import pydap.model
import pydap.lib


constructors = ('grid', 'sequence', 'structure')
name_regexp = r'[\w%!~"\'\*-]+'
dmr_atomic_types = ('Int8', 'UInt8', 'Byte', 'Char', 'Int16', 'UInt16', 'Int32', 'UInt32',
                    'Int64', 'UInt64', 'Float32', 'Float64')

namespace = {'': "http://xml.opendap.org/ns/DAP/4.0#"}


def get_group_variables(element, parent_name=''):
    variables = {}
    group_elements = element.findall('Group', namespace)
    for group_element in group_elements:
        group_name = parent_name + '/' + group_element.get('name')
        group_variables = get_variables(group_element, group_name)
        subgroup_variables = get_group_variables(group_element, group_name)
        variables = {**variables, **group_variables, **subgroup_variables}
    return variables


def get_variables(element, parent_name=''):
    variables = {}
    for atomic_type in dmr_atomic_types:
        for variable in element.findall(atomic_type, namespace):
            name = variable.attrib['name']
            name = pydap.lib.quote(name)
            if parent_name == '':
                # The FQN of root variables does not have leading slash
                fqn = name
            else:
                fqn = parent_name + '/' + name
            variables[fqn] = {'name': fqn, 'element': variable}
    return variables


def get_group_dimensions(element, parent_name=''):
    dimensions = {}
    group_elements = element.findall('Group', namespace)
    for group_element in group_elements:
        group_name = parent_name + '/' + group_element.get('name')
        group_dimensions = get_dimensions(group_element, group_name)
        subgroup_dimensions = get_group_dimensions(group_element, group_name)
        dimensions = {**dimensions, **group_dimensions, **subgroup_dimensions}
    return dimensions


def get_dimensions(element, parent_name=''):
    dimensions = {}
    dimensions_elements = element.findall('Dimension', namespace)
    for dimensions_element in dimensions_elements:
        name = dimensions_element.attrib['name']
        name = pydap.lib.quote(name)
        if parent_name == '':
            # The FQN of root variables does not have leading slash
            fqn = name
        else:
            fqn = parent_name + '/' + name
        size = dimensions_element.attrib['size']
        dimensions[fqn] = {'name': fqn, 'size': int(size)}
    return dimensions


def dap4_to_numpy_typemap(type_string):
    """
    This function takes a numpy dtype object
    and returns a dtype object that is compatible with
    the DAP2 specification.
    """
    dtype_str = pydap.lib.DAP4_TO_NUMPY_PARSER_TYPEMAP[type_string]
    return np.dtype(dtype_str)


def get_dtype(element):
    prefix, separator, dtype = element.tag.partition('}')
    dtype = dap4_to_numpy_typemap(dtype)
    return dtype


def get_attributes(element):
    attributes = {}
    attribute_elements = element.findall('Attribute', namespace)
    for attribute_element in attribute_elements:
        name = attribute_element.get('name')
        value = attribute_element.find('Value', namespace).text
        attributes[name] = value
    return attributes


def get_dims(element):
    # Not to be confused with dimensions
    dimension_elements = element.findall('Dim', namespace)
    dimensions = []
    for dimension_element in dimension_elements:
        name = dimension_element.get('name')
        if name.find('/', 1) == -1:
            # If this is a root Dimension, we remove the leading slash
            name = name.replace('/', '')
        dimensions.append(name)
    return dimensions


def has_map(element):
    maps = element.findall('Map', namespace)
    if len(maps) > 0:
        return True
    else:
        return False


def get_shape(dimensions, variable):
    shape = []
    for dim_name in variable['dims']:
        shape.append(dimensions[dim_name]['size'])
    return shape


def make_grid_var(dataset, variable):
    data = DummyData(dtype=variable['dtype'], shape=variable['shape'])
    var = pydap.model.GridType(name=variable['name'])
    var[variable['name']] = pydap.model.BaseType(name=variable['name'], data=data, dimensions=variable['dims'])
    for dim in variable['dims']:
        var[dim] = dataset[dim]
    return var


def dmr_to_dataset(dmr):
    """Return a dataset object from a DMR representation."""

    # Parse the DMR.
    dom_et = ET.fromstring(dmr)

    group_variables = get_group_variables(dom_et)
    group_dimensions = get_group_dimensions(dom_et)
    root_variables = get_variables(dom_et, '')
    root_dimensions = get_dimensions(dom_et, '')
    dimensions = {**root_dimensions, **group_dimensions}
    variables = {**root_variables, **group_variables}

    dataset = pydap.model.DatasetType('')

    for dimension in dimensions.values():
        dimension_name = dimension['name']
        dimension_variable = variables[dimension_name]['element']

        dimension['element'] = dimension_variable
        dimension['attributes'] = get_attributes(dimension_variable)
        dimension['dtype'] = get_dtype(dimension_variable)

        dim_data = DummyData(dimension['dtype'], shape=(dimension['size'],))
        var = pydap.model.BaseType(dimension_name, dim_data)
        var.attributes = dimension['attributes']
        dataset[var.name] = var

    for variable in variables.values():
        if variable['name'] in dimensions.keys():
            continue

        variable['attributes'] = get_attributes(variable['element'])
        variable['dtype'] = get_dtype(variable['element'])
        variable['dims'] = get_dims(variable['element'])
        variable['shape'] = get_shape(dimensions, variable)

        if has_map(variable['element']):
            var = make_grid_var(dataset, variable)
        else:
            data = DummyData(dtype=variable['dtype'], shape=variable['shape'])
            var = pydap.model.BaseType(name=variable['name'], data=data, dimensions=variable['dims'])
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


if __name__ == '__main__':
    #fname = '/home/griessbaum/Dropbox/UCSB/pydap_cpt/pydap_notebooks/ATL03_20181228015957_13810110_003_01.2var.h5.dmrpp.dmr'
    fname = '/home/griessbaum/Dropbox/UCSB/pydap_cpt/pydap_notebooks/coads_climatology.nc.dmr'
    with open(fname, 'rb') as dmr_file:
        dmr = dmr_file.read()
    ds = dmr_to_dataset(dmr)
    print(ds)
