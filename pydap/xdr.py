# This Python file uses the following encoding: utf-8
import struct

import numpy

from pydap.model import *


START_OF_SEQUENCE = '\x5a\x00\x00\x00'
END_OF_SEQUENCE = '\xa5\x00\x00\x00'


class DapPacker(object):
    def __init__(self, var):
        self.var = var

    def __iter__(self):
        if isinstance(self.var, SequenceType):
            for struct_ in self.var:
                yield START_OF_SEQUENCE
                for line in DapPacker(struct_):
                    yield line
            yield END_OF_SEQUENCE
        elif isinstance(self.var, StructureType):
            for child in self.var.walk():
                for line in DapPacker(child):
                    yield line
        else:
            # Get data...
            if getattr(self.var.data, 'shape', False):
                data = self.var.data
            else:
                data = numpy.asarray(self.var.data)
            # ...and give it iterable blocks:
            if len(data.shape) < 2:
                try:
                    data.shape = (1, -1)
                except:
                    pass

            # Yield length (twice) if array.
            if getattr(self.var, 'shape', None):
                if self.var.type in [Url, String]:
                    yield self._pack_length()
                else:
                    yield self._pack_length() * 2

            # Bytes are sent differently.
            if self.var.type == Byte:
                for b in self._pack_bytes(data):
                    yield b
            # String are zero padded to 4n.
            elif self.var.type in [Url, String]:
                for block in data:
                    for word in block.flat:
                        yield self._pack_string(word)
            else:
                for block in data:
                    dtype = ">%s%s" % (self.var.type.typecode, self.var.type.size)
                    yield block.astype(dtype).tostring()

    def __str__(self):
        return ''.join(self)

    def _pack_length(self):
        shape = getattr(self.var, 'shape', [1])
        length = numpy.prod(shape)
        return struct.pack('>L', long(length))

    def _pack_bytes(self, data):
        count = 0
        for block in data:
            data = block.astype('B').tostring()
            yield data
            count -= len(data)
        yield (count % 4) * '\0'

    def _pack_string(self, s):
        """
        Pack a string.
        
        We first pack the string length, followed by the string padded
        to size 4n.

        """
        # Pack length first.
        n = len(s)
        length = struct.pack('>L', n)

        padding = -n % 4
        data = length + s + (padding * '\0')
        return data


class DapUnpacker(object):
    def __init__(self, xdrdata, var):
        self._buf = xdrdata
        self.var = var
        self._pos = 0

    def getvalue(self):
        if isinstance(self.var, SequenceType):
            out = []
            mark = self._unpack_uint()
            while mark == 1509949440:
                var = self.var
                # Create a structure with the sequence vars:
                self.var = StructureType(name=self.var.name)
                self.var.update(var)
                out.append(self.getvalue())
                self.var = var
                mark = self._unpack_uint()

        elif isinstance(self.var, StructureType):
            out = []
            for child in self.var.walk():
                var = self.var
                self.var = child
                out.append(self.getvalue())
                self.var = var
            out = tuple(out)

        else:
            # Get data length.
            n = 1
            if getattr(self.var, 'shape', False):
                n = self._unpack_uint()
                if self.var.type not in [Url, String]:
                    self._unpack_uint()
                
            # Bytes are treated differently.
            if self.var.type == Byte:
                out = self._unpack_bytes(n)
                out = numpy.array(out, self.var.type.typecode)
            # As are strings...
            elif self.var.type in [Url, String]:
                out = self._unpack_string(n)
                out = numpy.array(out, self.var.type.typecode)
            else:
                i = self._pos
                self._pos = j = i + (n*self.var.type.size)
                dtype = ">%s%s" % (self.var.type.typecode, self.var.type.size)
                out = numpy.fromstring(self._buf[i:j], dtype=dtype)

            if getattr(self.var, 'shape', False):
                out.shape = self.var.shape
            else:   
                out = out[0]

        return out

    def _unpack_uint(self):
        i = self._pos
        self._pos = j = i+4
        data = self._buf[i:j]
        if len(data) < 4:
            raise EOFError
        x = struct.unpack('>L', data)[0]
        try:
            return int(x)
        except OverflowError:
            return x

    def _unpack_bytes(self, count):
        i = self._pos
        self._pos = j = i+count
        out = numpy.fromstring(self._buf[i:j], dtype='B')
        padding = -count % 4
        self._pos += padding
        return out

    def _unpack_string(self, count):
        out = []
        for s in range(count):
            # Unpack string length.
            n = self._unpack_uint()

            i = self._pos
            self._pos = j = i+n
            data = self._buf[i:j]
            out.append(data)

            # Fix cursor position.
            padding = -n % 4
            self._pos += padding
        return out
