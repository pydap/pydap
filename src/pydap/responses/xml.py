"""
    Build a xml object of the dmr object
"""

from lxml import etree
from functools import singledispatch

# SBL, on my machine this is all red and angry, and I couldn't find a way to fix, it acts like it can't find the model
#       directory and files
from pydap.model import BaseType, DatasetType, GroupType, SequenceType, StructureType
from pydap.responses.dmr import (
    _attribute_items,
    _attribute_type,
    _attribute_values,
    _children_by_declaration_order,
    _container_dimension_context,
    _dataset_name_attr,
    _dtype_to_dap4,
    _normalize_scalar,
    namespace,
)

# DAP 4 Namespace URI and a mapping for passing to lxml
DAP4_NS = namespace[""]
NSMAP = {"dap":DAP4_NS}

_XML_NS = "http://www.w3.org/XML/1998/namespace"

# //////////////////////////////////////////////////////////////////////////////////////////
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
        the different elements that are handled are [DatasetType, GroupType, SequenceType, StructureType, and BaseType]
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

# //////////////////////////////////////////////////////////////////////////////////////////
# Helper functions
# ///////////////////////////////////////////////////////////////////////////////////

def _new_root(name):
    """Create the single root element, declaring the DAP4 default namespace."""
    return etree.Element(_qual_name(name), nsmap={None: DAP4_NS})

def _qual_name(name):
    """Return ``tag`` qualified with the DAP4 namespace (Clark notation).

    This is required because ``lxml`` does not retroactively infer an
    element's namespace from an ancestor's default ``xmlns`` declaration:
    each element's namespace has to be set explicitly at creation time in
    order for the tree to serialize back out with everything sharing the
    same DAP4 namespace.
    """
    return "{{{ns}}}{name}".format(ns=DAP4_NS, name=name)

def _build_dimensions(parent, dims):
    """
        Takes the parent node and create a new dimension and populates it with child elements.
    """
    for name, size in dims.items():
        _new_child(parent, "Dimension", name=str(name), size=str(size))

def _new_child(parent, name, **attr):
    """
        creates a new child node and returns it
    """
    element = etree.SubElement(parent, _qual_name(name))
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

# ///////////////////////////////////////////////////////////////////////////////////////////
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
