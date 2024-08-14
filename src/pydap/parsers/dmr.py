"""A DMR parser."""

import ast
import collections
import re
from xml.etree import ElementTree as ET

import numpy as np

import pydap.lib
import pydap.model

constructors = ("grid", "sequence", "structure")
name_regexp = r'[\w%!~"\'\*-]+'
dmr_atomic_types = (
    "Int8",
    "UInt8",
    "Byte",
    "Char",
    "Int16",
    "UInt16",
    "Int32",
    "UInt32",
    "Int64",
    "UInt64",
    "Float32",
    "Float64",
)

namespace = {"": "http://xml.opendap.org/ns/DAP/4.0#"}


def dap4_to_numpy_typemap(type_string):
    """
    This function takes a numpy dtype object
    and returns a dtype object that is compatible with
    the DAP2 specification.
    """
    dtype_str = pydap.lib.DAP4_TO_NUMPY_PARSER_TYPEMAP[type_string]
    return np.dtype(dtype_str)


def get_variables(node, prefix="") -> dict:
    variables = collections.OrderedDict()
    group_name = node.get("name")
    if group_name is None:
        return variables
    if node.tag != "Dataset":
        prefix = prefix + "/" + group_name
    for subnode in node:
        if subnode.tag in dmr_atomic_types:
            name = subnode.get("name")
            if prefix != "":
                name = prefix + "/" + name
            variables[name] = {"element": subnode, "parent": node.tag}
        variables.update(get_variables(subnode, prefix))
    return variables


def get_named_dimensions(node, prefix=""):
    dimensions = {}
    group_name = node.get("name")
    if group_name is None:
        return dimensions
    if node.tag != "Dataset":
        prefix = prefix + "/" + group_name
    for subnode in node:
        if subnode.tag == "Dimension":
            name = subnode.get("name")
            if prefix != "":
                name = prefix + "/" + name
            dimensions[name] = int(subnode.attrib["size"])
        dimensions.update(get_named_dimensions(subnode, prefix))
    return dimensions


def get_dtype(element):
    dtype = element.tag
    dtype = dap4_to_numpy_typemap(dtype)
    return dtype


def get_attributes(element, attributes={}):
    attribute_elements = element.findall("Attribute")
    Float_types = ["Float32", "float", "Float64"]
    Int_types = ["Int16", "Int32", "Int64", "int", "Int8"]
    uInt_types = ["uInt16", "uInt32", "uInt64", "uint", "uInt8"]
    for attribute_element in attribute_elements:
        name = attribute_element.get("name")
        value = attribute_element.find("Value").text
        _type = attribute_element.get("type")
        if _type in dmr_atomic_types:
            if _type in Float_types:
                # keep float-type of value
                value = float(value)
            elif _type in Int_types or _type in uInt_types:
                # keeps integer-type of value
                value = int(value)
            else:
                try:
                    value = ast.literal_eval(value)
                except ValueError:
                    # leaves value as string
                    raise Warning(
                        """
                        Pydap could not turn the non-string Attribute: `{}`
                        with value `{}` into a numeric type during parsing
                        of the `DMR`. Parsing as string value instead. If you
                        think this is a bug consider raising a issue. To
                        learn more about DAP's atomic types, go to:
                        https://docs.opendap.org/index.php/
                        DAP4:_Specification_Volume_1#Atomic_Types
                        """.format(
                            name, value
                        )
                    )
        attributes[name] = value
    return attributes


def get_dim_names(element):
    # Not to be confused with dimensions
    dimension_elements = element.findall("Dim")
    dimensions = []
    for dimension_element in dimension_elements:
        name = dimension_element.get("name")
        if name is None:
            # We might have unnamed dimensions
            return dimensions
        if name.find("/", 1) == -1:
            # If this is a root Dimension, we remove the leading slash
            name = name.replace("/", "")
        dimensions.append(name)
    return dimensions


def get_dim_sizes(element):
    dimension_elements = element.findall("Dim")
    dimension_sizes = ()
    for dimension_element in dimension_elements:
        name = dimension_element.get("name")
        if name is None:
            size = int(dimension_element.get("size"))
            dimension_sizes += (size,)
    return dimension_sizes


def get_maps(element):
    maps = element.findall("Map")
    Maps = tuple([maps[i].get("name") for i in range(len(maps))])
    return Maps


def dmr_to_dataset(dmr):
    """Return a dataset object from a DMR representation."""

    # Parse the DMR. First dropping the namespace
    dom_et = DMRParser(dmr).node
    # emtpy dataset
    dataset = DMRParser(dmr).init_dataset()

    variables = get_variables(dom_et)
    named_dimensions = get_named_dimensions(dom_et)

    # get Global dimensions at root level
    global_dimensions = []
    for name, size in named_dimensions.items():
        if len(name.split("/")) == 1:
            global_dimensions.append([name, size])

    dataset.dimensions = tuple(tuple(item) for item in global_dimensions)

    # Add size entry for dimension variables
    for name, size in named_dimensions.items():
        if name in variables:
            variables[name]["size"] = size

    # Bootstrap variables
    for name, variable in variables.items():
        variable["name"] = name
        variable["attributes"] = get_attributes(variable["element"], {})
        variable["dtype"] = get_dtype(variable["element"])
        variable["dims"] = get_dim_names(variable["element"])
        variable["maps"] = get_maps(variable["element"])
        variable["shape"] = get_dim_sizes(variable["element"])

    # Add shape element to variables
    for name, variable in variables.items():
        for dim in variable["dims"]:
            if dim in variables.items():
                variable["shape"] += (variables[dim]["size"],)
            else:
                variable["shape"] += (named_dimensions[dim],)

    for name, variable in variables.items():
        var_name = variable["name"]
        path = None
        if len(var_name.split("/")) > 1:
            # path-like name - Groups!
            parts = var_name.split("/")
            var_name = parts[-1]
            path = ("/").join(parts[:-1])
            # need to do the same with dimensions
            for i in range(len(variable["dims"])):
                dim = variable["dims"][i].split("/")[-1]
                variable["dims"][i] = dim
            variable["attributes"]["path"] = path

        data = DummyData(dtype=variable["dtype"], shape=variable["shape"], path=path)
        array = pydap.model.BaseType(
            name=var_name,
            data=data,
            dimensions=variable["dims"],
        )
        # pass along maps
        if "maps" in variable.keys():
            array.Maps = variable["maps"]
        var = array
        var.attributes = variable["attributes"]
        if "parent" in variable.keys() and variable["parent"] in [
            "Sequence",
            "Structure",
        ]:
            parts = name.split("/")
            parent_name = parts[-2]
            path = ("/").join(parts[:-2])
            if variable["parent"] == "Sequence":
                dapType = pydap.model.SequenceType
            else:
                dapType = pydap.model.StructureType
            if parent_name not in dataset[path].keys():
                dataset[path + parent_name] = dapType(parent_name)
            dataset[("/").join(parts)] = var

        else:
            dataset[name] = var

    return dataset


class DMRParser(object):
    """A parser for the DMR."""

    def __init__(self, dmr):
        # super(DMRParser, self).__init__(dmr, re.IGNORECASE)
        self.dmr = dmr

        _dmr = re.sub(' xmlns="[^"]+"', "", self.dmr, count=1)
        self.node = ET.fromstring(_dmr)

    def init_dataset(self):
        """creates an empty dataset with a name and attributes"""
        dataset_name = self.node.get("name")
        dataset = pydap.model.DatasetType(dataset_name)
        AttsNames = [subnode.get("name") for subnode in self.node.findall("Attribute")]
        Attrs = {}
        for subnode in self.node:
            if subnode.get("name") in AttsNames:
                Attrs = get_attributes(subnode, Attrs)
        dataset.attributes = Attrs
        return dataset


class DummyData(object):
    def __init__(self, dtype, shape, path):
        self.dtype = dtype
        self.shape = shape
        self.path = path
