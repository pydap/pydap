"""The DMR response.

The DMR response builds a representation of the structure of the dataset,
informing which variables are contained, their shape, type and dimensions.
The DMR describes all metadata associated with a given dataset, allowing
clients to introspect the variables and request data as necessary.

"""

from collections.abc import Mapping
from functools import singledispatch

from pydap.lib import __version__
from pydap.model import BaseType, DatasetType, GroupType, SequenceType, StructureType
from pydap.responses.lib import BaseResponse
from pydap.responses.xml import (
    _attribute_items,
    _attribute_type,
    _attribute_values,
    _children_by_declaration_order,
    _container_dimension_context,
    _dataset_name_attr,
    _dtype_to_dap4,
    _xml_attr,
    _xml_text,
    namespace,
)

INDENT = " " * 4


def _emit_dimensions(dimensions, level):
    for name, size in dimensions.items():
        yield '{indent}<Dimension name="{name}" size="{size}"/>\n'.format(
            indent=level * INDENT, name=_xml_attr(name), size=_xml_attr(size)
        )


def _emit_variable_dimensions(var, level, phony_dimensions=()):
    for dim in var.dims:
        yield '{indent}<Dim name="{name}"/>\n'.format(
            indent=level * INDENT, name=_xml_attr(dim)
        )
    for dim in phony_dimensions:
        yield '{indent}<Dim name="{name}"/>\n'.format(
            indent=level * INDENT, name=_xml_attr(dim)
        )


def _emit_attributes(attributes, level, excluded=()):
    for key, value in _attribute_items(attributes, excluded):
        yield from _emit_attribute(key, value, level)


def _emit_attribute(key, value, level):
    indent = level * INDENT
    if isinstance(value, Mapping):
        yield '{indent}<Attribute name="{name}" type="Container">\n'.format(
            indent=indent, name=_xml_attr(key)
        )
        for child_key, child_value in value.items():
            yield from _emit_attribute(child_key, child_value, level + 1)
        yield "{indent}</Attribute>\n".format(indent=indent)
        return

    values = _attribute_values(value)
    attribute_type = _attribute_type(values)
    yield '{indent}<Attribute name="{name}" type="{type}">\n'.format(
        indent=indent, name=_xml_attr(key), type=attribute_type
    )
    for item in values:
        if item is None:
            yield "{indent}<Value/>\n".format(indent=(level + 1) * INDENT)
        else:
            yield "{indent}<Value>{value}</Value>\n".format(
                indent=(level + 1) * INDENT, value=_xml_text(item)
            )
    yield "{indent}</Attribute>\n".format(indent=indent)


def _emit_child_variables(var, level, phony_dimensions=None):
    if phony_dimensions is None:
        phony_dimensions = {}
    variables, _ = _children_by_declaration_order(var)
    for child in variables:
        for line in dmr(
            child, level, phony_dimensions=phony_dimensions.get(id(child), ())
        ):
            yield line


def _emit_child_groups(var, level):
    _, groups = _children_by_declaration_order(var)
    for child in groups:
        for line in dmr(child, level):
            yield line


class DMRResponse(BaseResponse):
    """The DMR response."""

    __version__ = __version__

    def __init__(self, dataset):
        BaseResponse.__init__(self, dataset)
        self.headers.extend(
            [
                ("Content-description", "dmr"),
                ("Content-type", "text/plain; charset=ascii"),
            ]
        )

    def __iter__(self):
        # generate DMR
        yield '<?xml version="1.0" encoding="ISO-8859-1"?>\n'.encode("ascii")
        for line in dmr(self.dataset):
            yield line.encode("ascii")


@singledispatch
def dmr(var):
    """Single dispatcher for generating the DMR response."""
    raise StopIteration


@dmr.register(DatasetType)
def _(var, level=0, phony_dimensions=()):
    str0 = 'Dataset xmlns="{namespace}"'.format(namespace=namespace[""])
    str1 = ' xml:base="{url}"'.format(url=_xml_attr("http://localhost:8001"))
    str2 = ' dapVersion="4.0" dmrVersion="1.0"'
    str3 = ' name="{name}">\n'.format(name=_dataset_name_attr(var.name))
    dimensions, child_phony_dimensions = _container_dimension_context(var)
    yield "<{indent}".format(indent=level * INDENT) + str0 + str1 + str2 + str3
    yield from _emit_dimensions(dimensions, level + 1)
    yield from _emit_child_variables(var, level + 1, child_phony_dimensions)
    yield from _emit_attributes(var.attributes, level + 1, excluded=("dimensions",))
    yield from _emit_child_groups(var, level + 1)

    yield "{indent}</Dataset>\n".format(indent=level * INDENT)


@dmr.register(StructureType)
def _structuretype(var, level=0, phony_dimensions=()):
    yield '{indent}<Structure name="{name}">\n'.format(
        indent=level * INDENT, name=_xml_attr(var.name)
    )
    yield from _emit_child_variables(var, level + 1)
    for dim in getattr(var, "dims", ()):
        yield '{indent}<Dim name="{name}"/>\n'.format(
            indent=(level + 1) * INDENT, name=_xml_attr(dim)
        )
    yield "{indent}</Structure>\n".format(indent=level * INDENT)


@dmr.register(SequenceType)
def _sequencetype(var, level=0, sequence=0, phony_dimensions=()):
    yield '{indent}<Sequence name="{name}">\n'.format(
        indent=level * INDENT, name=_xml_attr(var.name)
    )
    yield from _emit_child_variables(var, level + 1)
    for dim in getattr(var, "dims", ()):
        yield '{indent}<Dim name="{name}"/>\n'.format(
            indent=(level + 1) * INDENT, name=_xml_attr(dim)
        )
    yield "{indent}</Sequence>\n".format(indent=level * INDENT)


@dmr.register(GroupType)
def _grouptype(var, level=0, phony_dimensions=()):
    dimensions, child_phony_dimensions = _container_dimension_context(var)
    yield '{indent}<Group name="{name}">\n'.format(
        indent=level * INDENT, name=_xml_attr(var.name)
    )
    yield from _emit_dimensions(dimensions, level + 1)
    yield from _emit_child_variables(var, level + 1, child_phony_dimensions)
    yield from _emit_attributes(
        var.attributes, level + 1, excluded=("dimensions", "path", "Maps")
    )
    yield from _emit_child_groups(var, level + 1)
    yield "{indent}</Group>\n".format(indent=level * INDENT)


@dmr.register(BaseType)
def _basetype(var, level=0, phony_dimensions=()):
    _vartype = _dtype_to_dap4(var.dtype)
    yield '{indent}<{type} name="{name}">\n'.format(
        indent=level * INDENT,
        type=_vartype,
        name=_xml_attr(var.name),
    )
    yield from _emit_variable_dimensions(var, level + 1, phony_dimensions)
    yield from _emit_attributes(
        var.attributes, level + 1, excluded=("dims", "Maps", "path")
    )
    for _map in var.attributes.get("Maps", ()):
        yield '{indent}<Map name="{name}"/>\n'.format(
            indent=(level + 1) * INDENT, name=_xml_attr(_map)
        )
    yield "{indent}</{type}>\n".format(indent=level * INDENT, type=_vartype)
