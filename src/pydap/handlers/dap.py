"""A handler for remote datasets.

DAP handlers convert from different data formats (NetCDF, eg) to the internal
Pydap model. The Pydap client is just a handler that converts from a remote
dataset to the internal model.

"""

import sys
import pprint
from urlparse import urlsplit, urlunsplit
from urllib import quote

import numpy as np
import requests

from pydap.model import *
from pydap.lib import (
    encode, combine_slices, fix_slice, hyperslab,
    START_OF_SEQUENCE, END_OF_SEQUENCE, walk)
from pydap.handlers.lib import ConstraintExpression, BaseHandler
from pydap.parsers.dds import build_dataset
from pydap.parsers.das import parse_das, add_attributes
from pydap.parsers import parse_ce


BLOCKSIZE = 512


class DAPHandler(BaseHandler):

    """Build a dataset from a DAP base URL."""

    def __init__(self, url):
        # download DDS/DAS
        scheme, netloc, path, query, fragment = urlsplit(url)

        ddsurl = urlunsplit((scheme, netloc, path + '.dds', query, fragment))
        r = requests.get(ddsurl)
        r.raise_for_status()
        dds = r.text.encode('utf-8')

        dasurl = urlunsplit((scheme, netloc, path + '.das', query, fragment))
        r = requests.get(dasurl)
        r.raise_for_status()
        das = r.text.encode('utf-8')

        # build the dataset from the DDS and add attributes from the DAS
        self.dataset = build_dataset(dds)
        add_attributes(self.dataset, parse_das(das))

        # remove any projection from the url, leaving selections
        projection, selection = parse_ce(query)
        url = urlunsplit((scheme, netloc, path, '&'.join(selection), fragment))

        # now add data proxies
        for var in walk(self.dataset, BaseType):
            var.data = BaseProxy(url, var.id, var.descr)
        for var in walk(self.dataset, SequenceType):
            var.data = SequenceProxy(url, var.id, var.descr)

        # apply projections
        for var in projection:
            target = self.dataset
            while var:
                token, index = var.pop(0)
                target = target[token]
                if isinstance(target, BaseType):
                    target.data.slice = fix_slice(index, target.shape) 
                elif isinstance(target, GridType):
                    index = fix_slice(index, target.array.shape)
                    target.array.data.slice = index
                    for s, child in zip(index, target.maps):
                        target[child].data.slice = (s,)
                elif isinstance(target, SequenceType):
                    target.data.slice = index


class BaseProxy(object):

    """A proxy for remote base types.

    This class behaves like a Numpy array, proxying the data from a base type
    on a remote dataset.

    """

    def __init__(self, baseurl, id, descr, slice_=None):
        self.baseurl = baseurl
        self.id = id
        self.dtype = np.dtype(descr[1])
        self.shape = descr[2]
        self.slice = slice_ or tuple(slice(None) for s in self.shape)

    def __repr__(self):
        return 'BaseProxy(%s)' % ', '.join(
            map(repr, [
                self.baseurl, self.id, self.dtype, self.shape, self.slice]))

    def __getitem__(self, index):
        # build download url
        index = combine_slices(self.slice, fix_slice(index, self.shape))
        scheme, netloc, path, query, fragment = urlsplit(self.baseurl)
        url = urlunsplit((
            scheme, netloc, path + '.dods',
            quote(self.id) + hyperslab(index) + '&' + query,
            fragment)).rstrip('&')

        # download and unpack data
        r = requests.get(url)
        r.raise_for_status()
        dds, data = r.content.split('\nData:\n', 1)

        if self.shape:
            # skip size packing
            if self.dtype.char == 'S':
                data = data[4:]
            else:
                data = data[8:]

        # calculate array size
        shape = tuple((s.stop-s.start)/s.step for s in index)
        size = np.prod(shape)

        if self.dtype == np.byte:
            return np.fromstring(data[:size], 'B')
        elif self.dtype.char == 'S':
            out = []
            for word in range(size):
                n = np.fromstring(data[:4], '>I')  # read length
                data = data[4:]
                out.append(data[:n])
                data = data[n + (-n % 4):]
            return np.array(out, 'S')
        else:
            return np.fromstring(data, self.dtype).reshape(shape)

    def __len__(self):
        return self.shape[0]

    def __iter__(self):
        return iter(self[:])

    # Comparisons return a boolean array
    def __eq__(self, other):
        return self[:] == other

    def __ne__(self, other):
        return self[:] != other

    def __ge__(self, other):
        return self[:] >= other

    def __le__(self, other):
        return self[:] <= other

    def __gt__(self, other):
        return self[:] > other

    def __lt__(self, other):
        return self[:] < other


class SequenceProxy(object):

    """A proxy for remote sequences.

    This class behaves like a Numpy structured array, proxying the data from a
    sequence on a remote dataset.

    """

    shape = ()

    def __init__(self, baseurl, id, descr, selection=None, slice_=None):
        self.baseurl = baseurl
        self.id = id
        self.descr = descr
        dtype = descr[1]
        if not isinstance(dtype, list):
            dtype = [dtype]
        self.dtype = np.dtype(dtype)
        self.selection = selection or []
        self.slice = slice_ or (slice(None),)

    def __repr__(self):
        return 'SequenceProxy(%s)' % ', '.join(
            map(repr, [
                self.baseurl, self.id, self.descr, self.selection, self.slice
                ]))

    def __iter__(self):
        scheme, netloc, path, query, fragment = urlsplit(self.baseurl)
        if isinstance(self.descr[1], list):
            id = ','.join('%s.%s' % (self.id, d[0]) for d in self.descr[1])
        else:
            id = self.id
        url = urlunsplit((
            scheme, netloc, path + '.dods',
            quote(id) + hyperslab(self.slice) + '&' +
            '&'.join(self.selection), fragment)).rstrip('&')

        # download and unpack data
        r = requests.get(url, stream=True)
        r.raise_for_status()
        stream = StreamReader(r.iter_content(BLOCKSIZE))

        # strip dds response
        marker = '\nData:\n'
        buf = []
        while ''.join(buf) != marker:
            chunk = stream.read(1)
            if not chunk:
                break
            buf.append(chunk)
            buf = buf[-len(marker):]

        return unpack_sequence(stream, self.descr)

    def __getitem__(self, key):
        out = self.clone()

        # return the data for a children
        if isinstance(key, basestring):
            out.id = '{id}.{child}'.format(id=self.id, child=key)

            def get_child(descr):
                mapping = dict((d[0], d) for d in descr)
                return mapping[key]

            out.descr = apply_to_list(get_child, out.descr)
            dtype = out.descr[1][1]
            out.dtype = np.dtype(dtype)

        # return a new object with requested columns
        elif isinstance(key, list):
            def get_children(descr):
                mapping = dict((d[0], d) for d in descr)
                return [mapping[k] for k in key]
            out.descr = apply_to_list(get_children, out.descr)
            dtype = out.descr[1]
            if not isinstance(dtype, list):
                dtype = [dtype]
            out.dtype = np.dtype(dtype)

        # return a copy with the added constraints
        elif isinstance(key, ConstraintExpression):
            out.selection.extend(str(key).split('&'))

        # slice data
        else:
            if isinstance(key, int):
                key = slice(key, key+1)
            out.slice = combine_slices(self.slice, (key,))

        return out

    def clone(self):
        """Return a lightweight copy of the object."""
        return self.__class__(
            self.baseurl, self.id, self.descr, self.selection[:],
            self.slice[:])

    def __eq__(self, other):
        return ConstraintExpression('%s=%s' % (self.id, encode(other)))

    def __ne__(self, other):
        return ConstraintExpression('%s!=%s' % (self.id, encode(other)))

    def __ge__(self, other):
        return ConstraintExpression('%s>=%s' % (self.id, encode(other)))

    def __le__(self, other):
        return ConstraintExpression('%s<=%s' % (self.id, encode(other)))

    def __gt__(self, other):
        return ConstraintExpression('%s>%s' % (self.id, encode(other)))

    def __lt__(self, other):
        return ConstraintExpression('%s<%s' % (self.id, encode(other)))


class StreamReader(object):

    """Class to allow reading and peeking a `urllib3.HTTPResponse`."""

    def __init__(self, stream):
        self.stream = stream
        self.buf = ''

    def read(self, n):
        """Read and return `n` bytes from the stream."""
        # read n bytes and update buffer
        out = self.peek(n)
        self.buf = self.buf[n:]
        return out

    def peek(self, n):
        """Read and return `n` bytes without consuming them."""
        if n > len(self.buf):
            for chunk in self.stream:
                self.buf += chunk
                if len(self.buf) >= n:
                    break
        return self.buf[:n]


def apply_to_list(func, descr):
    """Apply a function to a list inside a dtype descriptor.

    Return tuple with name, modified dtype, and shape.
    
    """
    name, dtype, shape = descr
    if isinstance(dtype, list):
        dtype = func(dtype)
    else:
        dtype = apply_to_list(func, dtype)
    return name, dtype, shape


def unpack_sequence(buf, descr):
    """Unpack data from a sequence, yielding records."""
    name, dtype, shape = descr

    # is this a sequence or a sequence child?
    sequence = isinstance(dtype, list)

    # if there are no strings and no nested sequences we can
    # unpack record by record easily
    simple = all(isinstance(d, basestring) and 'S' not in d for d in dtype)

    if simple:
        dtype = np.dtype(fix(dtype))
        marker = buf.read(4)
        while marker == START_OF_SEQUENCE:
            rec = np.fromstring(buf.read(dtype.itemsize), dtype=dtype)[0]
            if not sequence:
                rec = rec[0]
            yield rec
            marker = buf.read(4)
    else:
        marker = buf.read(4)
        while marker == START_OF_SEQUENCE:
            rec = unpack_children(buf, descr)
            if not sequence:
                rec = rec[0]
            else:
                rec = tuple(rec)
            yield rec
            marker = buf.read(4)


def unpack_children(buf, descr):
    """Unpack children from a structure, returning their data."""
    name, dtype, shape = descr

    out = []
    if not isinstance(dtype, list):
        dtype = [dtype]

    for descr in dtype:
        name, d, shape = descr
        d = np.dtype(fix(d))

        # sequences and other structures
        if d.char == 'V':
            if buf.peek(4) in [START_OF_SEQUENCE, END_OF_SEQUENCE]:
                rows = unpack_sequence(buf, descr)
                #out.append(ListData(name, d.names, rows))
                out.append(np.array(
                    np.rec.fromrecords(list(rows), names=d.names)))
            else:
                out.append(tuple(unpack_children(buf, descr)))

        # special types: strings and bytes
        elif d.char == 'S':
            n = np.fromstring(buf.read(4), '>I')[0]
            out.append(buf.read(n))
            buf.read(-n % 4)
        elif d.char == 'B':
            data = np.fromstring(buf.read(1), d)[0]
            buf.read(3)
            out.append(data)

        # usual array data
        else:
            if shape:
                n = np.fromstring(buf.read(4), '>I')[0]
                buf.read(4)
                data = np.fromstring(buf.read(d.itemsize*n), d).reshape(shape)
            else:
                data = np.fromstring(buf.read(d.itemsize), d)[0]
            out.append(data)
    return out


def unpack_data(xdrdata, dataset):
    """Unpack a string of encoded data, returning data as lists."""
    return unpack_children(StreamReader(iter(xdrdata)), dataset.descr)


def fix(descr):
    """Fix descriptor for Numpy.

    Numpy dtypes must be list of tuples, but we use single tuples to
    differentiate children from sequences with only one child, ie,
    ``sequence['foo']`` is the children ``foo`` from ``sequence``, while 
    ``sequence[['foo']]`` is a sequence with only one child.
    
    Return the descriptor as a list so Numpy can understand it.

    """
    if isinstance(descr, tuple):
        name, dtype, shape = descr
        return [(name, fix(dtype), shape)]
    else:
        return descr


def dump():
    """Unpack dods response into lists.

    Return pretty-printed data.

    """
    dods = sys.stdin.read()
    dds, xdrdata = dods.split('\nData:\n', 1)
    dataset = build_dataset(dds)
    data = unpack_data(xdrdata, dataset)

    pprint.pprint(data)
