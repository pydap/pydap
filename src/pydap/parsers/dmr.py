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
    group_name = [
        pydap.lib._quote(node.get("name")) if node.get("name") is not None else None
    ][0]
    if group_name is None:
        return variables
    if node.tag != "Dataset":
        prefix = prefix + "/" + group_name
    for subnode in node:
        if subnode.tag in dmr_atomic_types + ("String",):
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


def get_atomic_attr(element):
    """
    Gets the attribute from an xml.ET element associated with a variable
    in the dataset. Attributes may be defined in various ways on a DMR,
    and must be a type that is atomic within the DAP2 and DAP4 spec:
    see
    https://opendap.github.io/dap4-specification/DAP4.html#_how_dap4_differs_from_dap2

    Ways that an attribute can be defined according to following cases:
    1. <Attribute name="name" type={atomic} value="val"/>
    2. <Attribute name="name" type={atomic}>
            <Value>val</Value>
    3. <Attribute name="name" type={atomic}>
            <Value value="val"/>

    In the general case an attribute may have multiple values, when defined within
    the scope of the attributes, resulting in an attribute that has a list as values
    (e.g. range of values). By convention, the order in which the attributes are
    defined is the way in which these appear on the list.

    Example 1:
        <Attribute name='range' type='int64'>
            <Value>-1</Value>
            <Value>1</Value>
        </Attribute>

    Then, range = [-1, 1].

    Example 2:

        <Attribute name="range" type="int64" value="-1">
            <Value>1</Value>
            <Value value=10/>
        </Attribute>

    Then range = [-1, 1, 10]

    """
    # get name of attribute
    name = element.get("name")
    # Get type, always a string. If numeric, must be turn into numeric type.
    _type = element.get("type")
    Float_types = ["Float32", "float", "Float64"]
    Int_types = ["Int16", "Int32", "Int64", "int", "Int8"]
    uInt_types = ["uInt16", "uInt32", "uInt64", "uint", "uInt8", "Char"]
    # Get values. There may be multiple, and these may be defined in various ways
    # according to the 3 cases above
    value = []
    # Case 1: Inline value definition. May be None.
    if element.get("value") is not None:
        value.append(element.get("value"))
    # Case 2 and 3:
    value += [
        val.text if val.text is not None else val.get("value")
        for val in element.findall("Value")
    ]
    if _type in dmr_atomic_types:
        if _type in Float_types:
            # keep float-type of value
            value = [float(val) if val is not None else val for val in value]
        elif _type in Int_types or _type in uInt_types:
            # keeps integer-type of value
            value = [int(val) if val is not None else val for val in value]
        else:
            try:
                value = [ast.literal_eval(val) for val in value if val is not None]
            except ValueError:
                # leaves value as string
                raise Warning(
                    """
                    Pydap failed to retrieve Attribute: `{}` element during
                    parsing of the `DMR`.""".format(
                        name
                    )
                )
    if len(value) <= 1:
        if value != []:
            value = value[0]
        else:
            value = None
    return name, value


def get_attributes(element, attributes={}):
    attribute_elements = element.findall("Attribute")
    for attribute_element in attribute_elements:
        name, value = get_atomic_attr(attribute_element)
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


def get_groups(node, prefix="/"):
    groups = node.findall("Group")  # may be seveal elements
    out = {}
    for group in groups:
        fqname = prefix + group.attrib["name"]
        named_dimensions = get_named_dimensions(group)
        global_dimensions = []
        for name, size in named_dimensions.items():
            global_dimensions.append([name.split("/")[-1], size])
        out.update(
            {
                fqname: {
                    "attributes": get_attributes(group, {}),
                    "Maps": get_maps(group),
                    "dimensions": {k: v for k, v in global_dimensions},
                    "path": prefix,
                }
            }
        )
        subgroups = group.findall("Group")
        if len(subgroups) > 0:
            out.update(get_groups(group, fqname + "/"))
    return out


def dmr_to_dataset(dmr):
    """Return a dataset object from a DMR representation."""

    # Parse the DMR. First dropping the namespace
    dom_et = DMRParser(dmr).node
    # emtpy dataset
    if DMRParser(dmr).Groups:
        split_by = "/"
    else:
        split_by = None

    dataset = DMRParser(dmr).init_dataset()

    variables = get_variables(dom_et)
    named_dimensions = get_named_dimensions(dom_et)

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
        if len(var_name.split(split_by)) > 1:
            # path-like name - Groups!
            parts = var_name.split(split_by)
            var_name = parts[-1]
            path = ("/").join(parts[:-1])
            variable["attributes"]["path"] = path
        data = DummyData(dtype=variable["dtype"], shape=variable["shape"], path=path)
        # make sure all dimensions have qualifying name
        Dims = []  # dims with fully qualifying names (fqn)
        nqfDims = []  # non-fqn when `dims` and `vars` share same path
        for dim in variable["dims"]:
            parts = dim.split(split_by)
            if len(parts) == 1:
                Dims.append("/" + dim)
            else:  # there is a group
                Dims.append(dim)
            if len(parts) == len(variable["name"].split(split_by)):
                # if path to dim is identical to path to variable
                dim_name = parts[-1]  # only keep the local dim name
                nqfDims.append(dim_name)
            else:
                # dimension name will have a fully qualifying name
                if len(parts) == 1:
                    nqfDims.append("/" + dim)
                else:
                    nqfDims.append(dim)

        # pass along maps
        var_kwargs = {
            "name": pydap.lib._quote(name),
            "data": data,
            "dims": Dims,
            "attributes": variable["attributes"],
        }
        if "maps" in variable.keys():
            var_kwargs.update({"Maps": variable["maps"]})
        if "parent" in variable.keys() and variable["parent"] in [
            "Sequence",
            "Structure",
        ]:
            parts = name.split(split_by)
            parent_name = parts[-2]
            path = ("/").join(parts[:-2])
            if (
                variable["parent"] == "Sequence"
                and parent_name not in dataset[path].keys()
            ):
                dataset.createSequence(("/").join(parts), path=path)
            elif (
                variable["parent"] == "Structure"
                and parent_name not in dataset[path].keys()
            ):
                dataset.createStructure(("/").join(parts), path=path)
        else:
            dataset.createVariable(**var_kwargs)

    return dataset


class DMRParser(object):
    """A parser for the DMR."""

    def __init__(self, dmr):
        self.dmr = dmr
        self.Groups = None

        _dmr = re.sub(' xmlns="[^"]+"', "", self.dmr, count=1)
        self.node = ET.fromstring(_dmr)
        if len(get_groups(self.node)) > 0:
            # no groups here
            self.Groups = True

    def init_dataset(self):
        """creates an empty dataset with a name and attributes"""
        dataset_name = self.node.get("name")
        dataset = pydap.model.DatasetType(dataset_name)
        AttsNames = [subnode.get("name") for subnode in self.node.findall("Attribute")]
        Attrs = {}
        for subnode in self.node:
            if subnode.get("name") in AttsNames:
                if subnode.get("type") not in dmr_atomic_types + (
                    "String",
                    "URI",
                ):
                    # container type
                    Attrs = get_attributes(subnode, Attrs)
                else:
                    name, value = get_atomic_attr(subnode)
                    Attrs[name] = value
        dataset.attributes = Attrs

        # define global dimensions (including named dimensions)
        if self.Groups:
            split_by = "/"
        else:
            split_by = None

        named_dimensions = get_named_dimensions(self.node)

        # get Global dimensions at root level
        global_dimensions = []
        for name, size in named_dimensions.items():
            if len(name.split(split_by)) == 1:
                global_dimensions.append([name, size])

        dataset.dimensions = {k: v for k, v in global_dimensions}

        # create Groups via dict
        Groups = get_groups(self.node)
        for key in Groups:
            dims = Groups[key].pop("dimensions", None)
            Maps = Groups[key].pop("Maps", None)
            attributes = Groups[key].pop("attributes", None)
            dataset.createGroup(
                name=pydap.lib._quote(key),
                dimensions=dims,
                Maps=Maps,
                attributes=attributes,
            )

        return dataset


class DummyData(object):
    def __init__(self, dtype, shape, path):
        self.dtype = dtype
        self.shape = shape
        self.path = path
