"""A handler for remote datasets.

DAP handlers convert from different data formats (NetCDF, eg) to the internal
pydap model. The pydap client is just a handler that converts from a remote
dataset to the internal model.

"""

import copy
import gzip
import io

# handlers should be set by the application
# http://docs.python.org/2/howto/logging.html#configuring-logging-for-a-library
import logging
import pprint
import re
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor
from io import BufferedReader, BytesIO
from itertools import chain

import numpy
import requests
from requests.utils import urlparse, urlunparse
from webob.response import Response as webob_Response

from pydap.handlers.lib import BaseHandler, ConstraintExpression, IterData
from pydap.lib import (
    DAP2_ARRAY_LENGTH_NUMPY_TYPE,
    DEFAULT_TIMEOUT,
    START_OF_SEQUENCE,
    BytesReader,
    StreamReader,
    _quote,
    combine_slices,
    encode,
    fix_slice,
    hyperslab,
    walk,
)
from pydap.model import BaseType, GridType, SequenceType, StructureType
from pydap.net import GET
from pydap.parsers import parse_ce
from pydap.parsers.das import add_attributes, parse_das
from pydap.parsers.dds import dds_to_dataset
from pydap.parsers.dmr import dmr_to_dataset
from pydap.responses.dods import DAP2_response_dtypemap

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

BLOCKSIZE = 512


class DAPHandler(BaseHandler):
    """Build a dataset from a DAP base URL."""

    def __init__(
        self,
        url,
        application=None,
        session=None,
        output_grid=True,
        timeout=DEFAULT_TIMEOUT,
        verify=True,
        user_charset="ascii",
        protocol=None,
        get_kwargs=None,
    ):

        self.application = application
        self.session = session
        self.output_grid = output_grid
        self.timeout = timeout
        self.verify = verify
        self.user_charset = user_charset
        self.url = url

        # urlparse returns an additional var compared to
        # urlsplit: `param`. Will toss it.
        scheme, netloc, path, _, query, fragment = urlparse(self.url)
        self.scheme = scheme
        self.netloc = netloc
        self.path = path
        self.query = query
        self.fragment = fragment

        if protocol:
            if protocol not in ["dap2", "dap4"]:
                raise TypeError("protocol must be one of `dap2` or `dap4")
            self.protocol = protocol
            if self.scheme == protocol:
                # the other alternative occurs during testing
                # the server - only when protocol and scheme match,
                # should pydap change the scheme provided by user
                self.scheme = "http"
        else:
            self.protocol = self.determine_protocol()
        self.get_kwargs = get_kwargs or {}

        self.projection, self.selection = parse_ce(self.query, self.protocol)
        arg = (
            self.scheme,
            self.netloc,
            self.path,
            "",
            "&".join(self.selection),
            self.fragment,
        )
        self.base_url = urlunparse(arg)
        self.make_dataset()
        self.add_proxies()

    def determine_protocol(self):
        # determines the opendap protocol from url scheme, query, or extension
        if self.application:
            # server - only dap2 for now.
            return "dap2"
        if self.scheme not in ["http", "https"]:
            if self.scheme in ["dap4", "dap2"]:
                protocol = self.scheme
                self.scheme = "http"  # revert to http
                return protocol
            else:
                raise TypeError(
                    "Invalid URL scheme - acceptable options are"
                    "`dap2`, `dap4`. `https` and `http`",
                )
        if self.query[:4] == "dap4":
            return "dap4"
        else:
            warnings.warn(
                "PyDAP was unable to determine the DAP protocol defaulting "
                "to DAP2. DAP2 is consider legacy and may result in slower "
                "responses. \nConsider replacing `http` in your `url` with "
                "either `dap2` or `dap4` to specify the DAP protocol (e.g. "
                "`dap2://<data_url>` or `dap4://<data_url>`).  For more \n"
                "information, go to https://www.opendap.org/faq-page."
            )
            return "dap2"

    def make_dataset(
        self,
    ):
        if self.protocol == "dap4":
            self.dataset_from_dap4()
        else:
            self.dataset_from_dap2()
            self.attach_das()

    def dataset_from_dap4(self):
        if not self.path.endswith(".dmr"):
            path = self.path + ".dmr"
        else:
            path = self.path
        dmr_url = urlunparse(
            (
                self.scheme,
                self.netloc,
                path,
                "",
                _quote(self.query),
                self.fragment,
            )
        )
        r = GET(
            dmr_url,
            self.application,
            self.session,
            timeout=self.timeout,
            verify=self.verify,
            get_kwargs=self.get_kwargs,
        )
        dmr = safe_charset_text(r, self.user_charset)
        self.dataset = dmr_to_dataset(dmr)

    def dataset_from_dap2(self):
        # escape for certain characters
        dds_url = urlunparse(
            (
                self.scheme,
                self.netloc,
                self.path + ".dds",
                "",
                _quote(self.query),
                self.fragment,
            )
        )
        r = GET(
            dds_url,
            self.application,
            self.session,
            timeout=self.timeout,
            verify=self.verify,
            get_kwargs=self.get_kwargs,
        )

        dds = safe_charset_text(r, self.user_charset)
        self.dataset = dds_to_dataset(dds)

    def attach_das(self):
        # Also pull the DAS and add additional attributes
        das_url = urlunparse(
            (
                self.scheme,
                self.netloc,
                self.path + ".das",
                "",
                self.query,
                self.fragment,
            )
        )
        r = GET(
            das_url,
            self.application,
            self.session,
            timeout=self.timeout,
            verify=self.verify,
            get_kwargs=self.get_kwargs,
        )
        das = safe_charset_text(r, self.user_charset)
        add_attributes(self.dataset, parse_das(das))

    def add_proxies(self):
        if self.protocol == "dap4":
            self.add_dap4_proxies()
        else:
            self.add_dap2_proxies()

    def add_dap4_proxies(self):
        # remove any projection from the base_url, leaving selections
        for var in walk(self.dataset, BaseType):
            if var.path is not None:
                var_name = var.path + "/" + var.name
            else:
                var_name = var.name
            var.data = BaseProxyDap4(
                self.base_url,
                var_name,
                var.dtype,
                var.shape,
                application=self.application,
                session=self.session,
                timeout=self.timeout,
                verify=self.verify,
                get_kwargs={**self.get_kwargs, "stream": True},
            )

        # apply projections to BaseType only
        # CE for sequences and structs
        # are not ready (see https://github.com/pydap/pydap/issues/314)
        for var in self.projection:
            target = self.dataset
            while var:
                token, index = var.pop(0)
                target = target[token]
                if isinstance(target, BaseType):
                    target.data.slice = fix_slice(index, target.shape)

    def add_dap2_proxies(self):
        # now add data proxies
        for var in walk(self.dataset, BaseType):
            var.data = BaseProxyDap2(
                self.base_url,
                var.id,
                var.dtype,
                var.shape,
                application=self.application,
                session=self.session,
                timeout=self.timeout,
                verify=self.verify,
                get_kwargs={**self.get_kwargs, "stream": True},
            )
        for var in walk(self.dataset, SequenceType):
            template = copy.copy(var)
            var.data = SequenceProxy(
                self.base_url,
                template,
                selection=self.selection,
                application=self.application,
                session=self.session,
                timeout=self.timeout,
                verify=self.verify,
                get_kwargs={**self.get_kwargs, "stream": True},
            )

        # apply projections
        for var in self.projection:
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
            var.set_output_grid(self.output_grid)


def get_charset(r, user_charset):
    charset = r.charset
    if not charset:
        charset = user_charset
    return charset


def safe_charset_text(r, user_charset):
    if isinstance(r, webob_Response):
        if r.content_encoding == "gzip":
            return (
                gzip.GzipFile(fileobj=BytesIO(r.body))
                .read()
                .decode(get_charset(r, user_charset))
            )
        else:
            r.charset = get_charset(r, user_charset)
    return r.text


def safe_dds_and_data(r, user_charset):
    """
    Takes the raw response of a dap2 request and splits it into the dds and data.
    If the response is gzipped, it is decompressed first.
    """
    dds, data = None, None  # initialize
    if isinstance(r, webob_Response):
        if r.content_encoding == "gzip":
            raw = gzip.GzipFile(fileobj=BytesIO(r.body)).read()
        else:
            raw = r.body
        _dds, data = raw.split(b"\nData:\n", 1)
        dds = _dds.decode(get_charset(r, user_charset))
    elif isinstance(r, requests.Response):
        raw = r.content
        _dds, data = raw.split(b"\nData:\n", 1)
        dds = _dds.decode(user_charset)
    return dds, data


class BaseProxyDap2(object):
    """A proxy for remote base types.

    This class behaves like a Numpy array, proxying the data from a base type
    on a remote dataset.
    """

    def __init__(
        self,
        baseurl,
        id,
        dtype,
        shape,
        slice_=None,
        application=None,
        session=None,
        timeout=DEFAULT_TIMEOUT,
        verify=True,
        user_charset="ascii",
        get_kwargs=None,
    ):
        self.baseurl = baseurl
        self.id = id
        self.dtype = dtype
        self.shape = shape
        self.slice = slice_ or tuple(slice(None) for s in self.shape)
        self.application = application
        self.session = session
        self.timeout = timeout
        self.verify = verify
        self.user_charset = user_charset
        self.get_kwargs = get_kwargs or {}

    def __repr__(self):
        return "BaseProxy(%s)" % ", ".join(
            map(repr, [self.baseurl, self.id, self.dtype, self.shape, self.slice])
        )

    def __getitem__(self, index):
        # build download url

        index = combine_slices(self.slice, fix_slice(index, self.shape))
        scheme, netloc, path, params, query, fragment = urlparse(self.baseurl)
        url = urlunparse(
            (
                scheme,
                netloc,
                path + ".dods",
                "",
                self.id + hyperslab(index) + "&" + _quote(query),
                fragment,
            )
        ).rstrip("&")

        # download and unpack data
        logger.info("Fetching URL: %s" % url)
        r = GET(
            url,
            self.application,
            self.session,
            timeout=self.timeout,
            verify=self.verify,
            get_kwargs=self.get_kwargs,
        )

        dds, data = safe_dds_and_data(r, self.user_charset)

        # Parse received dataset:
        dataset = dds_to_dataset(dds)
        dataset.data = unpack_dap2_data(BytesReader(data), dataset)
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


class BaseProxyDap4(BaseProxyDap2):

    def __init__(
        self,
        baseurl,
        id,
        dtype,
        shape,
        slice_=None,
        application=None,
        session=None,
        timeout=DEFAULT_TIMEOUT,
        verify=True,
        user_charset="ascii",
        get_kwargs=None,
    ):
        self.baseurl = baseurl
        self.id = id
        self.dtype = dtype
        self.shape = shape
        self.slice = slice_ or tuple(slice(None) for s in self.shape)
        self.application = application
        self.session = session
        self.timeout = timeout
        self.verify = verify
        self.user_charset = user_charset
        self.get_kwargs = get_kwargs or {}

    def __repr__(self):
        return "Dap4BaseProxy(%s)" % ", ".join(
            map(repr, [self.baseurl, self.id, self.dtype, self.shape, self.slice])
        )

    def __getitem__(self, index):
        # build download url
        index = combine_slices(self.slice, fix_slice(index, self.shape))
        scheme, netloc, path, _, query, fragment = urlparse(self.baseurl)
        ce = "dap4.ce=" + self.id + hyperslab(index)
        url = urlunparse((scheme, netloc, path + ".dap", "", ce, fragment)).rstrip("&")

        # download and unpack data
        logger.info("Fetching URL: %s" % url)

        r = GET(
            url,
            self.application,
            self.session,
            timeout=self.timeout,
            verify=self.verify,
            get_kwargs=self.get_kwargs,
        )

        dataset = UNPACKDAP4DATA(r, self.user_charset).dataset
        self.checksum = dataset[self.id].attributes["checksum"]
        self.data = dataset[self.id].data
        return self.data


class SequenceProxy(object):
    """A proxy for remote sequences.

    This class behaves like a Numpy structured array, proxying the data from a
    sequence on a remote dataset. The data is streamed from the dataset,
    meaning it can be treated one record at a time before the whole data is
    downloaded.

    """

    shape = ()

    def __init__(
        self,
        baseurl,
        template,
        selection=None,
        slice_=None,
        application=None,
        session=None,
        timeout=DEFAULT_TIMEOUT,
        verify=True,
        get_kwargs=None,
    ):
        self.baseurl = baseurl
        self.template = template
        self.selection = selection or []
        self.slice = slice_ or (slice(None),)
        self.application = application
        self.session = session
        self.timeout = timeout
        self.verify = verify

        # this variable is true when only a subset of the children are selected
        self.sub_children = False
        self.get_kwargs = get_kwargs or {}

    @property
    def dtype(self):
        return self.template.dtype

    def __repr__(self):
        return "SequenceProxy(%s)" % ", ".join(
            map(repr, [self.baseurl, self.template, self.selection, self.slice])
        )

    def __copy__(self):
        """Return a lightweight copy of the object."""
        return self.__class__(
            self.baseurl,
            self.template,
            self.selection[:],
            self.slice[:],
            self.application,
        )

    def __getitem__(self, key):
        """Return a new object representing a subset of the data."""
        out = copy.copy(self)

        # return the data for a children
        if isinstance(key, str):
            out.template = out.template[key]

        # return a new object with requested columns
        elif isinstance(key, list):
            out.sub_children = True
            out.template._visible_keys = key

        # return a copy with the added constraints
        elif isinstance(key, ConstraintExpression):
            out.selection.extend(str(key).split("&"))

        # slice data
        else:
            if isinstance(key, int):
                key = slice(key, key + 1)
            out.slice = combine_slices(self.slice, (key,))

        return out

    @property
    def url(self):
        """Return url from where data is fetched."""
        scheme, netloc, path, params, query, fragment = urlparse(self.baseurl)
        url = urlunparse(
            (
                scheme,
                netloc,
                path + ".dods",
                "",
                self.id + hyperslab(self.slice) + "&" + "&".join(self.selection),
                fragment,
            )
        ).rstrip("&")

        return url

    @property
    def id(self):
        """Return the id of this sequence."""
        if self.sub_children:
            id_ = ",".join(child.id for child in self.template.children())
        else:
            id_ = self.template.id
        return id_

    def __iter__(self):
        # download and unpack data
        r = GET(
            self.url,
            self.application,
            self.session,
            timeout=self.timeout,
            verify=self.verify,
            get_kwargs=self.get_kwargs,
        )

        if isinstance(r, webob_Response):
            i = r.app_iter
            if not hasattr(i, "__next__"):
                i = iter(i)
        elif isinstance(r, requests.Response):
            i = r.iter_content()

        # Fast forward past the DDS header
        # the pattern could span chunk boundaries though so make sure to check
        pattern = b"Data:\n"
        last_chunk = find_pattern_in_string_iter(pattern, i)

        if last_chunk is None:
            raise ValueError(
                "Could not find data segment in response from {}".format(self.url)
            )

        # Then construct a stream consisting of everything from
        # 'Data:\n' to the end of the chunk + the rest of the stream
        def stream_start():
            yield last_chunk

        stream = StreamReader(chain(stream_start(), i))

        return unpack_sequence(stream, self.template)

    def __eq__(self, other):
        return ConstraintExpression("%s=%s" % (self.id, encode(other)))

    def __ne__(self, other):
        return ConstraintExpression("%s!=%s" % (self.id, encode(other)))

    def __ge__(self, other):
        return ConstraintExpression("%s>=%s" % (self.id, encode(other)))

    def __le__(self, other):
        return ConstraintExpression("%s<=%s" % (self.id, encode(other)))

    def __gt__(self, other):
        return ConstraintExpression("%s>%s" % (self.id, encode(other)))

    def __lt__(self, other):
        return ConstraintExpression("%s<%s" % (self.id, encode(other)))


def unpack_sequence(stream, template):
    """Unpack data from a sequence, yielding records."""
    # is this a sequence or a base type?
    sequence = isinstance(template, SequenceType)

    # if there are no children, we use the template as the only column
    cols = list(template.children()) or [template]

    # if there are no strings and no nested sequences we can unpack record by
    # record easily
    simple = all(isinstance(c, BaseType) and c.dtype.char not in "SU" for c in cols)

    if simple:
        dtype = numpy.dtype([("", c.dtype, c.shape) for c in cols])
        marker = stream.read(4)
        while marker == START_OF_SEQUENCE:
            rec = numpy.frombuffer(stream.read(dtype.itemsize), dtype=dtype)[0]
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
            out.extend(convert_stream_to_list(stream, col.dtype, col.shape, col.id))
    return out


def convert_stream_to_list(stream, parser_dtype, shape, id):
    out = []
    response_dtype = DAP2_response_dtypemap(parser_dtype)
    if shape:
        n = numpy.frombuffer(stream.read(4), DAP2_ARRAY_LENGTH_NUMPY_TYPE)[0]
        count = response_dtype.itemsize * n
        if response_dtype.char in "S":
            # Consider on 'S' and not 'SU' because
            # response_dtype.char should never be
            data = []
            for _ in range(n):
                k = numpy.frombuffer(stream.read(4), DAP2_ARRAY_LENGTH_NUMPY_TYPE)[0]
                data.append(stream.read(k))
                stream.read(-k % 4)
            out.append(
                numpy.array([str(x.decode("ascii")) for x in data], "S").reshape(shape)
            )
        else:
            stream.read(4)  # read additional length
            try:
                out.append(
                    numpy.frombuffer(stream.read(count), response_dtype)
                    .astype(parser_dtype)
                    .reshape(shape)
                )
            except ValueError as e:
                if str(e) == "total size of new array must be unchanged":
                    # server-side failure.
                    # it is expected that the user should be mindful of this:
                    raise RuntimeError(
                        (
                            "variable {0} could not be properly "
                            "retrieved. To avoid this "
                            "error consider using open_url(..., "
                            "output_grid=False)."
                        ).format(id)
                    )
                else:
                    raise
            if response_dtype.char == "B":
                # Unsigned Byte type is packed to multiples of 4 bytes:
                stream.read(-n % 4)

    # special types: strings and bytes
    elif response_dtype.char in "S":
        # Consider on 'S' and not 'SU' because
        # response_dtype.char should never be
        # 'U'
        k = numpy.frombuffer(stream.read(4), DAP2_ARRAY_LENGTH_NUMPY_TYPE)[0]
        out.append(str(stream.read(k).decode("ascii")))
        stream.read(-k % 4)
    # usual data
    else:
        out.append(
            numpy.frombuffer(
                stream.read(response_dtype.itemsize), response_dtype
            ).astype(parser_dtype)[0]
        )
        if response_dtype.char == "B":
            # Unsigned Byte type is packed to multiples of 4 bytes:
            stream.read(3)
    return out


def unpack_dap2_data(xdr_stream, dataset):
    """Unpack a string of encoded data, returning data as lists."""
    return unpack_children(xdr_stream, dataset)


def find_pattern_in_string_iter(pattern, i):
    last_chunk = b""
    length = len(pattern)
    for this_chunk in i:
        last_chunk += this_chunk
        m = re.search(pattern, last_chunk)
        if m:
            return last_chunk[m.end() :]
        last_chunk = last_chunk[-length:]


def dump():  # pragma: no cover
    """Unpack dods response into lists.

    Return pretty-printed data.

    """
    dods = sys.stdin.read()
    dds, xdrdata = dods.split(b"\nData:\n", 1)
    dataset = dds_to_dataset(dds)
    xdr_stream = io.BytesIO(xdrdata)
    data = unpack_dap2_data(xdr_stream, dataset)
    pprint.pprint(data)


def decode_chunktype(chunk_type):
    """
    Takes the chunk_type from chunk header embeded in the dap response,
    and returns a tuple of
        last_chunk: bool
        error: bool
        endian
    """
    encoding = "{0:03b}".format(chunk_type)
    if sys.byteorder == "little":
        # If our machine's byteorder is little,
        # we need to swap since the chunk_type is always big endian
        encoding = encoding[::-1]
    last_chunk = bool(int(encoding[0]))
    error = bool(int(encoding[1]))
    endian = {"0": ">", "1": "<"}[encoding[2]]
    return last_chunk, error, endian


def get_count(variable):
    count = int(numpy.array(variable.shape).prod())
    item_size = numpy.dtype(variable.dtype).itemsize
    count = count * item_size
    return count


def decode_variable(buffer, start, stop, variable, endian):
    dtype = variable.dtype
    dtype = dtype.newbyteorder(endian)
    data = numpy.frombuffer(buffer[start:stop], dtype=dtype).astype(dtype)
    data = data.reshape(variable.shape)
    return data


def process_chunk(data, offset, chunk_size):
    """
    Process a chunk of data
    """
    chunk_data = data[offset : offset + chunk_size]
    return chunk_data


def stream2bytearray(data):
    """
    Computes the buffer size of the (binary) data form dap response.
    data is sent in chunks, with encoding in between. The encoding is
    sent in packs of 4 bytes, which tells info about endianness, chunk type
    and chunk size, and whether it is last chunk or not. Data inbetween chunks
    is numeric (array) data in binary form that needs to be turn into native
    numpy array data of size =  len(buffer). That last bit is done outside the
    scope of this function.
    """

    # Precompute chunk positions
    chunk_positions = []
    offset = 0
    while offset < len(data):
        # Read the chunk header
        chunk_header = numpy.frombuffer(data[offset : offset + 4], dtype=">u4")[0]
        chunk_size = chunk_header & 0x00FFFFFF
        chunk_type = (chunk_header >> 24) & 0xFF
        last, _, _ = decode_chunktype(chunk_type)
        chunk_positions.append((offset + 4, chunk_size))
        offset += 4 + chunk_size
        if last:
            break

    # Process chunks in parallel
    buffer = bytearray()
    with ThreadPoolExecutor() as executor:
        results = list(
            executor.map(lambda args: process_chunk(data, *args), chunk_positions)
        )
    # Combine results
    for chunk_data in results:
        buffer.extend(chunk_data)
    return buffer


def get_endianness(chunk_header):
    chunk_header = numpy.frombuffer(chunk_header, dtype=">u4")[0]
    chunk_type = (chunk_header >> 24) & 0xFF
    _, _, endian = decode_chunktype(chunk_type)
    return endian


class UNPACKDAP4DATA(object):
    """
    Unpacks DAP4 response, remote or local, which is split into chunks. The
    first chunk contains the DMR response, and the endianness is defined in the first
    4 bytes before the DMR. Once the endianness is set, it remains unchanged. This
    makes the assumption that the all variables within dataset have the same endianness.

    Parameters:
    -----------
        r: contains the dap response.
            May be a Webob.response.Response or requests.response created from
            pydap.net.GET if the dataset is remote (from a url), or a
            `io.BufferedReader` if the data is local within a filesystem.
            See `pydap.net.get.open_dap_file`
    """

    def __init__(self, r, user_charset="ascii"):
        self.user_charset = user_charset
        if isinstance(r, webob_Response):  # a Webob response
            self.r = r
            if self.r.content_encoding == "gzip":
                self.raw = BytesReader(
                    gzip.GzipFile(fileobj=BytesIO(self.r.body)).read()
                )
            else:
                self.raw = BytesReader(r.body)
        elif isinstance(r, BufferedReader):
            # r comes from reading a local file
            self.r = webob_Response()  # make empty response
            self.raw = BytesReader(r.read())
        elif isinstance(r, requests.Response):
            # r comes from reading a remote dataset
            self.r = r
            self.raw = BytesReader(r.content)
        else:
            raise TypeError(
                """
                Unrecognized file type object for unpacking dap4 binary data.
                Acceptable formats are `webob.response.Response` and
                `io.BufferedReader`
                """
            )
        self.dmr, self.data, self.endianness = self.safe_dmr_and_data()
        # need to split dmr from data
        dataset = dmr_to_dataset(self.dmr)
        self.dataset = self.unpack_dap4_data(dataset)

    def safe_dmr_and_data(self):
        """
        Splits the dap response (.dap) into the dmr (metadata), and the raw
        (binary) data. It also computes the endianness of the data.

        Returns:
            dmr, data, endianness
        """
        # decode the first 4 bytes are CRLF
        chunk_header = numpy.frombuffer(self.raw.read(4), dtype=">u4")[0]
        dmr_length = chunk_header & 0x00FFFFFF
        chunk_type = (chunk_header >> 24) & 0xFF
        if isinstance(self.r, webob_Response):
            dmr = self.raw.read(dmr_length).decode(
                get_charset(self.r, self.user_charset)
            )
        else:
            dmr = self.raw.read(dmr_length).decode(self.user_charset)
        data = self.raw.data
        # get endianness from first chunk
        _, _, endianness = decode_chunktype(chunk_type)
        return dmr, data, endianness

    def unpack_dap4_data(self, dataset):
        """
        Takes a pydap.DatasetType previously created, and populates its variables
        (BaseType only) with data that is currently in binary form (within a dap
        response).
        """
        # need self. data and self.dataset
        checksum_dtype = numpy.dtype(self.endianness + "u4")
        buffer = stream2bytearray(self.data)
        start = 0
        for variable in walk(dataset, BaseType):
            count = get_count(variable)
            stop = start + count
            data = decode_variable(
                buffer,
                start=start,
                stop=stop,
                variable=variable,
                endian=self.endianness,
            )
            checksum = numpy.frombuffer(
                buffer[stop : stop + 4], dtype=checksum_dtype
            ).byteswap("=")
            variable._set_data(data)
            variable.attributes["checksum"] = checksum
            # Jump over the 4 byte chunk_header
            start = stop + 4
        return dataset
