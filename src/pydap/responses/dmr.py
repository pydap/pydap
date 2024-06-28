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

from ..lib import DAP4_TO_NUMPY_PARSER_TYPEMAP, __version__
from ..model import BaseType, DatasetType, GroupType, SequenceType, StructureType
from .lib import BaseResponse

INDENT = " " * 4


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
        # generate DDS
        for line in dmr(self.dataset):
            yield line.encode("ascii")

        yield b"Data:\n"
        for block in dmr(self.dataset):
            yield block


@singledispatch
def dmr(var):
    """Single dispatcher for generating the DODS response."""
    raise StopIteration


@dmr.register(StructureType)
def _structuretype(var):
    for child in var.children():
        for block in dmr(child):
            yield block


@dmr.register(DatasetType)
def _(var, level=0, sequence=0):
    yield "{indent}Dataset {{\n".format(indent=level * INDENT)
    for child in var.children():
        for line in dmr(child, level + 1, sequence):
            yield line
    yield "{indent}}} {name};\n".format(indent=level * INDENT, name=var.name)


@dmr.register(SequenceType)
def _sequencetype(var, level=0, sequence=0):
    yield "{indent}Sequence {{\n".format(indent=level * INDENT)
    for child in var.children():
        for line in dmr(child, level + 1, sequence + 1):
            yield line
    yield "{indent}}} {name};\n".format(indent=level * INDENT, name=var.name)


@dmr.register(GroupType)
def _grouptype(var, level=0, sequence=0):
    yield "{indent}Group {{\n".format(indent=level * INDENT)
    for child in var.children():
        for line in dmr(child, level + 1, sequence):
            yield line
    yield "{indent}}} {name};\n".format(indent=level * INDENT, name=var.name)


@dmr.register(BaseType)
def _basetype(var, level=0, sequence=0):
    shape = var.shape[sequence:]

    if var.dimensions:
        shape = "".join(map("[{0[0]} = {0[1]}]".format, zip(var.dimensions, shape)))
    elif len(shape) == 1:
        shape = "[{0} = {1}]".format(var.name, shape[0])
    else:
        shape = "".join("[{0}]".format(len) for len in shape)

    yield "{indent}{type} {name}{shape};\n".format(
        indent=level * INDENT,
        type=DAP4_TO_NUMPY_PARSER_TYPEMAP[var.dtype],
        name=var.name,
        shape=shape,
    )
