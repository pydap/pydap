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

from ..model import (BaseType,
                     SequenceType, StructureType)
from ..lib import (walk, START_OF_SEQUENCE, END_OF_SEQUENCE, __version__,
                   NUMPY_TO_DAP2_TYPEMAP,
                   DAP2_TO_NUMPY_RESPONSE_TYPEMAP,
                   DAP2_ARRAY_LENGTH_NUMPY_TYPE)
from .lib import BaseResponse
from .dds import dds

try:
    from functools import singledispatch
except ImportError:
    from singledispatch import singledispatch


def DAP2_response_dtypemap(dtype):
    """
    This function takes a numpy dtype object
    and returns a dtype object that is compatible with
    the DAP2 specification.
    """
    dtype_str = DAP2_TO_NUMPY_RESPONSE_TYPEMAP[
                    NUMPY_TO_DAP2_TYPEMAP[
                        dtype.char]]
    return np.dtype(dtype_str)


def tostring_with_byteorder(x, dtype):
    return (x
            .astype(dtype.str)
            .newbyteorder(dtype.byteorder)
            .tostring())


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
        DAP2_types = []
        position = 0
        for child in var.children():
            if DAP2_response_dtypemap(child.dtype).char == 'S':
                (DAP2_types
                 .append(DAP2_ARRAY_LENGTH_NUMPY_TYPE))  # string length
                DAP2_types.append('|S{%s}' % position)   # string padded to 4n
                position += 1
            else:
                # Convert any numpy dtypes to numpy dtypes compatible
                # with the DAP2 standard:
                DAP2_types.append(DAP2_response_dtypemap(child.dtype).str)
        DAP2_dtype_str = ','.join(DAP2_types)
        strings = position > 0

        # array initializations is costy, so we keep a cache here; this will
        # be inneficient if there are many strings of different length only
        cache = {}

        for record in var.iterdata():
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
                DAP2_dtype_str = ','.join(DAP2_types).format(*padded)

            if DAP2_dtype_str not in cache:
                # Remember that DAP2_dtype is a (possibly composite)
                # numpy dtype that is compatible with the DAP2
                # data model. This means that all dtypes in
                # DAP2_dtype are representable in DAP2 -- AND --
                # the data in var can all be upconverted
                # in a lossless manner to the dtypes in DAP2_dtype.
                cache[DAP2_dtype_str] = np.zeros((1,), dtype=DAP2_dtype_str)
            # By assigning record to ``cache`` the upconversion
            # occurs naturally:
            cache[DAP2_dtype_str][:] = tuple(record)
            # byteorder was taken care of during the upconversion:
            yield cache[DAP2_dtype_str].tostring()

        yield END_OF_SEQUENCE

    # nested array, need to process individually
    else:
        # create a template structure
        struct = StructureType(var.name)
        for name in var.keys():
            struct[name] = copy.copy(var[name])

        for record in var.iterdata():
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

    # Convert any numpy dtypes to numpy dtypes compatible
    # with the DAP2 standard:
    DAP2_dtype = DAP2_response_dtypemap(data.dtype)

    if data.shape:
        # pack length for arrays
        length = np.prod(data.shape).astype(np.int)

        # send length twice at the begining of an array...
        factor = 2
        if DAP2_dtype.char == 'S':
            # ... expcept for strings:
            factor = 1
        yield tostring_with_byteorder(
                length,
                np.dtype(DAP2_ARRAY_LENGTH_NUMPY_TYPE)) * factor

    # make data iterable; 1D arrays must be converted to 2D, since
    # iteration over 1D yields scalars which are not properly cast to big
    # endian
    # This line was removed because endianness is now treated explicitly
    # in tostring_with_byteorder()
    # if len(data.shape) < 2:
    #     data = data.reshape(1, -1)
    # Only ensure that 0d arrays are iterable:
    if len(data.shape) == 0:
        data = data[np.newaxis]

    # unsigned bytes are padded up to 4n
    if DAP2_dtype == np.ubyte:
        length = np.prod(data.shape).astype(np.int)
        for block in data:
            yield tostring_with_byteorder(block, DAP2_dtype)
        yield (-length % 4) * b'\0'

    # regular data
    else:
        # strings are also zero padded and preceeded by their length
        if DAP2_dtype.char == 'S':
            for block in data:
                for word in block.flat:
                    length = len(word)
                    yield tostring_with_byteorder(
                                np.array(length),
                                np.dtype(DAP2_ARRAY_LENGTH_NUMPY_TYPE))
                    # byteorder is not important for strings:
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
                # Remember that DAP2_dtype is a
                # numpy dtype that is compatible with the DAP2
                # data model. This means that the dtype in
                # DAP2_dtype is representable in DAP2 -- AND --
                # the data in var can all be upconverted
                # in a lossless manner to the dtype in DAP2_dtype.
                yield tostring_with_byteorder(block, DAP2_dtype)


def calculate_size(dataset):
    """Calculate the size of the response. Returns the size in bytes."""
    length = 0

    for var in walk(dataset):
        # Pydap can't calculate the size of sequences since the data is
        # streamed directly from the source. Also, strings are encoded
        # individually, so it's not possible to get their size unless we read
        # everything.
        if (isinstance(var, SequenceType) or
            (isinstance(var, BaseType) and
             DAP2_response_dtypemap(var.dtype).char == 'S')):
            return None
        elif isinstance(var, BaseType):
            if var.shape:
                length += 8  # account for array size marker

            size = int(np.prod(var.shape))

            # Convert any numpy dtype to numpy dtype compatible
            # with the DAP2 standard:
            DAP2_dtype = DAP2_response_dtypemap(var.data.dtype)
            if DAP2_dtype == np.ubyte:
                length += size + (-size % 4)
            else:
                # Remember that numpy dtypes are upconverted to
                # DAP2_dtype when sent in the response.
                # Their length must thus be modified accordingly:
                length += size * DAP2_dtype.itemsize

    # account for DDS
    length += len(''.join(dds(dataset))) + len(b'Data:\n')
    return length
