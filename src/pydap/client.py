from urlparse import urlsplit, urlunsplit

import requests

from pydap.model import DapType
from pydap.lib import encode
from pydap.handlers.dap import DAPHandler, unpack_data
from pydap.parsers.dds import build_dataset
from pydap.parsers.das import parse_das, add_attributes


def open_url(url):
    dataset = DAPHandler(url).dataset

    # attach server-side functions
    dataset.functions = Functions(url)

    return dataset


def open_file(dods, das=None):
    with open(dods) as f:
        dds, data = f.read().split('\nData:\n', 1)
        dataset = build_dataset(dds)
        dataset.data = unpack_data(data, dataset)

    if das is not None:
        with open(das) as f:
            add_attributes(dataset, parse_das(f.read()))

    return dataset


def open_dods(url, metadata=False):
    r = requests.get(url)
    dds, data = r.content.split('\nData:\n', 1)
    dataset = build_dataset(dds)
    dataset.data = unpack_data(data, dataset)

    if metadata:
        scheme, netloc, path, query, fragment = urlsplit(url)
        dasurl = urlunsplit((scheme, netloc, path[:-4] + 'das', query, fragment))
        das = requests.get(dasurl).text.encode('utf-8')
        add_attributes(dataset, parse_das(das))

    return dataset


class Functions(object):
    """
    Proxy for server-side functions.

    """
    def __init__(self, baseurl):
        self.baseurl = baseurl

    def __getattr__(self, attr):
        return ServerFunction(self.baseurl, attr)


class ServerFunction(object):
    """
    A proxy for a server-side function.

    Instead of returning datasets, the function will return a proxy object,
    allowing nested requests to be performed on the server.

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
                params.append(encode(arg))
        id_ = self.name + '(' + ','.join(params) + ')'
        return ServerFunctionResult(self.baseurl, id_)


class ServerFunctionResult(object):
    """
    A proxy for the result from a server-side function call.

    """
    def __init__(self, baseurl, id_):
        self.id = id_
        self.dataset = None

        scheme, netloc, path, query, fragment = urlsplit(baseurl)
        self.url = urlunsplit((scheme, netloc, path + '.dods', id_, None))

    def __getattr__(self, name):
        if self.dataset is None:
            self.dataset = open_dods(self.url, True)
        return getattr(self.dataset, name)

    def __getitem__(self, key):
        if self.dataset is None:
            self.dataset = open_dods(self.url, True)
        return self.dataset[key]
        

