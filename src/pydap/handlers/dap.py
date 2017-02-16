"""A handler for remote datasets.

DAP handlers convert from different data formats (NetCDF, eg) to the internal
Pydap model. The Pydap client is just a handler that converts from a remote
dataset to the internal model.

"""

import io
import sys
import pprint
import copy
import re
from itertools import chain

# handlers should be set by the application
# http://docs.python.org/2/howto/logging.html#configuring-logging-for-a-library
import logging
import numpy as np
from six.moves.urllib.parse import urlsplit, urlunsplit, quote
from six import text_type, string_types, next

from pydap.model import (BaseType,
                         SequenceType, StructureType,
                         GridType)
from pydap.net import GET, raise_for_status
from pydap.lib import (
    encode, combine_slices, fix_slice, hyperslab,
    START_OF_SEQUENCE, walk)
from pydap.handlers.lib import ConstraintExpression, BaseHandler, IterData
from pydap.parsers.dds import build_dataset
from pydap.parsers.das import parse_das, add_attributes
from pydap.parsers import parse_ce
logger = logging.getLogger('pydap')
logger.addHandler(logging.NullHandler())


BLOCKSIZE = 512


class DAPHandler(BaseHandler):

    """Build a dataset from a DAP base URL."""

    def __init__(self, url, application=None, session=None, output_grid=True):
        # download DDS/DAS
        scheme, netloc, path, query, fragment = urlsplit(url)

        ddsurl = urlunsplit((scheme, netloc, path + '.dds', query, fragment))
        r = GET(ddsurl, application, session)
        raise_for_status(r)
        dds = r.text

        dasurl = urlunsplit((scheme, netloc, path + '.das', query, fragment))
        r = GET(dasurl, application, session)
        raise_for_status(r)
        das = r.text

        # build the dataset from the DDS and add attributes from the DAS
        self.dataset = build_dataset(dds)
        add_attributes(self.dataset, parse_das(das))

        # remove any projection from the url, leaving selections
        projection, selection = parse_ce(query)
        url = urlunsplit((scheme, netloc, path, '&'.join(selection), fragment))

        # now add data proxies
        for var in walk(self.dataset, BaseType):
            var.data = BaseProxy(url, var.id, var.dtype, var.shape,
                                 application=application,
                                 session=session)
        for var in walk(self.dataset, SequenceType):
            template = copy.copy(var)
            var.data = SequenceProxy(url, template, application=application,
                                     session=session)

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

        # retrieve only main variable for grid types:
        for var in walk(self.dataset, GridType):
            var.set_output_grid(output_grid)


class BaseProxy(object):

    """A proxy for remote base types.

    This class behaves like a Numpy array, proxying the data from a base type
    on a remote dataset.

    """

    def __init__(self, baseurl, id, dtype, shape, slice_=None,
                 application=None, session=None):
        self.baseurl = baseurl
        self.id = id
        self.dtype = dtype
        self.shape = shape
        self.slice = slice_ or tuple(slice(None) for s in self.shape)
        self.application = application
        self.session = session

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
        r = GET(url, self.application, self.session)
        raise_for_status(r)
        dds, data = r.body.split(b'\nData:\n', 1)
        dds = dds.decode(r.content_encoding or 'ascii')

        if self.shape:
            # skip size packing
            if self.dtype.char in 'SU':
                data = data[4:]
            else:
                data = data[8:]

        # calculate array size
        shape = tuple(
            int(np.ceil((s.stop-s.start)/float(s.step))) for s in index)
        size = int(np.prod(shape))

        if self.dtype == np.byte:
            return np.fromstring(data[:size], 'B').reshape(shape)
        elif self.dtype.char in 'SU':
            out = []
            for word in range(size):
                n = np.asscalar(np.fromstring(data[:4], '>I'))  # read length
                data = data[4:]
                out.append(data[:n])
                data = data[n + (-n % 4):]
            return np.array([text_type(x.decode('ascii'))
                             for x in out], 'S').reshape(shape)
        else:
            try:
                return np.fromstring(data, self.dtype).reshape(shape)
            except ValueError as e:
                if str(e) == 'total size of new array must be unchanged':
                    # server-side failure.
                    # it is expected that the user should be mindful of this:
                    raise RuntimeError(
                                ('variable {0} could not be properly '
                                 'retrieved. To avoid this '
                                 'error consider using open_url(..., '
                                 'output_grid=False).').format(quote(self.id)))
                else:
                    raise

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

    def __init__(self, baseurl, template, selection=None, slice_=None,
                 application=None, session=None):
        self.baseurl = baseurl
        self.template = template
        self.selection = selection or []
        self.slice = slice_ or (slice(None),)
        self.application = application
        self.session = session

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
        return self.__class__(self.baseurl, self.template, self.selection[:],
                              self.slice[:], self.application)

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
        r = GET(self.url, self.application, self.session)
        raise_for_status(r)

        i = r.app_iter
        if not hasattr(i, '__next__'):
            i = iter(i)

        # Fast forward past the DDS header
        # the pattern could span chunk boundaries though so make sure to check
        previous_chunk = b''
        this_chunk = b''
        pattern = b'Data:\n'
        for this_chunk in i:
            m = re.search(pattern, previous_chunk + this_chunk)
            if m:
                break
        if not m:
            raise ValueError("Could not find data segment in response from {}"
                             .format(self.url))

        last_chunk = (previous_chunk + this_chunk)[m.end():]

        # Then construct a stream consisting of everything from
        # 'Data:\n' to the end of the chunk + the rest of the stream
        def stream_start():
            yield last_chunk

        stream = StreamReader(chain(stream_start(), i))

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
        self.buf = bytearray()

    def read(self, n):
        """Read and return `n` bytes."""
        while len(self.buf) < n:
            bytes_read = next(self.stream)
            self.buf.extend(bytes_read)

        out = bytes(self.buf[:n])
        self.buf = self.buf[n:]
        return out


def unpack_sequence(stream, template):
    """Unpack data from a sequence, yielding records."""
    # is this a sequence or a base type?
    sequence = isinstance(template, SequenceType)

    # if there are no children, we use the template as the only column
    cols = list(template.children()) or [template]

    # if there are no strings and no nested sequences we can unpack record by
    # record easily
    simple = all(isinstance(c, BaseType) and c.dtype.char not in "SU"
                 for c in cols)

    if simple:
        dtype = np.dtype([("", c.dtype, c.shape) for c in cols])
        marker = stream.read(4)
        while marker == START_OF_SEQUENCE:
            rec = np.fromstring(stream.read(dtype.itemsize), dtype=dtype)[0]
            if not sequence:
                rec = rec[0]
            yield rec
            marker = stream.read(4)
    else:
        marker = stream.read(4)
        while marker == START_OF_SEQUENCE:
            rec = unpack_children(stream, template)
            if not sequence:
                rec = rec[0]
            else:
                rec = tuple(rec)
            yield rec
            marker = stream.read(4)


def unpack_children(stream, template):
    """Unpack children from a structure, returning their data."""
    cols = list(template.children()) or [template]

    out = []
    for col in cols:
        # sequences and other structures
        if isinstance(col, SequenceType):
            out.append(IterData(list(unpack_sequence(stream, col)), col))
        elif isinstance(col, StructureType):
            out.append(tuple(unpack_children(stream, col)))

        # unpack arrays
        elif col.shape:
            n = np.fromstring(stream.read(4), ">I")[0]
            count = col.dtype.itemsize * n
            if col.dtype.char in "SU":
                data = []
                for _ in range(n):
                    k = np.fromstring(stream.read(4), ">I")[0]
                    data.append(stream.read(k))
                    stream.read(-k % 4)
                out.append(np.array(text_type(data), dtype='S'))

            else:
                stream.read(4)  # read additional length
                out.append(
                    np.fromstring(
                        stream.read(count), col.dtype).reshape(col.shape))
                if col.dtype.char == "B":
                    stream.read(-n % 4)

        # special types: strings and bytes
        elif col.dtype.char in 'SU':
            n = np.fromstring(stream.read(4), '>I')[0]
            out.append(stream.read(n).decode('ascii'))
            stream.read(-n % 4)
        elif col.dtype.char == 'B':
            data = np.fromstring(stream.read(1), col.dtype)[0]
            stream.read(3)
            out.append(data)

        # usual data
        else:
            out.append(
                np.fromstring(stream.read(col.dtype.itemsize), col.dtype)[0])

    return out


def unpack_data(xdr_stream, dataset):
    """Unpack a string of encoded data, returning data as lists."""
    return unpack_children(xdr_stream, dataset)


def dump():  # pragma: no cover
    """Unpack dods response into lists.

    Return pretty-printed data.

    """
    dods = sys.stdin.read()
    dds, xdrdata = dods.split(b'\nData:\n', 1)
    xdr_stream = io.BytesIO(xdrdata)
    dds = dds.decode('ascii')
    dataset = build_dataset(dds)
    data = unpack_data(xdr_stream, dataset)

    pprint.pprint(data)
