"""The DMR response.

The DMR response builds a representation of the structure of the dataset,
informing which variables are contained, their shape, type and dimensions.
The DMR describes all metadata associated with a given dataset, allowing
clients to introspect the variables and request data as necessary.

"""

try:
    from functools import singledispatch
except ImportError:
    from singledispatch import singledispatch

from ..lib import __version__
from ..model import BaseType, DatasetType, GroupType, SequenceType, StructureType
from .lib import BaseResponse

INDENT = " " * 4
namespace = {"": "http://xml.opendap.org/ns/DAP/4.0#"}


class DMRResponse(BaseResponse):
    """The DDS response."""

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
    """Single dispatcher for generating the DODS response."""
    raise StopIteration


@dmr.register(DatasetType)
def _(var, level=0):
    str0 = 'Dataset xmlns="{namespace}"'.format(namespace=namespace[""])
    str1 = ' xml:base="{url}"'.format(url="http://localhost:8001")
    str2 = ' dapVersion="4.0" dmrVersion="1.0"'
    str3 = ' name="{name}">\n'.format(name=var.name)
    yield "<{indent}".format(indent=level * INDENT) + str0 + str1 + str2 + str3
    for name, size in var.dimensions.items():
        yield '{indent}<Dimension name="{name}" size="{size}"/>\n'.format(
            indent=(level + 1) * INDENT, name=name, size=size
        )
    for child in var.children():
        for line in dmr(child, level + 1):
            yield line
    for key, value in var.attributes.items():
        if key != "dimensions":
            _type = type(value).__name__
            yield '{indent}<Attribute name="{name}" type="{type}">\n'.format(
                indent=(level + 1) * INDENT, name=key, type=_type
            )
            yield "{indent}<Value>{val}</Value>\n".format(
                indent=(level + 2) * INDENT, val=value
            )
            yield "{indent}</Attribute>\n".format(indent=(level + 1) * INDENT)

    yield "{indent}</Dataset>\n".format(indent=level * INDENT)


@dmr.register(StructureType)
def _structuretype(var):
    pass


@dmr.register(SequenceType)
def _sequencetype(var, level=0, sequence=0):
    pass


@dmr.register(GroupType)
def _grouptype(var, level=0):
    yield '{indent}<Group name="{name}">\n'.format(indent=level * INDENT, name=var.name)
    for dim, size in var.attributes["dimensions"].items():
        yield '{indent}<Dimension name="{name}" size="{size}"/>\n'.format(
            indent=(level + 1) * INDENT, name=dim, size=size
        )
    for key, value in var.attributes.items():
        if key not in ["dimensions", "path"]:
            _type = type(value).__name__
            yield '{indent}<Attribute name="{name}" type="{type}">\n'.format(
                indent=(level + 1) * INDENT, name=key, type=_type
            )
            yield "{indent}<Value>{val}</Value>\n".format(
                indent=(level + 2) * INDENT, val=value
            )
            yield "{indent}</Attribute>\n".format(indent=(level + 1) * INDENT)
    for child in var.children():
        for line in dmr(child, level + 1):
            yield line
    yield "{indent}</Group>\n".format(indent=level * INDENT)


@dmr.register(BaseType)
def _basetype(var, level=0):
    _ntype = var.dtype
    _vartype = str(_ntype)[0].upper() + str(_ntype)[1:]
    if _vartype == "<U0":
        _vartype = "String"
    yield '{indent}<{type} name="{name}">\n'.format(
        indent=level * INDENT,
        type=_vartype,
        name=var.name,
    )
    # get dimensions
    for dim in var.dims:
        yield '{indent}<Dim name="{name}"/>\n'.format(
            indent=(level + 1) * INDENT, name=dim
        )
    for key, value in var.attributes.items():
        if key != "dims":
            if isinstance(value, list):
                _type = type(value[0]).__name__
                yield '{indent}<Attribute name="{name}" type="{type}">\n'.format(
                    indent=(level + 1) * INDENT, name=key, type=_type
                )
                for val in value:
                    yield "{indent}<Value>{val}</Value>\n".format(
                        indent=(level + 2) * INDENT, val=val
                    )
            else:
                _type = type(value).__name__
                yield '{indent}<Attribute name="{name}" type="{type}">\n'.format(
                    indent=(level + 1) * INDENT, name=key, type=_type
                )
                yield "{indent}<Value>{val}</Value>\n".format(
                    indent=(level + 2) * INDENT, val=value
                )
            yield "{indent}</Attribute>\n".format(indent=(level + 1) * INDENT)
    yield "{indent}</{type}>\n".format(indent=level * INDENT, type=_vartype)

    # get maps
    if "Maps" in var.attributes.keys():
        Maps = var.Maps
        for _map in Maps:
            yield '{indent}<Map name="{name}">\n'.format(
                indent=(level + 1) * INDENT, name=_map
            )
