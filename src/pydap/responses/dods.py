from collections import Iterable

import numpy as np

from pydap.model import *
from pydap.lib import walk, START_OF_SEQUENCE, END_OF_SEQUENCE
from pydap.responses.lib import BaseResponse
from pydap.responses.dds import dispatch as dds_dispatch


typemap = {
        'd': '>d',
        'f': '>f',
        'i': '>i', 'l': '>i', 'q': '>i', 'h': '>i',
        'b': 'B',
        'I': '>I', 'L': '>I', 'Q': '>I', 'H': '>I',
        'B': 'B',
}


class DODSResponse(BaseResponse):
    def __init__(self, dataset):
        BaseResponse.__init__(self, dataset)
        self.headers.extend([
            ('Content-description', 'dods_data'),
            ('Content-type', 'application/octet-stream'),

            # CORS
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Headers',
                'Origin, X-Requested-With, Content-Type'),
        ])

        length = calculate_size(dataset)
        if length is not None:
            self.headers.append(('Content-length', length))

    def __iter__(self):
        # generate DDS
        for line in dds_dispatch(self.dataset):
            yield line

        yield 'Data:\n'
        for block in dispatch(self.dataset):
            yield block 

        if hasattr(self.dataset, 'close'):
            self.dataset.close()


def dispatch(var):
    types = [
            (SequenceType, sequence),
            (StructureType, structure),
            (BaseType, base),
    ]

    for class_, func in types:
        if isinstance(var, class_):
            return func(var)


def structure(var):
    for child in var.children():
        for block in dispatch(child):
            yield block


def sequence(var):
    # a flat array can be processed one record (or more?) at a time
    if all(isinstance(child, BaseType) for child in var.children()):
        types = []
        for child in var.children():
            if child.dtype.char in 'SU':
                types.append('>I')    # string length as int
                types.append('|S{}')  # string padded to 4n
            else:
                types.append(typemap[child.dtype.char])
        dtype = ','.join(types)
        strings = '|S{}' in types

        # array initializations is costy, so we keep a cache here; this will
        # be inneficient if there are many strings of different length only
        cache = {}

        for record in var:
            yield START_OF_SEQUENCE

            if strings:
                out = []
                padded = []
                for value in record:
                    if isinstance(value, basestring):
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
            struct[name] = var[name].clone()
            if isinstance(struct[name], SequenceType):
                struct[name].sequence_level -= 1

        for record in var:
            yield START_OF_SEQUENCE
            struct.data = record
            for block in structure(struct):
                yield block
        yield END_OF_SEQUENCE


def base(var):
    data = var.data

    if data.shape:
        # pack length for arrays
        length = np.prod(data.shape).astype('I')
        if data.dtype.char == 'S':
            yield length.newbyteorder('>').tostring()
        else:
            yield length.newbyteorder('>').tostring() * 2

    # bytes are padded up to 4n
    if data.dtype == np.byte:
        length = np.prod(data.shape)
        for block in data:
            yield block.tostring()
        yield (-length % 4) * '\0'

    # strings are also zero padded and preceeded by their length
    elif data.dtype.char == 'S':
        for block in data:
            for word in block.flat:
                length = len(word)
                yield np.array(length).astype('>I').tostring()
                yield word
                yield (-length % 4) * '\0'

    # regular data
    else:
        # make data iterable; 1D arrays must be converted to 2D, since iteration
        # over 1D yields scalars which are not properly cast to big endian
        if len(data.shape) < 2:
            try:
                data = data.reshape(1, -1)
            except:
                data = [data]

        for block in data:
            yield block.astype(typemap[block.dtype.char]).tostring()


def calculate_size(dataset):
    """
    Calculate the size of the response.

    """
    length = 0

    for var in walk(dataset):
        # Pydap can't calculate the size of sequences since the data is streamed
        # directly from the source. Also, strings are encoded individually, so 
        # it's not possible to get their size unless we read everything.
        if (isinstance(var, SequenceType) or
                (isinstance(var, BaseType) and var.data.dtype.char == 'S')):
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
    length += len(''.join(dds_dispatch(dataset))) + len('Data:\n')

    return str(length)
