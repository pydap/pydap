"""A DMR parser."""

import ast
import copy
import re
import warnings
from collections import OrderedDict

# from pathlib import Path
# from typing import Any, Iterable
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
    variables = OrderedDict()
    group_name = (
        pydap.lib._quote(node.get("name"))
        if node.tag in ["Dataset", "Group", "Structure", "Sequence"]
        else None if node.get("name") is not None else None
    )
    if group_name is None:
        return variables
    if node.tag != "Dataset":
        prefix = prefix + "/" + group_name
    for subnode in copy.deepcopy(node):
        if subnode.tag in dmr_atomic_types + ("String",):
            name = subnode.get("name")
            if prefix != "":
                if node.tag == "Group":
                    name = prefix + "/" + name
                elif node.tag in ["Structure", "Sequence"]:
                    name = prefix + "." + name
            _dims = get_dim_names(copy.deepcopy(subnode))
            variables[name] = {
                "name": name,
                "parent": node.tag,
                "dims": _dims,
                "attributes": get_attributes(subnode, {}),
                "dtype": get_dtype(subnode),
                "maps": get_maps(subnode),
                "shape": get_dim_sizes(subnode),
            }
        variables.update(get_variables(subnode, prefix))
    return variables


def get_named_dimensions(node, prefix="", depth=False) -> dict:
    """returns the (non-fq) dimension names to be used to
    define dimensions at the container (root or group)
    level
    """
    _dimensions = OrderedDict()  # order matters
    group_name = node.get("name")
    if group_name is None:
        return _dimensions
    if node.tag != "Dataset":
        prefix = prefix + "/" + group_name
    for subnode in node:
        if subnode.tag == "Dimension":
            name = subnode.get("name")
            if prefix != "":
                name = prefix + "/" + name
            _dimensions[name] = int(subnode.attrib["size"])
        if depth:
            _dimensions.update(get_named_dimensions(subnode, prefix, depth))
    return _dimensions


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
                raise Warning("""
                    Pydap failed to retrieve Attribute: `{}` element during
                    parsing of the `DMR`.""".format(name))
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
    """This is done at the variable level. `Dims` element
    in the xml document.
    """
    _dimensions = [
        (
            el.get("name").replace("/", "")
            if el.get("name") is not None and el.get("name").find("/", 1) == -1
            else el.get("name")
        )
        for el in element.findall("Dim")
    ]
    return tuple([item for item in _dimensions if item is not None])


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


def get_groups(node, prefix="/") -> dict:
    """"""
    groups = node.findall("Group")  # may be seveal elements
    out = {}
    for group in groups:
        fqname = prefix + group.attrib["name"]
        global_dimensions = OrderedDict()
        for name, size in get_named_dimensions(group).items():
            global_dimensions[name.split("/")[-1]] = size
        out.update(
            {
                fqname: {
                    "attributes": get_attributes(group, {}),
                    "Maps": get_maps(group),
                    "dimensions": dict(global_dimensions),
                    "path": prefix,
                }
            }
        )
        subgroups = group.findall("Group")
        if len(subgroups) > 0:
            out.update(get_groups(group, fqname + "/"))
    return out


def dmr_to_dataset(dmr, flat=True, dmrVersion=None):
    """Return a dataset object from a DMR representation. flat: boolean only
    for Structures"""

    # Parse the DMR. First dropping the namespace
    dom_et = copy.deepcopy(DMRParser(dmr, dmrVersion=dmrVersion).node)
    dmr_instance = DMRParser(dmr, dmrVersion=dmrVersion)

    # emtpy dataset
    if dmr_instance.Groups:
        split_by = "/"
    else:
        split_by = None
    if dmr_instance.dmrVersion == "2.0":
        GROUPS_metadata = get_groups(dom_et)
    dataset = dmr_instance.init_dataset()

    variables: OrderedDict[str, dict] = OrderedDict()
    named: dict[str, int] = {}
    variables = get_variables(dom_et)

    # Add size entry for dimension variables
    for name, size in get_named_dimensions(dom_et, depth=True).items():
        if name in variables:
            variables[name]["size"] = size
        else:
            named.update({name: size})

    for name in variables:
        for dim in variables[name]["dims"]:
            if dim in variables:
                variables[name]["shape"] += (variables[dim]["size"],)
            else:
                try:
                    variables[name]["shape"] += (named[dim],)
                except KeyError as e:
                    print(name, variables[name]["dims"])
                    raise e
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
            if len(parts) == len(name.split(split_by)):
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
            "data": data,
            "dims": Dims,
            "dtype": variable["dtype"],
            "shape": variable["shape"],
            "attributes": variable["attributes"],
        }
        if "maps" in variable.keys():
            var_kwargs.update({"Maps": variable["maps"]})
        if "parent" in variable.keys() and variable["parent"] in [
            "Sequence",
            "Structure",
        ]:
            parent_type = variable["parent"]
            if flat:
                # Flat Access
                var_kwargs.update({"name": pydap.lib._quote(name)})
            else:
                parent_name = name.split(".")
                var_kwargs.update({"name": name})
                if len(parent_name) > 2:
                    raise ValueError(
                        f" The variable {name[1:]} contains one or more nested"
                        f"{parent_type}s. This is currently unsupported. Consider"
                        "removing this variable by using a Constraint Expression"
                    )
                if parent_name[0][1:] not in dataset.keys():
                    if parent_type == "Sequence":
                        warnings.warn(
                            f"The remote file contains Sequence `{parent_name[0][1:]}`"
                            ". Sequences in DAP4 are not fully supported and their"
                            " use may lead to unexpected results."
                        )
                        dataset.createSequence(parent_name[0], dims=Dims)
                    else:
                        dataset.createStructure(parent_name[0], dims=Dims)
        else:
            var_kwargs.update({"name": pydap.lib._quote(name)})
            if dmr_instance.dmrVersion == "2.0" and path:
                groups = path.split("/")
                groups_fqn = ["/".join(groups[:N]) for N in range(1, len(groups) + 1)][
                    1:
                ]
                # keep track of existing groups in dataset (fqn)
                ds_groups = list(dataset.groups().items())
                for group in groups_fqn:
                    if group not in ds_groups and group in GROUPS_metadata.keys():
                        dims = GROUPS_metadata[group].pop("dimensions", None)
                        Maps = GROUPS_metadata[group].pop("Maps", None)
                        attributes = GROUPS_metadata[group].pop("attributes", None)
                        dataset.createGroup(
                            name=pydap.lib._quote(group),
                            dimensions=dims,
                            Maps=Maps,
                            attributes=attributes,
                        )
                        GROUPS_metadata.pop(group)
                    ds_groups = list(dataset.groups().items())

        dataset.createVariable(**var_kwargs)

    if dmr_instance.dmrVersion == "2.0":
        # create any missing groups
        recorded = [path + gname[1:] for gname, path in dataset.groups().items()]
        miss = [
            fqn
            for fqn in GROUPS_metadata.keys()
            if pydap.lib._quote(fqn) not in recorded
        ]
        for fqn in miss:
            dims = GROUPS_metadata[fqn].pop("dimensions", None)
            Maps = GROUPS_metadata[fqn].pop("Maps", None)
            attributes = GROUPS_metadata[fqn].pop("attributes", None)
            dataset.createGroup(
                name=pydap.lib._quote(fqn),
                dimensions=dims,
                Maps=Maps,
                attributes=attributes,
            )
        # assign root to each variable
    dataset.assign_dataset_recursive(dataset)
    return dataset


class DMRParser(object):
    """A parser for the DMR."""

    def __init__(self, dmr, dmrVersion=None):
        self.dmr = dmr
        self.dmrVersion = dmrVersion
        self.Groups = None
        _dmr = re.sub(' xmlns="[^"]+"', "", self.dmr, count=1)
        self.node = ET.fromstring(_dmr)
        if len(get_groups(self.node)) > 0:
            # no groups here
            self.Groups = True

        # Hyrax has bumped the dmrVersion from 1.0 to 2.0 to indicate proper
        # deserialization of DAP4 datasets in accordance with the DAP4 spec.
        # Pydap only supports version 1.0 for now, and so this attribute
        # will be used to discern between the two versions.
        if (
            self.dmrVersion is None
            and hasattr(self.node, "attrib")
            and "dmrVersion" in self.node.attrib
        ):
            self.dmrVersion = self.node.attrib["dmrVersion"]

        AttsNames = [subnode.get("name") for subnode in self.node.findall("Attribute")]
        # identify any TDS specific attribute and if so, bump version to 2
        if any(
            map(
                lambda x: x in AttsNames,
                ["_DAP4_Little_Endian", "_dap4.ce"],
            )
        ):
            self.dmrVersion = "2.0"

    def init_dataset(self):
        """creates an empty dataset with a name and attributes"""
        dataset_name = self.node.get("name")
        dataset = pydap.model.DatasetType(dataset_name)
        server_attrs = [
            "DODS_EXTRA",
            "_NCProperties",
            "_dap4.ce",
            "_DAP4_Little_Endian",
            "build_dmrpp_metadata",
        ]
        AttsNames = [subnode.get("name") for subnode in self.node.findall("Attribute")]
        Attrs = {}
        for subnode in self.node:
            if (
                subnode.get("name") in AttsNames
                and subnode.get("name") not in server_attrs
            ):
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

        # get Global dimensions at root level
        global_dimensions = []
        for name, size in get_named_dimensions(self.node).items():
            if len(name.split(split_by)) == 1:
                global_dimensions.append([name, size])

        dataset.dimensions = {k: v for k, v in global_dimensions}
        variables = get_variables(self.node)
        # create Groups via dict
        Groups = get_groups(self.node)
        # check if any var at root level
        root_vars = [
            subnode.tag
            for subnode in self.node
            if subnode.tag in dmr_atomic_types + ("String",)
        ]

        if self.dmrVersion == "1.0" or len(root_vars) == 0:
            if self.dmrVersion == "1.0" or len(variables.keys()) == 0:
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
            else:
                root_groups = [
                    subnode.get("name")
                    for subnode in self.node
                    if subnode.tag == "Group"
                ]
                for ky in root_groups:
                    dims = Groups["/" + ky].pop("dimensions", None)
                    Maps = Groups["/" + ky].pop("Maps", None)
                    attributes = Groups["/" + ky].pop("attributes", None)
                    dataset.createGroup(
                        name=pydap.lib._quote("/" + ky),
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
