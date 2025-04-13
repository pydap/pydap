"""The DDS response.

The DDS response builds a representation of the structure of the dataset,
informing which variables are contained, their shape, type and dimensions.
Together with the DAS, the DDS describes all metadata associated with a given
dataset, allowing clients to introspect the variables and request data as
necessary.

"""

try:
    from functools import singledispatch
except ImportError:
    from singledispatch import singledispatch

from ..lib import NUMPY_TO_DAP2_TYPEMAP, __version__
from ..model import BaseType, DatasetType, GridType, SequenceType, StructureType
from .lib import BaseResponse

INDENT = " " * 4


class DDSResponse(BaseResponse):
    """The DDS response."""

    __version__ = __version__

    def __init__(self, dataset):
        BaseResponse.__init__(self, dataset)
        self.headers.extend(
            [
                ("Content-description", "dods_dds"),
                ("Content-type", "text/plain; charset=ascii"),
            ]
        )

    def __iter__(self):
        for line in dds(self.dataset):
            yield line.encode("ascii")


@singledispatch
def dds(var, level=0, sequence=0):
    """Single dispatcher that generates the DDS response."""
    raise StopIteration


@dds.register(DatasetType)
def _(var, level=0, sequence=0):
    yield "{indent}Dataset {{\n".format(indent=level * INDENT)
    for child in var.children():
        for line in dds(child, level + 1, sequence):
            yield line
    yield "{indent}}} {name};\n".format(indent=level * INDENT, name=var.name)


@dds.register(SequenceType)
def _sequencetype(var, level=0, sequence=0):
    yield "{indent}Sequence {{\n".format(indent=level * INDENT)
    for child in var.children():
        for line in dds(child, level + 1, sequence + 1):
            yield line
    yield "{indent}}} {name};\n".format(indent=level * INDENT, name=var.name)


@dds.register(StructureType)
def _structuretype(var, level=0, sequence=0):
    yield "{indent}Structure {{\n".format(indent=level * INDENT)
    for child in var.children():
        for line in dds(child, level + 1, sequence):
            yield line
    yield "{indent}}} {name};\n".format(indent=level * INDENT, name=var.name)


@dds.register(GridType)
def _gridtype(var, level=0, sequence=0):
    yield "{indent}Grid {{\n".format(indent=level * INDENT)

    yield "{indent}Array:\n".format(indent=(level + 1) * INDENT)
    for line in dds(var.array, level + 2, sequence):
        yield line

    yield "{indent}Maps:\n".format(indent=(level + 1) * INDENT)
    for map_ in var.maps.values():
        for line in dds(map_, level + 2, sequence):
            yield line

    yield "{indent}}} {name};\n".format(indent=level * INDENT, name=var.name)


@dds.register(BaseType)
def _basetype(var, level=0, sequence=0):
    shape = var.shape[sequence:]

    if var.dims:
        shape = "".join(map("[{0[0]} = {0[1]}]".format, zip(var.dims, shape)))
    elif len(shape) == 1:
        shape = "[{0} = {1}]".format(var.name, shape[0])
    else:
        shape = "".join("[{0}]".format(len) for len in shape)

    yield "{indent}{type} {name}{shape};\n".format(
        indent=level * INDENT,
        type=NUMPY_TO_DAP2_TYPEMAP[var.dtype.char],
        name=var.name,
        shape=shape,
    )
