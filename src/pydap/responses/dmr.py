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
                ("Content-description", "dmr++"),
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
def _(var, level=0, path="/"):
    str0 = 'Dataset xmlns="{namespace}"'.format(namespace=namespace[""])
    str1 = ' xml:base="{url}"'.format(url="http://localhost:8001")
    str2 = ' dapVersion="4.0" dmrVersion="1.0"'
    str3 = ' name="{name}">\n'.format(name=var.name)
    yield "<{indent}".format(indent=level * INDENT) + str0 + str1 + str2 + str3
    for child in var.children():
        for line in dmr(child, level + 1, path):
            yield line
    yield "{indent}</Dataset>\n".format(indent=level * INDENT)


@dmr.register(StructureType)
def _structuretype(var):
    pass


@dmr.register(SequenceType)
def _sequencetype(var, level=0, sequence=0):
    pass


@dmr.register(GroupType)
def _grouptype(var, level=0, path="/"):
    dims = var.dimensions
    yield '{indent}<Group name="{name}">\n'.format(indent=level * INDENT, name=var.name)
    path += var.name + "/"
    for dim in dims:
        size = var[dim].shape[0]
        yield '{indent}<Dimension name="{name}" size="{size}"/>\n'.format(
            indent=(level + 1) * INDENT, name=dim, size=size
        )
    for child in var.children():
        for line in dmr(child, level + 1, path):
            yield line
    yield "{indent}</Group>\n".format(indent=level * INDENT)


@dmr.register(BaseType)
def _basetype(var, level=0, path="/"):
    _ntype = var.dtype
    _vartype = str(_ntype)[0].upper() + str(_ntype)[1:]
    yield '{indent}<{type} name="{name}">\n'.format(
        indent=level * INDENT,
        type=_vartype,
        name=var.name,
    )
    # get dimensions
    dims = var.dimensions
    for dim in dims:
        yield '{indent}<Dim name="{name}"/>\n'.format(
            indent=(level + 1) * INDENT, name=path + dim
        )
    for key, value in var.attributes.items():
        _type = type(value).__name__
        yield '{indent}<Attribute name="{name}" type="{type}">\n'.format(
            indent=(level + 1) * INDENT, name=key, type=_type
        )
        yield "{indent}<Value>{val}</Value>\n".format(
            indent=(level + 2) * INDENT, val=value
        )
        yield "{indent}</Attribute>\n".format(indent=(level + 1) * INDENT)
    yield "{indent}</{type}>\n".format(indent=level * INDENT, type=_vartype)
