"""Basic functions related to the DAP spec."""

import operator
import threading
import warnings
from collections import Counter
from functools import reduce
from itertools import zip_longest
from sys import maxsize as MAXSIZE

import numpy as np
from requests.utils import quote as quote_
from requests.utils import unquote as unquote_

from . import __version__
from .exceptions import ConstraintExpressionError

__dap__ = "2.15"

# when installed in --editable mode, the `__version__` can be a very long str
# which causes `test_responses_html.py to fail (Content-Length' != '5864'
# in test_headers). This will work for now.

__version__ = str(__version__)[:5]  # it used to be 3.4.1, len=5.

START_OF_SEQUENCE = b"\x5a\x00\x00\x00"
END_OF_SEQUENCE = b"\xa5\x00\x00\x00"
STRING = "|S128"
DEFAULT_TIMEOUT = 120  # 120 seconds = 2 minutes

NUMPY_TO_DAP2_TYPEMAP = {
    "d": "Float64",
    "f": "Float32",
    "h": "Int16",
    "H": "UInt16",
    "i": "Int32",
    "l": "Int32",
    "q": "Int32",
    "I": "UInt32",
    "L": "UInt32",
    "Q": "UInt32",
    # DAP2 does not support signed bytes.
    # Its Byte type is unsigned and thus corresponds
    # to numpy's 'B'.
    # The consequence is that there is no natural way
    # in DAP2 to represent numpy's 'b' type.
    # Ideally, DAP2 would have a signed Byte type
    # and an unsigned UByte type and we would have the
    # following mapping: {'b': 'Byte', 'B': 'UByte'}
    # but this not how the protocol has been defined.
    # This means that numpy's 'b' must be mapped to Int16
    # and data must be upconverted in the DODS response.
    "b": "Int16",
    "B": "Byte",
    # There are no boolean types in DAP2. Upconvert to
    # Byte:
    "?": "Byte",
    "S": "String",
    # Map numpy's 'U' to String b/c
    # DAP2 does not explicitly support unicode.
    "U": "String",
}

# DAP2 demands big-endian 32 bytes signed integers
# www.opendap.org/pdf/dap_2_data_model.pdf
# Before pydap 3.2.2, length was
# big-endian 32 bytes UNSIGNED integers:
# DAP2_ARRAY_LENGTH_NUMPY_TYPE = '>I'
# Since pydap 3.2.2, the length type is accurate:
DAP2_ARRAY_LENGTH_NUMPY_TYPE = ">i"

DAP2_TO_NUMPY_RESPONSE_TYPEMAP = {
    "Float64": ">d",
    "Float32": ">f",
    # This is a weird aspect of the DAP2 specification.
    # For backward-compatibility, Int16 and UInt16 are
    # encoded as 32 bits integers in the response,
    # respectively:
    "Int16": ">i",
    "UInt16": ">I",
    "Int32": ">i",
    "UInt32": ">I",
    # DAP2 does not support signed bytes.
    # It's Byte type is unsigned and thus corresponds
    # to numpy 'B'.
    # The consequence is that there is no natural way
    # in DAP2 to represent numpy's 'b' type.
    # Ideally, DAP2 would have a signed Byte type
    # and a usigned UByte type and we would have the
    # following mapping: {'Byte': 'b', 'UByte': 'B'}
    # but this not how the protocol has been defined.
    # This means that DAP2 Byte is unsigned and must be
    # mapped to numpy's 'B' type, usigned byte.
    "Byte": "B",
    # Map String to numpy's string type 'S' b/c
    # DAP2 does not explicitly support unicode.
    "String": "S",
    "URL": "S",
    #
    # These two types are not DAP2 but it is useful
    # to include them for compatiblity with other
    # data sources:
    "Int": ">i",
    "UInt": ">I",
}

# Typemap from lower case DAP2 types to
# numpy dtype string with specified endiannes.
# Here, the endianness is very important:
LOWER_DAP2_TO_NUMPY_PARSER_TYPEMAP = {
    "float64": ">d",
    "float32": ">f",
    "int16": ">h",
    "uint16": ">H",
    "int32": ">i",
    "uint32": ">I",
    "byte": "B",
    "string": STRING,
    "url": STRING,
    "int": ">i",
    "uint": ">I",
}

# Typemap from lower case DAP4 types to
# numpy dtype string with specified endiannes.
# Here, the endianness is very important:
DAP4_TO_NUMPY_PARSER_TYPEMAP = {
    "Float16": ">f2",
    "Float32": ">f4",
    "Float64": ">f8",
    "Int8": ">i1",
    "UInt8": ">u1",
    "Int16": ">i2",
    "UInt16": ">u2",
    "Int32": ">i4",
    "UInt32": ">u4",
    "Int64": ">i8",
    "UInt64": ">u8",
    "Byte": "B",
    "String": STRING,
    "Url": STRING,
    "Char": ">u1",
}


def _quote(name):
    """Return quoted name according to the DAP specification.

    >>> _quote("White space")
    'White%20space'
    >>> _quote("Period.")
    'Period%2E'

    """
    safe = "%_!~*'-\"/"
    if "dap4" == name[:4]:
        # Dap4 protocol. Must not scape = sign there.
        prefix = name[:8]
        name = name[8:]
    else:
        prefix = ""
    name = quote_(name.encode("utf-8"), safe=safe).replace(".", "%2E")
    return prefix + name.replace("[", "%5B").replace("]", "%5D")


def unquote(name):
    """Return unquoted name according to the DAP specification.

    >>> unquote("White%20space")
    'White space'
    >>> unquote("Period%2E")
    'Period.'

    """
    name = name.replace("%2E", ".").replace("%5B", "[").replace("%5D", "]")
    return unquote_(name)


def encode(obj):
    """Return an object encoded to its DAP representation."""
    # fix for Python 3.5, where strings are being encoded as numbers
    if isinstance(obj, str) or isinstance(obj, np.ndarray) and obj.dtype.char in "SU":
        return '"{0}"'.format(obj)

    # fix for DeprecationWarning: Conversion of an array with ndim > 0 to a
    # scalar is deprecated
    if isinstance(obj, np.ndarray) and np.ndim(obj) > 0:
        arr_str = np.array2string(obj, formatter={"float_kind": lambda x: f"{x:.6f}"})
        return f'"[{arr_str[1:-1]}]"'
    else:
        try:
            return "%.6g" % obj
        except Exception:
            return '"{0}"'.format(obj)


def fix_slice(slice_, shape):
    """Return a normalized slice.

    This function returns a slice so that it has the same length of `shape`,
    and no negative indexes, if possible.

    This is based on this document:

        https://numpy.org/doc/stable/user/basics.indexing.html#slicing-and-striding

    """
    # convert `slice_` to a tuple
    if not isinstance(slice_, tuple):
        slice_ = (slice_,)

    # expand Ellipsis and make `slice_` at least as long as `shape`
    expand = len(shape) - len(slice_)
    out = []
    for s in slice_:
        if s is Ellipsis:
            out.extend((slice(None),) * (expand + 1))
            expand = 0
        else:
            out.append(s)
    slice_ = tuple(out) + (slice(None),) * expand

    out = []
    for s, N in zip(slice_, shape):
        if isinstance(s, int):
            if s < 0:
                s += N
            out.append(s)
        else:
            k = s.step or 1

            i = s.start
            if i is None:
                i = 0
            elif i < 0:
                i += N

            j = s.stop
            if j is None or j >= (N + i):
                j = N + i
            elif j < 0:
                j += N

            out.append(slice(i, j, k))

    return tuple(out)


def combine_slices(slice1, slice2):
    """Return two tuples of slices combined sequentially.

    These two should be equal:

        x[ combine_slices(s1, s2) ] == x[s1][s2]

    """
    out = []
    for exp1, exp2 in zip_longest(slice1, slice2, fillvalue=slice(None)):
        if isinstance(exp1, int):
            exp1 = slice(exp1, exp1 + 1)
        if isinstance(exp2, int):
            exp2 = slice(exp2, exp2 + 1)

        start = (exp1.start or 0) + (exp2.start or 0)
        step = (exp1.step or 1) * (exp2.step or 1)

        if exp1.stop is None and exp2.stop is None:
            stop = None
        elif exp1.stop is None:
            stop = (exp1.start or 0) + exp2.stop
        elif exp2.stop is None:
            stop = exp1.stop
        else:
            stop = min(exp1.stop, (exp1.start or 0) + exp2.stop)

        out.append(slice(start, stop, step))
    return tuple(out)


def hyperslab(slice_):
    """Return a DAP representation of a multidimensional slice."""
    if not isinstance(slice_, tuple):
        slice_ = [slice_]
    else:
        slice_ = list(slice_)

    while slice_ and slice_[-1] == slice(None):
        slice_.pop(-1)

    return "".join(
        "[%s:%s:%s]" % (s.start or 0, s.step or 1, (s.stop or MAXSIZE) - 1)
        for s in slice_
    )


def walk(var, type=object):
    """Yield all variables of a given type from a dataset.

    The iterator returns also the parent variable.

    """
    if isinstance(var, type):
        yield var
    for child in var.children():
        for subvar in walk(child, type):
            yield subvar


def tree(template, prefix=""):
    # Print the current node's name, add '.' at the root level
    if prefix == "":
        print(f".{unquote_(template.name)}")
    else:
        print(template.name)

    # Iterate over the children
    Nchild = len([child for child in template.children()])
    for i, child in enumerate(template.children()):
        # Determine the prefix for the current child
        if i == Nchild - 1:
            child_prefix = "└──"
            next_prefix = "   "
        else:
            child_prefix = "├──"
            next_prefix = "│  "

        # Print the current child
        print(prefix + child_prefix, end="")

        # Recursively call tree on the child with updated prefix
        tree(child, prefix + next_prefix)


def fix_shorthand(projection, dataset):
    """Fix shorthand notation in the projection.

    Some clients request variables by their name, not by the id. This is called
    the "shorthand notation", and it has to be fixed. This function will return
    a new projection with no shorthand calls.

    """
    out = []
    for var in projection:
        if len(var) == 1 and var[0][0] not in list(dataset.keys()):
            token, slice_ = var.pop(0)
            for child in walk(dataset):
                if token == unquote(child.name):
                    if var:
                        raise ConstraintExpressionError(
                            "Ambiguous shorthand notation request: %s" % token
                        )
                    var = [(parent, ()) for parent in child.id.split(".")[:-1]] + [
                        (token, slice_)
                    ]
        out.append(var)
    return out


def get_var(dataset, id_):
    """Given an id, return the corresponding variable from the dataset."""
    tokens = id_.split(".")
    return reduce(operator.getitem, [dataset] + tokens)


def decode_np_strings(numpy_var):
    """Given a fixed-width numpy string, decode it to a unicode type"""
    if isinstance(numpy_var, (bytes, np.bytes_)):
        return numpy_var.decode("utf-8")
    else:
        return numpy_var


def get_batch_data(ds, cache={}, checksums=True):
    """
    parent object - either a dataset or Group type (dap4)
    """
    import pydap

    # dimensions = sorted(ds.dimensions)
    dimensions = [
        var.id
        for var in walk(ds.dataset, pydap.model.BaseType)
        if var.name in var.parent.dimensions
    ]
    # check if data has been pre-downloaded
    if "consolidated" in ds.dataset.session.headers:
        # need to add a check that consolidated has
        # been performed on that collection.
        cache = fetch_consolidated_dimensions(ds, cache)
    else:
        register_all_for_batch(ds.dataset, dimensions, checksums=checksums)
        cache = fetch_batched_dimensions(ds.dataset, dimensions, cache)
    return cache


def register_all_for_batch(ds, Variables, checksums=True) -> None:
    """
    Used to register all dimension array when pydap
    dataset has been initialized with batch=True.

    Parameters:
    ----------
        ds: dataset (dap4)
        Variables: list
            List of dimensions in `ds` that will be processed
        checksums: bool | True (default)
    """

    for name in Variables:
        var = ds[name]
        if not var._is_data_loaded():  # and var.id != concat_dim:
            var._pending_batch_slice = slice(None)
            ds.register_for_batch(var, checksums=checksums)
            var._is_registered_for_batch = True
    ds._start_batch_timer()
    # return promise


def fetch_batched_dimensions(ds, Variables, cache=None):
    """
    Helper function that fetched dimensions within a pydap dataset
    or Group, that have been registered for batched download. Only compatible
    with DAP4 protocol, and batch=True parameter when intializating the
    pydap dataset.

    Parameters:
    ----------
        ds: pydap dataset (dap4)
        Variables: list
            items within the ds or Group.
        cache: bool (False is default)
            dictionary that stores the name of the dimension and its value

    Returns:
        dict:
            containing all dimension array data
    """
    if cache is None:
        cache = {}

    promise = ds._current_batch_promise
    promise._event.wait()

    for name in Variables:
        data = promise.wait_for_result(ds[name].id)
        cache[ds[name].id] = np.asarray(data)

    ds.dataset._current_batch_promise = None
    return cache


def fetch_consolidated_dimensions(ds, cache, checksums=True) -> {}:
    """
    Helper function that makes it easier to process previously download
    dap responses of dimension data, i.e. after `consolidated_metadata`
    is executed. This helper processes dimension array data that was
    downloaded / batched together in a single dap response.
    when the urls for the dap responses are cached.

    This function needs to be run after executing `consolidated_metadata` since
    in that function, the cache_session object contains special metadata in its
    headers. It also requires that the pydap dataset associated with the BaseType
    `var`, is in Batch=True mode.

    Parameters:
    ----------
        ds: Dataset | GroupType (DAP4)
            Must `batch=True` and point to remote data.
        cache: dict
            Where dimension array data will be stored.
        checksums: bool (Default=True)
            Whether the dap response was requested with checksum=true. If true,
            there is a checksum value inbetween each variable within the dap
            response. when `checksum=False`, the dap response was created without the
            checksum per variable. Important info for decoding

    Returns:
        cache: dict
            contains the dimension array data decoded into numpy arrays.
    """

    import pydap

    var_name = list(ds.variables())[0]
    baseurl = ds[var_name].data.baseurl
    session = ds.dataset.session
    cache_urls = session.cache.urls()
    miss_url, curr_url = recover_missing_url(cache_urls, baseurl)
    dap_urls = miss_url + curr_url
    for URL in set(dap_urls):
        r = session.get(URL, stream=True)
        pyds = pydap.handlers.dap.UNPACKDAP4DATA(r, checksums=checksums).dataset
        for name in pyds.keys():
            # get fully qualifying name here?
            cache[pyds[name].id] = np.asarray(pyds[name].data)
    return cache


def resolve_batch_for_all_variables(array, key=None, checksums=True):
    """
    Resolves a batch promise for all non-dimension variables within the
    parent container.
    """
    import pydap

    dataset = array.dataset
    # get the fully qualifying name of all variables in dataset
    Variables = [
        var.id
        for var in walk(dataset, pydap.model.BaseType)
        if var.name not in var.parent.dimensions
    ]

    if dataset._current_batch_promise is None:
        dataset._current_batch_promise = BatchPromise()
        _slice = slice(None) if not key else key
        for name in Variables:
            var = dataset[name]
            if not var._is_data_loaded():
                var._pending_batch_slice = _slice
                var._batch_promise = dataset._current_batch_promise
                dataset.register_for_batch(var, checksums=checksums)

        dataset._start_batch_timer()


def recover_missing_url(cached_urls, baseurl):
    """
    given a list of opendap (dap4) urls, it reconstructs missing dap url
    along with its constraints, that matches the corresponding cached url that
    fetches identical data.

    Returns:


    """
    import pydap.client as client

    dap_urls = [url for url in cached_urls if url.split("?")[0].endswith(".dap")]
    common_prefix = client.compute_base_url_prefix(dap_urls)
    # the following is a test on its own it len(dap_ulrs)=0 then there is something
    # wrong (for example - some of the cached urls contain urls from different
    # collection)
    dap_urls = [
        url
        for url in dap_urls
        if url.split("?")[0][: len(common_prefix)] == common_prefix
    ]

    base_urls = [url.split(".dap")[0] for url in dap_urls]

    # find all currently matching dap url that have been cached
    current_dap_urls = [
        url for url in cached_urls if url.split(".dap")[0] == baseurl.split(".dap")[0]
    ]

    duplicate = [item for item, count in Counter(base_urls).items() if count > 1]
    if len(duplicate) == 1:
        # assume there is only one repeated base url - produce of
        # consolidate metadata with freshly created session object
        duplicate = duplicate[0]
    else:
        warnings.warn(
            "Could not figure out dap urls. Clear your session cache and start again"
        )

    queries = [
        url.split("?")[-1]
        for url in dap_urls
        if url.split("?")[0] == duplicate + ".dap"
    ]

    new_dap_urls = [baseurl + ".dap?" + query for query in queries]
    missing_dap_urls = [url for url in new_dap_urls if url not in cached_urls]
    paired_urls = [
        duplicate + ".dap" + url.split(".dap")[1] for url in missing_dap_urls
    ]

    return paired_urls, current_dap_urls


class BatchPromise:
    def __init__(self):
        self._event = threading.Event()
        self._results = {}

    def set_results(self, results):
        self._results = results
        self._event.set()

    def wait_for_result(self, var_id):
        self._event.wait()
        return self._results[var_id]

    def is_resolved(self):
        return self._event.is_set()


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


class old_BytesReader(object):
    """Class to allow reading a `bytes` object."""

    def __init__(self, data):
        self.data = data

    def read(self, n):
        """Read and return `n` bytes."""
        out = self.data[:n]
        self.data = self.data[n:]
        return out

    def peek(self, n):
        return self.data[:n]


class BytesReader:
    """Class to allow reading from a file-like object or bytes."""

    def __init__(self, source):
        if isinstance(source, (bytes, bytearray)):
            import io

            self.data = io.BytesIO(source)
        elif hasattr(source, "read"):
            self.data = source
        else:
            raise TypeError("Expected bytes or a file-like object with .read()")

    def read(self, n):
        return self.data.read(n)

    def peek(self, n):
        import io

        if isinstance(self.data, io.BytesIO):
            current_pos = self.data.tell()
            out = self.data.read(n)
            self.data.seek(current_pos)
            return out
        elif hasattr(self.data, "peek"):
            return self.data.peek(n)
        else:
            # Manual peek fallback: read + seek back (requires seekable stream)
            current_pos = self.data.tell()
            out = self.data.read(n)
            self.data.seek(current_pos)
            return out

    def slice(self, offset, n):
        """Mimics buffer[offset:offset+n] for file-like object"""
        pos = self.data.tell()
        self.data.seek(offset)
        buf = self.data.read(n)
        self.data.seek(pos)
        return buf
