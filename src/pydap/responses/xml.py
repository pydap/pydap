"""
Build a xml object of the dmr object
"""

from collections import OrderedDict
from collections.abc import Iterable, Mapping
from functools import singledispatch
from xml.sax.saxutils import escape

import numpy as np
from lxml import etree

from pydap.lib import NUMPY_TO_DAP4_TYPEMAP

# SBL, on my machine this is all red and angry, and I couldn't find a way to fix,
# it acts like it can't find the model directory and files
from pydap.model import BaseType, DatasetType, GroupType, SequenceType, StructureType

# DAP 4 Namespace URI and a mapping for passing to lxml
DAP4_NS = {"dap":  "http://xml.opendap.org/ns/DAP/4.0#"}

_XML_NS = "http://www.w3.org/XML/1998/namespace"


# =====================================
# API migrated from pydap.responses.dmr
# =====================================


def _xml_attr(value):
    value = escape(str(value), {'"': "&quot;"})
    return value.encode("ascii", "xmlcharrefreplace").decode("ascii")


def _xml_text(value):
    value = escape(str(_normalize_scalar(value)))
    return value.encode("ascii", "xmlcharrefreplace").decode("ascii")


def _dataset_name_attr(value):
    return _xml_attr(str(value).replace("%2E", ".").replace("%2e", "."))


def _dtype_to_dap4(dtype):
    dtype = np.dtype(dtype)
    key = (dtype.kind, dtype.itemsize)
    if dtype.kind in {"S", "U"}:
        key = (dtype.kind, None)
    try:
        return NUMPY_TO_DAP4_TYPEMAP[key]
    except KeyError as exc:
        raise TypeError("Unsupported DAP4 dtype: {dtype}".format(dtype=dtype)) from exc


def _normalize_scalar(value):
    if isinstance(value, np.ndarray) and value.shape == ():
        value = value.item()
    elif isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def _attribute_values(value):
    if isinstance(value, np.ndarray):
        if value.shape == ():
            return [value[()]]
        return list(value.ravel())
    if (
        isinstance(value, Iterable)
        and not isinstance(value, (str, bytes, Mapping))
        and getattr(value, "shape", None) != ()
    ):
        return list(value)
    return [value]


def _scalar_attribute_type(value):
    if isinstance(value, np.generic):
        return _dtype_to_dap4(value.dtype)
    if isinstance(value, np.ndarray):
        return _dtype_to_dap4(value.dtype)
    if isinstance(value, bool):
        return "UInt8"
    if isinstance(value, int):
        return "Int64"
    if isinstance(value, float):
        return "Float64"
    return "String"


def _attribute_type(values):
    types = [_scalar_attribute_type(value) for value in values if value is not None]
    if not types:
        return "String"
    if len(set(types)) == 1:
        return types[0]
    if "String" in types:
        return "String"
    if any(type_.startswith("Float") for type_ in types):
        return "Float64"
    if any(type_.startswith("Int") for type_ in types):
        return "Int64"
    if any(type_.startswith("UInt") for type_ in types):
        return "UInt64"
    return "String"


def _attribute_items(attributes, excluded=()):
    for key, value in attributes.items():
        if key not in excluded:
            yield key, value


def _dimensions(attributes):
    return attributes.get("dimensions", {})


def _container_dimension_name(container, name):
    if isinstance(container, DatasetType):
        return "/" + name
    path = container.attributes.get("path", "/")
    if not path.endswith("/"):
        path += "/"
    return path + container.name + "/" + name


def _next_phony_dimension_name(used_names):
    index = 0
    while True:
        name = "phony_dim_{index}".format(index=index)
        if name not in used_names:
            used_names.add(name)
            return name
        index += 1


def _container_dimension_context(var):
    dimensions = OrderedDict(_dimensions(var.attributes))
    phony_dimensions = {}
    used_names = set(dimensions)

    variables, _ = _children_by_declaration_order(var)
    for child in variables:
        if not isinstance(child, BaseType):
            continue
        shape = tuple(child.shape or ())
        missing_dims = []
        for size in shape[len(child.dims) :]:
            name = _next_phony_dimension_name(used_names)
            dimensions[name] = size
            missing_dims.append(_container_dimension_name(var, name))
        if missing_dims:
            phony_dimensions[id(child)] = tuple(missing_dims)
    return dimensions, phony_dimensions


def _is_group(child):
    return isinstance(child, GroupType)


def _children_by_declaration_order(var):
    children = list(var.children())
    variables = [child for child in children if not _is_group(child)]
    groups = [child for child in children if _is_group(child)]
    return variables, groups


# /////////////////////////////////////////////////////////////////////////////////
# Entry Point
# ////////////////////////////////////////////////////////////////////////////////


def build_dmr_tree(dataset):
    """
    Entry function to build a xml dom tree from a dmr object

    param dataset: a 'pydap.model.DatasetType' object instance
    returns: the root node of the xml dome tree
    """
    if not isinstance(dataset, DatasetType):
        raise TypeError(
            "build_dmr_tree expects a DatasetType but got {}".format(type(dataset))
        )
    return build_dmr_element(dataset)


# ////////////////////////////////////////////////////////////////////////////////////
# SingleDispatch Functions
# //////////////////////////////////////////////////////////////////////////////


@singledispatch
def build_dmr_element(dataset, parent=None, phony_dimensions=()):
    """
    "A runtime function overloading by executing different implementations
    based on the data type of the first argument" (google on singledispatch)
    basically a switch statement for functions
    the different elements that are handled are [DatasetType, GroupType, SequenceType,
    StructureType, and BaseType]
    """
    raise TypeError(
        "unsupported dataset type for dmr tree generation {}".format(type(dataset))
    )


@build_dmr_element.register(DatasetType)
def _dataset_element_factory(dataset, parent=None, phony_dimensions=()):
    """
    the build_dmr_element function for DatasetType objects
    """
    element = _new_root("Dataset")
    element.set("{%s}base" % _XML_NS, "http://localhost:8001")
    element.set("dapVersion", "4.0")
    element.set("dmrVersion", "1.0")
    # name should be unescaped
    element.set("name", _dataset_name_attr(dataset.name)) 

    dimensions, child_phony_dimensions = _container_dimension_context(dataset)
    _build_dimensions(element, dimensions)
    _build_child_variables(element, dataset, child_phony_dimensions)
    _build_attributes(element, dataset.attributes, excluded=("dimensions",))
    _build_child_groups(element, dataset)

    if parent is not None:
        parent.append(element)
    return element


@build_dmr_element.register(GroupType)
def _group_element(dataset, parent=None, phony_dimensions=()):
    """
    the build_dmr_element function for GroupType objects
    """
    element = _new_child(parent, "Group", name=str(dataset.name))

    dimensions, child_phony_dimensions = _container_dimension_context(dataset)
    _build_dimensions(element, dimensions)
    _build_child_variables(element, dataset, child_phony_dimensions)
    _build_attributes(
        element, dataset.attributes, excluded=("dimensions", "path", "Maps")
    )
    _build_child_groups(element, dataset)
    return element


@build_dmr_element.register(SequenceType)
def _sequence_element(dataset, parent=None, phony_dimensions=()):
    """
    the build_dmr_element function for SequenceType objects
    """
    element = _new_child(parent, "Sequence", name=str(dataset.name))
    _build_child_variables(element, dataset)
    for dim in getattr(dataset, "dims", ()):
        _new_child(element, "Dim", name=str(dim))
    return element


@build_dmr_element.register(StructureType)
def _structure_element(var, parent=None, phony_dimensions=()):
    """
    the build_dmr_element function for StructureType objects
    """
    element = _new_child(parent, "Structure", name=str(var.name))
    _build_child_variables(element, var)
    for dim in getattr(var, "dims", ()):
        _new_child(element, "Dim", name=str(dim))
    return element


@build_dmr_element.register(BaseType)
def _basetype_element(dataset, parent=None, phony_dimensions=()):
    """
    the build_dmr_element function for BaseType objects
    """
    vartype = _dtype_to_dap4(dataset.dtype)
    element = _new_child(parent, vartype, name=str(dataset.name))
    _build_variable_dims(element, dataset, phony_dimensions)
    _build_attributes(element, dataset.attributes, excluded=("dims", "Maps", "path"))
    for map_name in dataset.attributes.get("Maps", ()):
        _new_child(element, "Map", name=str(map_name))
    return element


# ///////////////////////////////////////////////////////////////////////////////////
# Helper functions
# ///////////////////////////////////////////////////////////////////////////////////


def _new_root(name):
    """Create the single root element, declaring the DAP4 default namespace."""
    return etree.Element(_qual_name(name), nsmap={None: DAP4_NS["dap"]})


def _qual_name(name):
    """Return ``tag`` qualified with the DAP4 namespace (Clark notation).

    This is required because ``lxml`` does not retroactively infer an
    element's namespace from an ancestor's default ``xmlns`` declaration:
    each element's namespace has to be set explicitly at creation time in
    order for the tree to serialize back out with everything sharing the
    same DAP4 namespace.
    """
    return "{{{ns}}}{name}".format(ns=DAP4_NS["dap"], name=name)


def _build_dimensions(parent, dims):
    """
    Takes the parent node and create a new dimension and populates it with child
    elements.
    """
    for name, size in dims.items():
        _new_child(parent, "Dimension", name=str(name), size=str(size))


def _new_child(parent, daptype, **attr):
    """
    creates a new child node and returns it
    """
    element = etree.SubElement(parent, _qual_name(daptype))
    for key, value in attr.items():
        if value is not None:
            element.set(key, str(value))
    return element


def _build_child_variables(parent, dataset, phony_dimensions=None):
    """
    Retrieves a list of variables and builds them
    """
    if phony_dimensions is None:
        phony_dimensions = {}
    variables, _ = _children_by_declaration_order(dataset)
    for child in variables:
        build_dmr_element(
            child, parent, phony_dimensions=phony_dimensions.get(id(child), ())
        )


def _build_attributes(parent, attributes, excluded=()):
    """
    takes a list of attributes and passes them to _build_attribute for building
    """
    for key, value in _attribute_items(attributes, excluded):
        _build_attribute(parent, key, value)


def _build_attribute(parent, key, value):
    """
    takes a single attribute and builds it as a xml element
    """
    if isinstance(value, dict):
        attr_element = _new_child(parent, "Attribute", name=str(key), type="Container")
        for child_key, child_value in value.items():
            _build_attribute(attr_element, child_key, child_value)
        return

    attr_values = _attribute_values(value)
    attribute_type = _attribute_type(attr_values)
    attr_element = _new_child(parent, "Attribute", name=str(key), type=attribute_type)
    for item in attr_values:
        value_element = _new_child(attr_element, "Value")
        if item is not None:
            _set_value_text(value_element, item)


def _set_value_text(element, value):
    """
    takes a value, normalizes it, and set it as the element value
    """
    value = _normalize_scalar(value)
    if value is not None:
        element.text = str(value)


def _build_child_groups(parent, dataset):
    """
    gets a list of child groups and builds them
    """
    _, groups = _children_by_declaration_order(dataset)
    for child in groups:
        build_dmr_element(child, parent)


def _build_variable_dims(parent, dataset, phony_dimensions=()):
    """
    builds variable dimensions
    """
    for dim in dataset.dims:
        _new_child(parent, "Dim", name=str(dim))
    for dim in phony_dimensions:
        _new_child(parent, "Dim", name=str(dim))


# ////////////////////////////////////////////////////////////////////////////////////
# toString Function
# ////////////////////////////////////////////////////////////////////////////////////


def dmr_tree_to_string(tree, pretty_print=True, xml_declaration=True):
    """Serialize a lxml DMR tree (as returned by :func:`build_dmr_tree`) to text."""
    return etree.tostring(
        tree,
        pretty_print=pretty_print,
        xml_declaration=xml_declaration,
        encoding="ISO-8859-1",
    ).decode("ISO-8859-1")
