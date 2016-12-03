"""The DODS response.

This is the DAP response that carries data. The response comes with a DDS
header describing the structure of the data, followed by the data encoded as
XDR.

Even though Python has a library for XDR encoding/decoding, the DODS response
uses Numpy directly since it's faster.

"""

import copy

import numpy as np
from six import string_types

from pydap.model import (BaseType,
                         SequenceType, StructureType)
from pydap.lib import walk, START_OF_SEQUENCE, END_OF_SEQUENCE, __version__
from pydap.responses.lib import BaseResponse
from pydap.responses.dds import dds

try:
    from functools import singledispatch
except ImportError:
    from singledispatch import singledispatch

typemap = {
    'd': '>d',
    'f': '>f',
    'i': '>i', 'l': '>i', 'q': '>i', 'h': '>i',
    'b': 'B',
    'I': '>I', 'L': '>I', 'Q': '>I', 'H': '>I',
    'B': 'B',
    'U': 'S'  # Map unicode to string type b/c
              # DAP doesn't explicitly support it
}


class DODSResponse(BaseResponse):

    """The DODS response."""

    __version__ = __version__

    def __init__(self, dataset):
        BaseResponse.__init__(self, dataset)
        self.headers.extend([('Content-description', 'dods_data'),
                             ('Content-type', 'application/octet-stream')])

        length = calculate_size(dataset)
        if length is not None:
            self.headers.append(('Content-length', str(length)))

    def __iter__(self):
        # generate DDS
        for line in dds(self.dataset):
            yield line.encode('ascii')

        yield b'Data:\n'
        for block in dods(self.dataset):
            yield block


@singledispatch
def dods(var):
    """Single dispatcher for generating the DODS response."""
    raise StopIteration


@dods.register(StructureType)
def _structuretype(var):
    for child in var.children():
        for block in dods(child):
            yield block


@dods.register(SequenceType)
def _sequencetype(var):
    # a flat array can be processed one record (or more?) at a time
    if all(isinstance(child, BaseType) for child in var.children()):
        types = []
        position = 0
        for child in var.children():
            if child.dtype.char in 'SU':
                types.append('>I')                  # string length as int
                types.append('|S{%s}' % position)   # string padded to 4n
                position += 1
            else:
                types.append(typemap[child.dtype.char])
        dtype = ','.join(types)
        strings = position > 0

        # array initializations is costy, so we keep a cache here; this will
        # be inneficient if there are many strings of different length only
        cache = {}

        for record in var:
            yield START_OF_SEQUENCE

            if strings:
                out = []
                padded = []
                for value in record:
                    if isinstance(value, string_types):
                        length = len(value) or 1
                        out.append(length)
                        padded.append(length + (-length % 4))
                    out.append(value)
                record = out
                dtype = ','.join(types).format(*padded)

            if dtype not in cache:
                cache[dtype] = np.zeros((1,), dtype=dtype)
            cache[dtype][:] = tuple(record)
            yield cache[dtype].tostring()

        yield END_OF_SEQUENCE

    # nested array, need to process individually
    else:
        # create a template structure
        struct = StructureType(var.name)
        for name in var.keys():
            struct[name] = copy.copy(var[name])

        for record in var:
            yield START_OF_SEQUENCE
            struct.data = record
            for block in dods(struct):
                yield block
        yield END_OF_SEQUENCE


@dods.register(BaseType)
def _basetype(var):
    data = var.data

    if not hasattr(data, "shape"):
        data = np.asarray(data)

    if data.shape:
        # pack length for arrays
        length = np.prod(data.shape).astype('I')
        if data.dtype.char in 'SU':
            yield length.newbyteorder('>').tostring()
        else:
            yield length.newbyteorder('>').tostring() * 2

    # bytes are padded up to 4n
    if data.dtype == np.byte:
        length = np.prod(data.shape)
        for block in data:
            yield block.tostring()
        yield (-length % 4) * b'\0'

    # regular data
    else:
        # make data iterable; 1D arrays must be converted to 2D, since
        # iteration over 1D yields scalars which are not properly cast to big
        # endian
        if len(data.shape) < 2:
            data = data.reshape(1, -1)

        # strings are also zero padded and preceeded by their length
        if data.dtype.char in 'SU':
            for block in data:
                for word in block.flat:
                    length = len(word)
                    yield np.array(length).astype('>I').tostring()
                    if hasattr(word, 'encode'):
                        yield word.encode('ascii')
                    elif hasattr(word, 'tostring'):
                        yield word.tostring()
                    else:
                        raise TypeError("Could not convert word '{0}' to bytes"
                                        .format(word))
                    yield (-length % 4) * b'\0'
        else:
            for block in data:
                yield block.astype(typemap[data.dtype.char]).tostring()


def calculate_size(dataset):
    """Calculate the size of the response. Returns the size in bytes."""
    length = 0

    for var in walk(dataset):
        # Pydap can't calculate the size of sequences since the data is
        # streamed directly from the source. Also, strings are encoded
        # individually, so it's not possible to get their size unless we read
        # everything.
        if (isinstance(var, SequenceType) or
                (isinstance(var, BaseType) and var.dtype.char in 'SU')):
            return None
        elif isinstance(var, BaseType):
            if var.shape:
                length += 8  # account for array size marker

            size = int(np.prod(var.shape))
            if var.data.dtype == np.byte:
                length += size + (-size % 4)
            elif var.data.dtype == np.short:
                length += size * 4
            else:
                opendap_size = np.dtype(typemap[var.data.dtype.char]).itemsize
                length += size * opendap_size

    # account for DDS
    length += len(''.join(dds(dataset))) + len(b'Data:\n')

    return length
