"""
Client interface to OPeNDAP servers.

This module implements the ``open_url`` function, which returns an
object representing a remote dataset served by an OPeNDAP server. The
client builds the dataset representation from the DDS+DAS responses,
though in the future it can be extended to support other representations
(like DDX, or perhaps JSON).

"""

import sys
from urlparse import urlsplit, urlunsplit

from pydap.model import *
from pydap.model import DapType
from pydap.proxy import *
from pydap.parsers.dds import DDSParser
from pydap.parsers.das import DASParser
from pydap.xdr import DapUnpacker
from pydap.util.http import request
from pydap.exceptions import ClientError
from pydap.lib import walk, combine_slices, fix_slice, parse_qs, fix_shn, encode_atom


def open_url(url):
    """
    Open a given dataset URL, trying different response methods. 

    The function checks the stub DDX method, and falls back to the
    DDS+DAS responses. It can be easily extended for other representations
    like JSON.

    The URL should point to the dataset, omitting any response extensions
    like ``.dds``. Username and password can be passed in the URL like::

        http://user:password@example.com:port/path

    They will be transmitted as plaintext if the server supports only
    Basic authentication, so be careful. For Digest authentication this
    is safe.

    The URL can point directly to an Opendap dataset, or it can contain
    any number of contraint expressions (selection/projections)::

        http://example.com/dataset?var1,var2&var3>10

    You can also specify a cache directory, a timeout and a proxy using
    the global variables from ``pydap.lib``::

        >>> import pydap.lib
        >>> pydap.lib.TIMEOUT = 60  # seconds
        >>> pydap.lib.CACHE = '.cache'
        >>> import httplib2
        >>> from pydap.util import socks
        >>> pydap.lib.PROXY = httplib2.ProxyInfo(socks.PROXY_TYPE_HTTP, 'localhost', 8000)

    """
    for response in [_ddx, _ddsdas]:
        dataset = response(url)
        if dataset: break
    else:
        raise ClientError("Unable to open dataset.")

    # Remove any projections from the url, leaving selections.
    scheme, netloc, path, query, fragment = urlsplit(url)
    projection, selection = parse_qs(query)
    url = urlunsplit(
            (scheme, netloc, path, '&'.join(selection), fragment))

    # Set data to a Proxy object for BaseType and SequenceType. These
    # variables can then be sliced to retrieve the data on-the-fly.
    for var in walk(dataset, BaseType):
        var.data = ArrayProxy(var.id, url, var.shape)
    for var in walk(dataset, SequenceType):
        var.data = SequenceProxy(var.id, url)

    # Set server-side functions.
    dataset.functions = Functions(url)

    # Apply the corresponding slices.
    projection = fix_shn(projection, dataset)
    for var in projection:
        target = dataset
        while var:
            token, slice_ = var.pop(0)
            target = target[token]
            if slice_ and isinstance(target.data, VariableProxy):
                shape = getattr(target, 'shape', (sys.maxint,))
                target.data._slice = fix_slice(slice_, shape)

    return dataset


class Functions(object):
    """
    An entry point for server side functions.

    Since we don't know which functions the server support, any function
    can be called by the user. The name will be passed to the server, together
    with the corresponding arguments.

    """
    def __init__(self, baseurl):
        self.baseurl = baseurl

    def __getattr__(self, attr):
        return ServerFunction(self.baseurl, attr)


class ServerFunction(object):
    """
    An object representing a named server side function.

    The function uses lazy evaluation to allow for nested calls. Calling
    the function will return a ``ServerFunctionResult`` object that only
    downloads data when actually accessed by the user.

    """
    def __init__(self, baseurl, name):
        self.baseurl = baseurl
        self.name = name

    def __call__(self, *args):
        params = []
        for arg in args:
            if isinstance(arg, (DapType, ServerFunctionResult)):
                params.append(arg.id)
            else:
                params.append(encode_atom(arg))
        id_ = self.name + '(' + ','.join(params) + ')'
        return ServerFunctionResult(self.baseurl, id_)


class ServerFunctionResult(object):
    """
    An object containing the result from a server function call.

    The result will download data when any attribute or item is
    accessed, simulating a dataset object.

    """
    def __init__(self, baseurl, id_):
        self.id = id_
        self.dataset = None

        scheme, netloc, path, query, fragment = urlsplit(baseurl)
        self.url = urlunsplit((
                scheme, netloc, path + '.dods', id_, None))
    
    def __getattr__(self, name):
        if self.dataset is None: self.dataset = open_dods(self.url, True)
        return getattr(self.dataset, name)

    def __getitem__(self, key):
        if self.dataset is None: self.dataset = open_dods(self.url, True)
        return self.dataset[key]


def open_dods(url, get_metadata=False):
    """
    Download data from a DODS response and build a dataset.

    This function is useful to open "raw" URLs.

    """
    resp, data = request(url)
    dds, xdrdata = data.split('\nData:\n', 1)
    dataset = DDSParser(dds).parse()
    dataset.data = DapUnpacker(xdrdata, dataset).getvalue()

    if get_metadata:
        scheme, netloc, path, query, fragment = urlsplit(url)
        dasurl = urlunsplit(
                (scheme, netloc, path[:-5] + '.das', query, fragment))
        resp, das = request(dasurl)
        dataset = DASParser(das, dataset).parse()

    return dataset


def _ddx(url):
    """
    Stub function for DDX.

    Still waiting for the DDX spec to write this.

    """
    pass


def _ddsdas(url):
    """
    Build the dataset from the DDS+DAS responses.

    This function builds the dataset object from the DDS and DAS
    responses, adding Proxy objects to the variables.

    """
    scheme, netloc, path, query, fragment = urlsplit(url)
    ddsurl = urlunsplit(
            (scheme, netloc, path + '.dds', query, fragment))
    dasurl = urlunsplit(
            (scheme, netloc, path + '.das', query, fragment))

    respdds, dds = request(ddsurl)
    respdas, das = request(dasurl)

    # Build the dataset structure and attributes.
    dataset = DDSParser(dds).parse()
    dataset = DASParser(das, dataset).parse()
    return dataset

