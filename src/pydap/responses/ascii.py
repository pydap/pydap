"""The ASCII response.

The ASCII response is an unnoficial response used to return the data as ASCII.
Pydap's implementation is reverse engineered from the official server.

"""

try:
    from functools import singledispatch
except ImportError:
    from singledispatch import singledispatch
import copy

import numpy as np
from six.moves import zip

from pydap.model import (BaseType,
                         SequenceType, StructureType)
from pydap.lib import encode, __version__
from pydap.responses.lib import BaseResponse
from pydap.responses.dds import dds


class ASCIIResponse(BaseResponse):

    """The ASCII response."""

    __version__ = __version__

    def __init__(self, dataset):
        BaseResponse.__init__(self, dataset)
        self.headers.extend([
            ('Content-description', 'dods_ascii'),
            ('Content-type', 'text/plain; charset=ascii'),
        ])

    def __iter__(self):
        for line in dds(self.dataset):
            yield line.encode('ascii')
        yield (45 * '-' + '\n').encode('ascii')

        for line in ascii(self.dataset):
            yield line.encode('ascii')


@singledispatch
def ascii(var, printname=True):
    """A single dispatcher for the ASCII response."""
    raise StopIteration


@ascii.register(SequenceType)
def _sequenctype(var, printname=True):
    yield ', '.join([child.id for child in var.children()])
    yield '\n'
    for rec in var:
        out = copy.copy(var)
        out.__class__ = StructureType
        out.data = rec
        for i, line in enumerate(ascii(out, printname=False)):
            line = line.strip()
            if line and i > 0:
                yield ', '
            yield line
        yield '\n'


@ascii.register(StructureType)
def _structuretype(var, printname=True):
    for child in var.children():
        for line in ascii(child, printname):
            yield line
        yield '\n'


@ascii.register(BaseType)
def _basetype(var, printname=True):
    if printname:
        yield var.id
        yield '\n'

    if not getattr(var, "shape", ()):
        yield encode(var.data)
    else:
        for indexes, value in zip(np.ndindex(var.shape), var.data.flat):
            yield "{indexes} {value}\n".format(
                indexes="[" + "][".join([str(idx) for idx in indexes]) + "]",
                value=encode(value))
