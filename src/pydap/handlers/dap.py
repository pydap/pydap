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
from six import text_type, string_types

from pydap.model import (BaseType,
                         SequenceType, StructureType,
                         GridType)
from ..net import GET, raise_for_status
from ..lib import (
    encode, combine_slices, fix_slice, hyperslab,
    START_OF_SEQUENCE, walk, StreamReader, BytesReader,
    DEFAULT_TIMEOUT, DAP2_ARRAY_LENGTH_NUMPY_TYPE)
from .lib import ConstraintExpression, BaseHandler, IterData
from ..parsers.dds import build_dataset
from ..parsers.das import parse_das, add_attributes
from ..parsers import parse_ce
from ..responses.dods import DAP2_response_dtypemap
logger = logging.getLogger('pydap')
logger.addHandler(logging.NullHandler())


BLOCKSIZE = 512


class DAPHandler(BaseHandler):

    """Build a dataset from a DAP base URL."""

    def __init__(self, url, application=None, session=None, output_grid=True,
                 timeout=DEFAULT_TIMEOUT):
        # download DDS/DAS
        scheme, netloc, path, query, fragment = urlsplit(url)

        ddsurl = urlunsplit((scheme, netloc, path + '.dds', query, fragment))
        r = GET(ddsurl, application, session, timeout=timeout)
        raise_for_status(r)
        if not r.charset:
            r.charset = 'ascii'
        dds = r.text

        dasurl = urlunsplit((scheme, netloc, path + '.das', query, fragment))
        r = GET(dasurl, application, session, timeout=timeout)
        raise_for_status(r)
        if not r.charset:
            r.charset = 'ascii'
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
                 application=None, session=None, timeout=DEFAULT_TIMEOUT):
        self.baseurl = baseurl
        self.id = id
        self.dtype = dtype
        self.shape = shape
        self.slice = slice_ or tuple(slice(None) for s in self.shape)
        self.application = application
        self.session = session
        self.timeout = timeout

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
        r = GET(url, self.application, self.session, timeout=self.timeout)
        raise_for_status(r)
        dds, data = r.body.split(b'\nData:\n', 1)
        dds = dds.decode(r.content_encoding or 'ascii')

        # Parse received dataset:
        dataset = build_dataset(dds)
        dataset.data = unpack_data(BytesReader(data), dataset)
        return dataset[self.id].data

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
                 application=None, session=None, timeout=DEFAULT_TIMEOUT):
        self.baseurl = baseurl
        self.template = template
        self.selection = selection or []
        self.slice = slice_ or (slice(None),)
        self.application = application
        self.session = session
        self.timeout = timeout

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
            out.template._visible_keys = key

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
        r = GET(self.url, self.application, self.session, timeout=self.timeout)
        raise_for_status(r)

        i = r.app_iter
        if not hasattr(i, '__next__'):
            i = iter(i)

        # Fast forward past the DDS header
        # the pattern could span chunk boundaries though so make sure to check
        pattern = b'Data:\n'
        last_chunk = find_pattern_in_string_iter(pattern, i)

        if last_chunk is None:
            raise ValueError("Could not find data segment in response from {}"
                             .format(self.url))

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
        else:
            out.extend(convert_stream_to_list(stream, col.dtype, col.shape,
                                              col.id))
    return out


def convert_stream_to_list(stream, parser_dtype, shape, id):
    out = []
    response_dtype = DAP2_response_dtypemap(parser_dtype)
    if shape:
        n = np.fromstring(stream.read(4), DAP2_ARRAY_LENGTH_NUMPY_TYPE)[0]
        count = response_dtype.itemsize * n
        if response_dtype.char in 'S':
            # Consider on 'S' and not 'SU' because
            # response_dtype.char should never be
            data = []
            for _ in range(n):
                k = np.fromstring(stream.read(4),
                                  DAP2_ARRAY_LENGTH_NUMPY_TYPE)[0]
                data.append(stream.read(k))
                stream.read(-k % 4)
            out.append(np.array([text_type(x.decode('ascii'))
                                 for x in data], 'S').reshape(shape))
        else:
            stream.read(4)  # read additional length
            try:
                out.append(
                    np.fromstring(
                        stream.read(count), response_dtype)
                    .astype(parser_dtype).reshape(shape))
            except ValueError as e:
                if str(e) == 'total size of new array must be unchanged':
                    # server-side failure.
                    # it is expected that the user should be mindful of this:
                    raise RuntimeError(
                                ('variable {0} could not be properly '
                                 'retrieved. To avoid this '
                                 'error consider using open_url(..., '
                                 'output_grid=False).').format(quote(id)))
                else:
                    raise
            if response_dtype.char == "B":
                # Unsigned Byte type is packed to multiples of 4 bytes:
                stream.read(-n % 4)

    # special types: strings and bytes
    elif response_dtype.char in 'S':
        # Consider on 'S' and not 'SU' because
        # response_dtype.char should never be
        # 'U'
        k = np.fromstring(stream.read(4), DAP2_ARRAY_LENGTH_NUMPY_TYPE)[0]
        out.append(text_type(stream.read(k).decode('ascii')))
        stream.read(-k % 4)
    # usual data
    else:
        out.append(
            np.fromstring(stream.read(response_dtype.itemsize), response_dtype)
            .astype(parser_dtype)[0])
        if response_dtype.char == "B":
            # Unsigned Byte type is packed to multiples of 4 bytes:
            stream.read(3)
    return out


def unpack_data(xdr_stream, dataset):
    """Unpack a string of encoded data, returning data as lists."""
    return unpack_children(xdr_stream, dataset)


def find_pattern_in_string_iter(pattern, i):
    last_chunk = b''
    length = len(pattern)
    for this_chunk in i:
        last_chunk += this_chunk
        m = re.search(pattern, last_chunk)
        if m:
            return last_chunk[m.end():]
        last_chunk = last_chunk[-length:]


def dump():  # pragma: no cover
    """Unpack dods response into lists.

    Return pretty-printed data.

    """
    dods = sys.stdin.read()
    dds, xdrdata = dods.split(b'\nData:\n', 1)
    dataset = build_dataset(dds)
    xdr_stream = io.BytesIO(xdrdata)
    data = unpack_data(xdr_stream, dataset)
    data = dataset.data

    pprint.pprint(data)
