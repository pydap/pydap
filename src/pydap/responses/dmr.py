"""The DMR response.

The DMR response builds a representation of the structure of the dataset,
informing which variables are contained, their shape, type and dimensions.
The DMR describes all metadata associated with a given dataset, allowing
clients to introspect the variables and request data as necessary.

"""

from collections import OrderedDict
from collections.abc import Iterable, Mapping
from functools import singledispatch
from xml.sax.saxutils import escape

import numpy as np

from pydap.lib import NUMPY_TO_DAP4_TYPEMAP, __version__
from pydap.model import BaseType, DatasetType, GroupType, SequenceType, StructureType
from pydap.responses.lib import BaseResponse

INDENT = " " * 4
namespace = {"": "http://xml.opendap.org/ns/DAP/4.0#"}


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
