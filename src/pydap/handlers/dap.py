"""A handler for remote datasets.

DAP handlers convert from different data formats (NetCDF, eg) to the internal
Pydap model. The Pydap client is just a handler that converts from a remote
dataset to the internal model.

"""

import sys
import pprint
import copy

# handlers should be set by the application
# http://docs.python.org/2/howto/logging.html#configuring-logging-for-a-library
import logging
logger = logging.getLogger('pydap')
if sys.version_info >= (2, 7):
    logger.addHandler(logging.NullHandler())

import numpy as np
import requests
from six.moves.urllib.parse import urlsplit, urlunsplit, quote
from six import string_types, next

from pydap.model import *
from pydap.lib import (
    encode, combine_slices, fix_slice, hyperslab,
    START_OF_SEQUENCE, END_OF_SEQUENCE, walk)
from pydap.handlers.lib import ConstraintExpression, BaseHandler, IterData
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
            var.data = BaseProxy(url, var.id, var.dtype, var.shape)
        for var in walk(self.dataset, SequenceType):
            template = copy.copy(var)
            var.data = SequenceProxy(url, template)

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

    def __init__(self, baseurl, id, dtype, shape, slice_=None):
        self.baseurl = baseurl
        self.id = id
        self.dtype = dtype
        self.shape = shape
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
        logger.info("Fetching URL: %s" % url)
        r = requests.get(url)
        r.raise_for_status()
        dds, data = r.content.split(b'\nData:\n', 1)

        if self.shape:
            # skip size packing
            if self.dtype.char == 'S':
                data = data[4:]
            else:
                data = data[8:]

        # calculate array size
        shape = tuple(
            int(np.ceil((s.stop-s.start)/float(s.step))) for s in index)
        size = int(np.prod(shape))

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
    sequence on a remote dataset. The data is streamed from the dataset, 
    meaning it can be treated one record at a time before the whole data is
    downloaded.

    """

    shape = ()

    def __init__(self, baseurl, template, selection=None, slice_=None):
        self.baseurl = baseurl
        self.template = template
        self.selection = selection or []
        self.slice = slice_ or (slice(None),)

        # this variable is true when only a subset of the children are selected
        self.sub_children = False

    @property
    def dtype(self):
        return self.template.dtype

    def __repr__(self):
        return 'SequenceProxy(%s)' % ', '.join(
            map(repr, [
                self.baseurl, self.template, self.selection, self.slice]))

    def __copy__(self):
        """Return a lightweight copy of the object."""
        return self.__class__(
            self.baseurl, self.template, self.selection[:], self.slice[:])

    def __getitem__(self, key):
        """Return a new object representing a subset of the data."""
        out = copy.copy(self)

        # return the data for a children
        if isinstance(key, string_types):
            out.template = out.template[key]

        # return a new object with requested columns
        elif isinstance(key, list):
            out.sub_children = True
            out.template._keys = key

        # return a copy with the added constraints
        elif isinstance(key, ConstraintExpression):
            out.selection.extend(str(key).split('&'))

        # slice data
        else:
            if isinstance(key, int):
                key = slice(key, key+1)
            out.slice = combine_slices(self.slice, (key,))

        return out

    @property
    def url(self):
        """Return url from where data is fetched."""
        scheme, netloc, path, query, fragment = urlsplit(self.baseurl)
        url = urlunsplit((
            scheme, netloc, path + '.dods',
            self.id + hyperslab(self.slice) + '&' +
            '&'.join(self.selection), fragment)).rstrip('&')

        return url

    @property
    def id(self):
        """Return the id of this sequence."""
        if self.sub_children:
            id_ = ','.join(
                quote(child.id) for child in self.template.children())
        else:
            id_ = quote(self.template.id)
        return id_

    def __iter__(self):
        # download and unpack data
        r = requests.get(self.url, stream=True)
        r.raise_for_status()
        stream = StreamReader(r.iter_content(BLOCKSIZE))

        # strip dds response
        marker = b'\nData:\n'
        buf = []
        while ''.join(buf) != marker:
            chunk = stream.read(1)
            buf.append(chunk)
            buf = buf[-len(marker):]

        return unpack_sequence(stream, self.template)

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

    """Class to allow reading a `urllib3.HTTPResponse`."""

    def __init__(self, stream):
        self.stream = stream
        self.buf = ''

    def read(self, n):
        """Read and return `n` bytes."""
        while len(self.buf) < n:
            self.buf += next(self.stream)
        out = self.buf[:n]
        self.buf = self.buf[n:]
        return out


def unpack_sequence(buf, template):
    """Unpack data from a sequence, yielding records."""
    # is this a sequence or a base type?
    sequence = isinstance(template, SequenceType)

    # if there are no children, we use the template as the only column
    cols = list(template.children()) or [template]

    # if there are no strings and no nested sequences we can unpack record by
    # record easily
    simple = all(isinstance(c, BaseType) and c.dtype.char != "S" for c in cols)

    if simple:
        dtype = np.dtype([("", c.dtype, c.shape) for c in cols])
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
            rec = unpack_children(buf, template)
            if not sequence:
                rec = rec[0]
            else:
                rec = tuple(rec)
            yield rec
            marker = buf.read(4)


def unpack_children(buf, template):
    """Unpack children from a structure, returning their data."""
    cols = list(template.children()) or [template]

    out = []
    for col in cols:
        # sequences and other structures
        if isinstance(col, SequenceType):
            out.append(IterData(list(unpack_sequence(buf, col)), col))
        elif isinstance(col, StructureType):
            out.append(tuple(unpack_children(buf, col)))

        # unpack arrays
        elif col.shape:
            n = np.fromstring(buf.read(4), ">I")[0]
            count = col.dtype.itemsize * n
            if col.dtype.char != "S":
                buf.read(4)  # read additional length
                out.append(
                    np.fromstring(
                        buf.read(count), col.dtype).reshape(col.shape))
                if col.dtype.char == "B":
                    buf.read(-n % 4)
            else:
                data = []
                for _ in range(n):
                    k = np.fromstring(buf.read(4), ">I")[0]
                    data.append(buf.read(k))
                    buf.read(-k % 4)
                out.append(np.array(data))

        # special types: strings and bytes
        elif col.dtype.char == 'S':
            n = np.fromstring(buf.read(4), '>I')[0]
            out.append(buf.read(n))
            buf.read(-n % 4)
        elif col.dtype.char == 'B':
            data = np.fromstring(buf.read(1), col.dtype)[0]
            buf.read(3)
            out.append(data)

        # usual data
        else:
            out.append(
                np.fromstring(buf.read(col.dtype.itemsize), col.dtype)[0])

    return out


def unpack_data(xdrdata, dataset):
    """Unpack a string of encoded data, returning data as lists."""
    return unpack_children(StreamReader(iter(xdrdata)), dataset)


def dump():
    """Unpack dods response into lists.

    Return pretty-printed data.

    """
    dods = sys.stdin.read()
    dds, xdrdata = dods.split(b'\nData:\n', 1)
    dataset = build_dataset(dds)
    data = unpack_data(xdrdata, dataset)

    pprint.pprint(data)
