"""A DMR parser."""

import ast
import copy
import re
import warnings
from collections import OrderedDict
from pathlib import Path
from typing import Any, Iterable
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


def dmr_to_dataset(dmr, flat=True):
    """Return a dataset object from a DMR representation."""

    # Parse the DMR. First dropping the namespace
    dom_et = copy.deepcopy(DMRParser(dmr).node)
    # emtpy dataset
    if DMRParser(dmr).Groups:
        split_by = "/"
    else:
        split_by = None

    dataset = DMRParser(dmr).init_dataset()

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
            "name": pydap.lib._quote(name),
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
            # Flat Access
            parent_type = variable["parent"]
            warnings.warn(
                f"The remote dataset contains a variable named `{name[1:]}` inside a"
                f" `{parent_type}`. The access to the variable is flattened and "
                f"escaped. It can accessed unescaped as: {name[1:]}."
            )
        dataset.createVariable(**var_kwargs)
        # assign root to each variable
        dataset.assign_dataset_recursive(dataset)

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

        # get Global dimensions at root level
        global_dimensions = []
        for name, size in get_named_dimensions(self.node).items():
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


class DMRPPParser:
    """
    Parser for the OPeNDAP DMR++ XML format.
    Reads groups, dimensions, coordinates, data variables, encoding, chunk manifests,
    and attributes. Highly modular to allow support for older dmrpp schema versions.
    Includes many utility functions to extract different information such as finding
    all variable tags, splitting hdf5 groups, parsing dimensions, and more.

    OPeNDAP DMR++ homepage: https://opendap.github.io/DMRpp-wiki/DMRpp.html
    """

    # DAP and DMRPP XML namespaces
    _NS = {
        "dap": "http://xml.opendap.org/ns/DAP/4.0#",
        "dmrpp": "http://xml.opendap.org/dap/dmrpp/1.0.0#",
        "xmlns": "http://www.w3.org/XML/1998/namespace",
    }
    # DAP data types to numpy data types
    _DAP_NP_DTYPE = {
        "Byte": "uint8",
        "UByte": "uint8",
        "Int8": "int8",
        "UInt8": "uint8",
        "Int16": "int16",
        "UInt16": "uint16",
        "Int32": "int32",
        "UInt32": "uint32",
        "Int64": "int64",
        "UInt64": "uint64",
        "Url": "object",
        "Float32": "float32",
        "Float64": "float64",
        "String": "object",
    }
    # Default zlib compression value
    _DEFAULT_ZLIB_VALUE = 6
    # Encoding keys that should be removed from attributes and placed in xarray
    # encoding dict
    # _ENCODING_KEYS = {"_FillValue", "missing_value", "scale_factor", "add_offset"}
    root: ET.Element
    data_filepath: str

    def __init__(
        self,
        root: ET.Element,
        data_filepath: str | None = None,
        skip_variables: Iterable[str] | None = None,
    ):
        """
        Initialize the DMRParser with the given DMR++ file contents and source data file
        path.

        Parameters
        ----------
        root
            Root of the xml tree structure of a DMR++ file.
        data_filepath
            The path to the actual data file that will be set in the chunk manifests.
            If None, the data file path is taken from the DMR++ file.
        """
        self.root = root
        self.data_filepath = (
            data_filepath
            if data_filepath is not None
            else self.root.attrib.get("{" + self._NS["xmlns"] + "}base")
        )
        self.skip_variables = skip_variables or ()

    def to_dataset(self):
        """Parses the DMRpp element and translates it to the Pydap dataset model"""
        Groups = [str(item) for item in self._split_groups(self.root).keys()]
        dimensions = {}
        dim_tags = self._find_dimension_tags(self.find_node_fqn(Groups[0]))

        pyds = pydap.model.DatasetType(
            name=self.root.get("name"), dimensions=dimensions
        )

        metadata, attrs = self._parse_dataset(self.find_node_fqn(Groups[0]))
        # order of serialization
        for var in metadata.keys():
            data = DummyData(
                dtype=metadata[var]["data_type"],
                shape=metadata[var]["shape"],
                path=Groups[0],
            )
            pyds.createVariable(
                name=var,
                data=data,
                dims=metadata[var]["fqn_dims"],
                Maps=metadata[var]["Maps"],
                attributes=metadata[var].pop("attributes"),
            )

        for gr in Groups[1:]:
            metadata, attrs = self._parse_dataset(self.find_node_fqn(gr))
            dimensions = {}
            dim_tags = self._find_dimension_tags(self.find_node_fqn(gr))
            for dim in dim_tags:
                dimensions.update(self._parse_dim(dim))

            pyds.createGroup(name=gr, dimensions=dimensions, attributes=attrs)

            for var in metadata.keys():
                data = DummyData(
                    dtype=metadata[var]["data_type"],
                    shape=metadata[var]["shape"],
                    path=gr,
                )
                pyds.createVariable(
                    name=gr + "/" + var,
                    data=data,
                    dims=metadata[var]["fqn_dims"],
                    Maps=metadata[var]["Maps"],
                    attributes=metadata[var].pop("attributes"),
                )
        return pyds

    def parse_dataset(
        self,
        group: str | None = None,
    ):
        """
        Parses the given file and creates a ManifestStore.

        Parameters
        ----------
        group
            The group to parse. Ignored if no groups are present, and the entire
            dataset is parsed. If `None` or "/", and groups are present, the first group
            is parsed.  If not `None` or "/", and no groups are present, a UserWarning
            is issued indicating that the group will be ignored.

        Returns
        -------
        ManifestStore

        Examples
        --------
        Open a sample DMR++ file and parse the dataset
        """
        group = group or "/"
        ngroups = len(self.root.findall("dap:Group", self._NS))

        if ngroups == 0 and group != "/":
            warnings.warn(
                f"No groups in DMR++ file {self.data_filepath!r}; "
                f"ignoring group parameter {group!r}"
            )

        group_path = Path("/") if ngroups == 0 else Path("/") / group.removeprefix("/")
        dataset_element = self._split_groups(self.root).get(group_path)

        if dataset_element is None:
            raise ValueError(
                f"Group {group_path} not found in DMR++ file {self.data_filepath!r}"
            )

        return self._parse_dataset(dataset_element)

    def find_node_fqn(self, fqn: str) -> ET.Element:
        """
        Find the element in the root element by converting the fully qualified name to
        an xpath query.

        E.g. fqn = "/a/b" --> root.find("./*[@name='a']/*[@name='b']")

        See more about OPeNDAP fully qualified names (FQN) here:
        https://docs.opendap.org/index.php/DAP4:_Specification_Volume_1#Fully_Qualified_Names

        Parameters
        ----------
        fqn
            The fully qualified name of an element. For example, "/a/b".

        Returns
        -------
        ET.Element
            The matching node found within the root element.

        Raises
        ------
        ValueError
            If the fully qualified name is not found in the root element.
        """
        if fqn == "/":
            return self.root

        elements = fqn.strip("/").split("/")  # /a/b/ --> ['a', 'b']
        xpath_segments = [f"*[@name='{element}']" for element in elements]
        xpath_query = "/".join([".", *xpath_segments])  # "./[*[@name='a']/*[@name='b']"

        if (element := self.root.find(xpath_query, self._NS)) is None:
            raise ValueError(f"Path {fqn} not found in provided root")

        return element

    def _split_groups(self, root: ET.Element) -> dict[Path, ET.Element]:
        """
        Split the input <Dataset> element into several <Dataset> ET.Elements by <Group>
        name.
        E.g. {"/": <Dataset>, "left": <Dataset>, "right": <Dataset>}

        Parameters
        ----------
        root : ET.Element
            The root element of the DMR file.

        Returns
        -------
        dict[Path, ET.Element]
        """
        all_groups: dict[Path, ET.Element] = {}
        dataset_tags = [
            d for d in root if d.tag != "{" + self._NS["dap"] + "}" + "Group"
        ]
        if len(dataset_tags) > 0:
            all_groups[Path("/")] = ET.Element(root.tag, root.attrib)
            all_groups[Path("/")].extend(dataset_tags)
        all_groups.update(self._split_groups_recursive(root, Path("/")))
        return all_groups

    def _split_groups_recursive(
        self, root: ET.Element, current_path=Path("")
    ) -> dict[Path, ET.Element]:
        group_dict: dict[Path, ET.Element] = {}
        for g in root.iterfind("dap:Group", self._NS):
            new_path = current_path / Path(g.attrib["name"])
            dataset_tags = [
                d for d in g if d.tag != "{" + self._NS["dap"] + "}" + "Group"
            ]
            group_dict[new_path] = ET.Element(g.tag, g.attrib)
            group_dict[new_path].extend(dataset_tags)
            group_dict.update(self._split_groups_recursive(g, new_path))
        return group_dict

    def _parse_dataset(
        self,
        root: ET.Element,
    ):
        """
        Parse the dataset using the root element of the DMR++ file.

        Parameters
        ----------
        root : ET.Element
            The root element of the DMR++ file.

        Returns
        -------
        ManifestGroup
        """

        manifest_dict: dict[str, Any] = {}
        for var_tag in self._find_var_tags(root):
            if var_tag.attrib["name"] not in self.skip_variables:
                try:
                    variable = self._parse_variable(var_tag)
                    manifest_dict[var_tag.attrib["name"]] = variable
                except (UnboundLocalError, ValueError):
                    name = var_tag.attrib["name"]
                    warnings.warn(
                        f"This DMRpp contains the variable {name} that could not"
                        " be parsed. Consider adding it to the list  of skipped "
                        "variables, or opening an issue to help resolve this"
                    )

        # Attributes
        attrs: dict[str, str] = {}
        # Look for an attribute tag called "HDF5_GLOBAL" and unpack it
        hdf5_global_attrs = root.find("dap:Attribute[@name='HDF5_GLOBAL']", self._NS)
        if hdf5_global_attrs is not None:
            # Remove the container attribute and add its children to the root dataset
            root.remove(hdf5_global_attrs)
            root.extend(hdf5_global_attrs)
        for attr_tag in root.iterfind("dap:Attribute", self._NS):
            attrs.update(self._parse_attribute(attr_tag))

        return manifest_dict, attrs

    def _find_var_tags(self, root: ET.Element) -> list[ET.Element]:
        """
        Find all variable tags in the DMR++ file. Also known as array tags.
        Tags are labeled with the DAP data type. E.g. <Float32>, <Int16>, <String>

        Parameters
        ----------
        root : ET.Element
            The root element of the DMR++ file.

        Returns
        -------
        list[ET.Element]
        """
        vars_tags: list[ET.Element] = []
        for dap_dtype in self._DAP_NP_DTYPE:
            vars_tags += root.findall(f"dap:{dap_dtype}", self._NS)
        return vars_tags

    def _parse_dim(self, root: ET.Element) -> dict[str, int]:
        """
        Parse single <Dim> or <Dimension> tag

        If the tag has no name attribute, it is a phony dimension.
        E.g. <Dim size="300"/> --> {"phony_dim": 300}
        If the tag has both name and size attributes, it is a regular dimension.
        E.g. <Dim name="lat" size="1447"/> --> {"lat": 1447}

        Parameters
        ----------
        root : ET.Element
            The root element Dim/Dimension tag

        Returns
        -------
        dict
            E.g. {"time": 1, "lat": 1447, "lon": 2895}, {"phony_dim": 300},
                 {"time": None, "lat": None, "lon": None}
        """
        if "name" not in root.attrib and "size" in root.attrib:
            return {"phony_dim": int(root.attrib["size"])}
        if "name" in root.attrib and "size" in root.attrib:
            return {Path(root.attrib["name"]).name: int(root.attrib["size"])}
        raise ValueError("Not enough information to parse Dim/Dimension tag")

    def _find_dimension_tags(self, root: ET.Element) -> list[ET.Element]:
        """
        Find the all tags with dimension information.

        First attempts to find Dimension tags, then falls back to Dim tags.
        If Dim tags are found, the fully qualified name is used to find the
        corresponding Dimension tag.

        Parameters
        ----------
        root : ET.Element
            An ElementTree Element from a DMR++ file.

        Returns
        -------
        list[ET.Element]
        """
        dimension_tags = root.findall("dap:Dimension", self._NS)
        if not dimension_tags:
            # Dim tags contain a fully qualified name that references a Dimension tag
            #  elsewhere in the DMR++
            dim_tags = root.findall("dap:Dim", self._NS)
            for d in dim_tags:
                dimension_tag = self.find_node_fqn(d.attrib["name"])
                if dimension_tag is not None:
                    dimension_tags.append(dimension_tag)
        return dimension_tags

    def _find_dim_tags(self, root: ET.Element) -> list[ET.Element]:
        """
        Find the all Dim tags with fully qualifying names.

        Parameters
        ----------
        root : ET.Element
            An ElementTree Element from a DMR++ file.

        Returns
        -------
        list[ET.Element]
        """
        dimension_tags = root.findall("dap:Dimension", self._NS)
        if not dimension_tags:
            # Dim tags contain a fully qualified name that references a Dimension tag
            #  elsewhere in the DMR++
            dim_tags = root.findall("dap:Dim", self._NS)
            for d in dim_tags:
                dimension_tag = self.find_node_fqn(d.attrib["name"])
                if dimension_tag is not None:
                    dimension_tags.append(dimension_tag)
        return dimension_tags

    def _parse_variable(self, var_tag: ET.Element):
        """
        Parse a variable from a DMR++ tag.

        Parameters
        ----------
        var_tag : ET.Element
            An ElementTree Element representing a variable in the DMR++ file. Will have
            DAP dtype as tag. E.g. <Float32>

        Returns
        -------
        ManifestArray
        """

        # Dimension info
        dims: dict[str, int] = {}
        dimension_tags = self._find_dimension_tags(var_tag)
        for dim in dimension_tags:
            dims.update(self._parse_dim(dim))
        # convert DAP dtype to numpy dtype
        dtype = np.dtype(
            self._DAP_NP_DTYPE[var_tag.tag.removeprefix("{" + self._NS["dap"] + "}")]
        )
        # Chunks and Filters
        shape: tuple[int, ...] = tuple(dims.values())
        chunks_shape = shape
        chunks_tag = var_tag.find("dmrpp:chunks", self._NS)
        array_fill_value = np.array(0).astype(dtype)[()]
        if chunks_tag is not None:
            # Chunks
            chunk_dim_text = chunks_tag.findtext(
                "dmrpp:chunkDimensionSizes", namespaces=self._NS
            )
            if chunk_dim_text is not None:
                # 1 1447 2895 -> (1, 1447, 2895)
                chunks_shape = tuple(map(int, chunk_dim_text.split()))
            else:
                chunks_shape = shape
            if "fillValue" in chunks_tag.attrib:
                fillValue_attrib = chunks_tag.attrib["fillValue"]
                array_fill_value = np.array(fillValue_attrib).astype(dtype)[()]
            if chunks_shape:
                chunkmanifest = self._parse_chunks(chunks_tag, chunks_shape)
            else:
                chunkmanifest = {"entries": {}, "shape": array_fill_value.shape}
            # Filters
            codecs = self._parse_filters(chunks_tag, dtype)

        # Attributes
        attrs: dict[str, Any] = {}
        for attr_tag in var_tag.iterfind("dap:Attribute", self._NS):
            attrs.update(self._parse_attribute(attr_tag))
        # if "_FillValue" in attrs:
        # encoded_cf_fill_value = encode_cf_fill_value(attrs["_FillValue"], dtype)
        # attrs["_FillValue"] = encoded_cf_fill_value

        metadata: dict[str, Any] = {}
        # creates array v3 in virtualizarr
        metadata.update(
            shape=shape,
            data_type=dtype,
            chunk_shape=chunks_shape,
            codecs=codecs,
            dimension_names=dims,
            fqn_dims=[dim.get("name") for dim in var_tag.findall("dap:Dim", self._NS)],
            Maps=[map.get("name") for map in var_tag.findall("dap:Map", self._NS)],
            attributes=attrs,
            fill_value=array_fill_value,
            chunkmanifest=chunkmanifest,
        )
        return metadata

    def _parse_attribute(self, attr_tag: ET.Element) -> dict[str, Any]:
        """
        Parse an attribute from a DMR++ attr tag. Converts the attribute value to a
        native python type.
        Raises an exception if nested attributes are passed. Container attributes must
        be unwrapped in the parent function.

        Parameters
        ----------
        attr_tag : ET.Element
            An ElementTree Element with an <Attr> tag.

        Returns
        -------
        dict
        """
        attr: dict[str, Any] = {}
        values = []
        if "type" in attr_tag.attrib and attr_tag.attrib["type"] == "Container":
            # DMR++ build information that is not part of the dataset
            if attr_tag.attrib["name"] == "build_dmrpp_metadata":
                return {}
            else:
                container_attr = attr_tag.attrib["name"]
                warnings.warn(
                    "This DMRpp contains a nested attribute "
                    f"{container_attr}. Nested attributes cannot "
                    "be assigned to a variable or dataset and will be dropped"
                )
                return {}
        dtype = np.dtype(self._DAP_NP_DTYPE[attr_tag.attrib["type"]])
        # if multiple Value tags are present, store as "key": "[v1, v2, ...]"
        for value_tag in attr_tag:
            # cast attribute to native python type using dmr provided dtype
            val = (
                dtype.type(value_tag.text).item()
                if dtype != np.object_
                else value_tag.text
            )
            # "*" may represent nan values in DMR++
            if val == "*":
                val = np.nan
            values.append(val)
        attr[attr_tag.attrib["name"]] = values[0] if len(values) == 1 else values
        return attr

    def _parse_filters(
        self, chunks_tag: ET.Element, dtype: np.dtype
    ) -> list[dict] | None:
        """
        Parse filters from a DMR++ chunks tag.

        Parameters
        ----------
        chunks_tag : ET.Element
            An ElementTree Element with a <chunks> tag.

        dtype : np.dtype
            The numpy dtype of the variable.

        Returns
        -------
        list[dict] | None
            E.g. [{"id": "shuffle", "elementsize": 4}, {"id": "zlib", "level": 4}]
        """
        if "compressionType" in chunks_tag.attrib:
            filters: list[dict] = []
            # shuffle deflate --> ["shuffle", "deflate"]
            compression_types = chunks_tag.attrib["compressionType"].split(" ")
            for c in compression_types:
                if c == "shuffle":
                    filters.append(
                        {
                            "name": "numcodecs.shuffle",
                            "configuration": {"elementsize": dtype.itemsize},
                        }
                    )
                elif c == "deflate":
                    filters.append(
                        {
                            "name": "numcodecs.zlib",
                            "configuration": {
                                "level": int(
                                    chunks_tag.attrib.get(
                                        "deflateLevel", self._DEFAULT_ZLIB_VALUE
                                    )
                                ),
                            },
                        }
                    )
            return filters
        return None

    def _parse_chunks(
        self, chunks_tag: ET.Element, chunks_shape: tuple[int, ...]
    ) -> dict[str, object]:
        """
        Parse the chunk manifest from a DMR++ chunks tag.

        Parameters
        ----------
        chunks_tag : ET.Element
            An ElementTree Element with a <chunks> tag.

        chunks_shape : tuple
            Chunk sizes for each dimension. E.g. (1, 1447, 2895)

        Returns
        -------
        dict
        """
        chunkmanifest: dict[str, object] = {}
        default_num: list[int] = (
            [0 for i in range(len(chunks_shape))] if chunks_shape else [0]
        )
        chunk_key_template = ".".join(["{}" for i in range(len(default_num))])
        for chunk_tag in chunks_tag.iterfind("dmrpp:chunk", self._NS):
            chunk_num = default_num
            if "chunkPositionInArray" in chunk_tag.attrib:
                # "[0,1023,10235]" -> ["0","1023","10235"]
                chunk_pos = chunk_tag.attrib["chunkPositionInArray"][1:-1].split(",")
                # [0,1023,10235] // [1, 1023, 2047] -> [0,1,5]
                chunk_num = [
                    int(chunk_pos[i]) // chunks_shape[i]
                    for i in range(len(chunks_shape))
                ]
            # [0,1,5] -> "0.1.5"
            chunk_key = chunk_key_template.format(*chunk_num)
            chunkmanifest[chunk_key] = {
                "path": self.data_filepath,
                "offset": int(chunk_tag.attrib["offset"]),
                "length": int(chunk_tag.attrib["nBytes"]),
            }
        return chunkmanifest


class DummyData(object):
    def __init__(self, dtype, shape, path):
        self.dtype = dtype
        self.shape = shape
        self.path = path
