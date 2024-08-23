"""The DAS response.

The DAS response describes the attributes associated with a dataset and its
variables. Together with the DDS the DAS response completely describes the
metadata of a dataset, allowing it to be introspected and data to be
downloaded.

"""

try:
    from functools import singledispatch
except ImportError:
    from singledispatch import singledispatch

from collections.abc import Iterable

import numpy as np

from ..lib import NUMPY_TO_DAP2_TYPEMAP, __version__, _quote, encode
from ..model import BaseType, DatasetType, GridType, SequenceType, StructureType
from .lib import BaseResponse

INDENT = " " * 4


class DASResponse(BaseResponse):
    """The DAS response."""

    __version__ = __version__

    def __init__(self, dataset):
        BaseResponse.__init__(self, dataset)
        self.headers.extend(
            [
                ("Content-description", "dods_das"),
                ("Content-type", "text/plain; charset=ascii"),
            ]
        )

    def __iter__(self):
        for line in das(self.dataset):
            try:
                yield line.encode("ascii")
            except UnicodeDecodeError:
                yield line.encode("UTF-8")


@singledispatch
def das(var, level=0):
    """Single dispatcher that generates the DAS response."""
    raise StopIteration


@das.register(DatasetType)
def _datasettype(var, level=0):
    yield "{indent}Attributes {{\n".format(indent=level * INDENT)

    for attr in sorted(var.attributes.keys()):
        values = var.attributes[attr]
        for line in build_attributes(attr, values, level + 1):
            yield line

    for child in var.children():
        for line in das(child, level=level + 1):
            yield line
    yield "{indent}}}\n".format(indent=level * INDENT)


@das.register(StructureType)
@das.register(SequenceType)
def _structuretype(var, level=0):
    yield "{indent}{name} {{\n".format(indent=level * INDENT, name=var.name)

    for attr in sorted(var.attributes.keys()):
        values = var.attributes[attr]
        for line in build_attributes(attr, values, level + 1):
            yield line

    for child in var.children():
        for line in das(child, level=level + 1):
            yield line
    yield "{indent}}}\n".format(indent=level * INDENT)


@das.register(BaseType)
@das.register(GridType)
def _basetypegridtype(var, level=0):
    yield "{indent}{name} {{\n".format(indent=level * INDENT, name=var.name)

    for attr in sorted(var.attributes.keys()):
        values = var.attributes[attr]
        if np.asarray(values).size > 0:
            for line in build_attributes(attr, values, level + 1):
                yield line
    yield "{indent}}}\n".format(indent=level * INDENT)


def build_attributes(attr, values, level=0):
    """Recursive function to build the DAS."""
    # check for metadata
    if isinstance(values, dict):
        yield "{indent}{attr} {{\n".format(indent=(level) * INDENT, attr=attr)
        for k, v in values.items():
            for line in build_attributes(k, v, level + 1):
                yield line
        yield "{indent}}}\n".format(indent=(level) * INDENT)
    else:
        # get type
        type = get_type(values)

        # encode values
        if (
            isinstance(values, str)
            or not isinstance(values, Iterable)
            or getattr(values, "shape", None) == ()
        ):
            values = [encode(values)]
        else:
            values = map(encode, values)

        yield "{indent}{type} {attr} {values};\n".format(
            indent=(level) * INDENT,
            type=type,
            attr=_quote(attr),
            values=", ".join(values),
        )


def get_type(values):
    """Extract the type of a variable.

    This function tries to determine the DAP type of a Python variable using
    several methods. Returns the DAP type as a string.

    """
    if hasattr(values, "dtype"):
        return NUMPY_TO_DAP2_TYPEMAP[values.dtype.char]
    elif isinstance(values, str) or not isinstance(values, Iterable):
        return type_convert(values)
    else:
        # if there are several values, they may have different types, so we
        # need to convert all of them and use a precedence table
        types = [type_convert(val) for val in values]
        precedence = ["String", "Float64", "Int32"]
        types.sort(key=precedence.index)
        return types[0]


def type_convert(obj):
    """Map Python objects to the corresponding Opendap types.

    Returns the DAP representation of the type as a string.

    """
    if isinstance(obj, float):
        return "Float64"
    elif isinstance(obj, int):
        return "Int32"
    else:
        return "String"
