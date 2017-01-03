"""Pydap client.

This module contains functions to access DAP servers. The most common use is to
open a dataset by its canonical URL, ie, without any DAP related extensions
like dds/das/dods/html. Here is an example:

    >>> from pydap.client import open_url
    >>> dataset = open_url("http://test.pydap.org/coads.nc")

This will return a `DatasetType` object, which is a container for lazy
evaluated objects. Data is downloaded automatically when arrays are sliced or
when sequences are iterated.

It is also possible to download data directly from a dods (binary) response.
This allows calling server-specific functions, like those supported by the
Ferret and the GrADS data servers:

    >>> from pydap.client import open_dods
    >>> dataset = open_dods(
    ...     "http://test.pydap.org/coads.nc.dods",
    ...     metadata=True)

Setting the `metadata` flag will also request the das response, populating the
dataset with the corresponding metadata.

If the dods response has already been downloaded, it is possible to open it as
if it were a remote dataset. Optionally, it is also possible to specify a das
response:

    >>> from pydap.client import open_file
    >>> dataset = open_file(
    ...     "/path/to/file.dods", "/path/to/file.das")  #doctest: +SKIP

Remote datasets opened with `open_url` can call server functions. Pydap has a
lazy mechanism for function call, supporting any function. Eg, to call the
`geogrid` function on the server:

    >>> dataset = open_url(
    ...     'http://test.opendap.org/dap/data/nc/coads_climatology.nc')
    >>> new_dataset = dataset.functions.geogrid(dataset.SST, 10, 20, -10, 60)
    >>> print(new_dataset.SST.SST.shape)
    (12, 12, 21)

"""

from io import open, BytesIO
from six.moves.urllib.parse import urlsplit, urlunsplit

from pydap.model import DapType
from pydap.lib import encode
from pydap.net import GET
from pydap.handlers.dap import DAPHandler, unpack_data, StreamReader
from pydap.parsers.dds import build_dataset
from pydap.parsers.das import parse_das, add_attributes


def open_url(url, application=None, session=None, output_grid=True):
    """
    Open a remote URL, returning a dataset.

    set output_grid to False to retrieve only main arrays and
    never retrieve coordinate axes.
    """
    dataset = DAPHandler(url, application, session, output_grid).dataset

    # attach server-side functions
    dataset.functions = Functions(url, application, session)

    return dataset


def open_file(dods, das=None):
    """Open a file downloaded from a `.dods` response, returning a dataset.

    Optionally, read also the `.das` response to assign attributes to the
    dataset.

    """
    dds = ''
    # This file contains both ascii _and_ binary data
    # Let's handle them separately in sequence
    # Without ignoring errors, the IO library will
    # actually read past the ascii part of the
    # file (despite our break from iteration) and
    # will error out on the binary data
    with open(dods, "rt", buffering=1, encoding='ascii',
              newline='\n', errors='ignore') as f:
        for line in f:
            if line.strip() == 'Data:':
                break
            dds += line
    dataset = build_dataset(dds)
    pos = len(dds) + len('Data:\n')

    with open(dods, "rb") as f:
        f.seek(pos)
        dataset.data = unpack_data(f, dataset)

    if das is not None:
        with open(das) as f:
            add_attributes(dataset, parse_das(f.read()))

    return dataset


def open_dods(url, metadata=False, application=None, session=None):
    """Open a `.dods` response directly, returning a dataset."""
    r = GET(url, application, session)
    dds, data = r.body.split(b'\nData:\n', 1)
    dds = dds.decode(r.content_encoding or 'ascii')
    dataset = build_dataset(dds)
    stream = StreamReader(BytesIO(data))
    dataset.data = unpack_data(stream, dataset)

    if metadata:
        scheme, netloc, path, query, fragment = urlsplit(url)
        dasurl = urlunsplit(
            (scheme, netloc, path[:-4] + 'das', query, fragment))
        das = GET(dasurl, application, session).text
        add_attributes(dataset, parse_das(das))

    return dataset


class Functions(object):

    """Proxy for server-side functions."""

    def __init__(self, baseurl, application=None, session=None):
        self.baseurl = baseurl
        self.application = application
        self.session = session

    def __getattr__(self, attr):
        return ServerFunction(self.baseurl, attr, self.application,
                              self.session)


class ServerFunction(object):

    """A proxy for a server-side function.

    Instead of returning datasets, the function will return a proxy object,
    allowing nested requests to be performed on the server.

    """

    def __init__(self, baseurl, name, application=None, session=None):
        self.baseurl = baseurl
        self.name = name
        self.application = application
        self.session = None

    def __call__(self, *args):
        params = []
        for arg in args:
            if isinstance(arg, (DapType, ServerFunctionResult)):
                params.append(arg.id)
            else:
                params.append(encode(arg))
        id_ = self.name + '(' + ','.join(params) + ')'
        return ServerFunctionResult(self.baseurl, id_, self.application,
                                    self.session)


class ServerFunctionResult(object):

    """A proxy for the result from a server-side function call."""

    def __init__(self, baseurl, id_, application=None, session=None):
        self.id = id_
        self.dataset = None
        self.application = application
        self.session = session

        scheme, netloc, path, query, fragment = urlsplit(baseurl)
        self.url = urlunsplit((scheme, netloc, path + '.dods', id_, None))

    def __getitem__(self, key):
        if self.dataset is None:
            self.dataset = open_dods(self.url, True, self.application,
                                     self.session)
        return self.dataset[key]

    def __getattr__(self, name):
        return self[name]
