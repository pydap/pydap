"""
pydap client.

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

    >>> from pydap.client import open_dods_url
    >>> dataset = open_dods_url(
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

Remote datasets opened with `open_url` can call server functions. pydap has a
lazy mechanism for function call, supporting any function. Eg, to call the
`geogrid` function on the server:

    >>> dataset = open_url(
    ...     'http://test.opendap.org/dap/data/nc/coads_climatology.nc')
    >>> new_dataset = dataset.functions.geogrid(dataset.SST, 10, 20, -10, 60)
    >>> print(new_dataset.SST.SST.shape) #doctest: +SKIP
    (12, 12, 21)

"""

import os

# import logging
import re
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO, open
from os.path import commonprefix
from urllib.parse import parse_qs, unquote, urlencode

import requests
from requests.utils import urlparse, urlunparse
from requests_cache import CachedSession

import pydap.handlers.dap
import pydap.lib
import pydap.model
import pydap.net
import pydap.parsers.das
import pydap.parsers.dds
from pydap.handlers.dap import UNPACKDAP4DATA, DAPHandler
from pydap.lib import DEFAULT_TIMEOUT as DEFAULT_TIMEOUT
from pydap.parsers.dmr import DMRParser, dmr_to_dataset

from .net import create_session


def open_url(
    url,
    application=None,
    session=None,
    output_grid=False,
    timeout=DEFAULT_TIMEOUT,
    verify=True,
    user_charset="ascii",
    protocol=None,
    use_cache=False,
    session_kwargs=None,
    cache_kwargs=None,
    get_kwargs=None,
):
    """
    Open a remote OPeNDAP URL, or a local (wsgi) application returning a pydap
    dataset.

    Parameters
    ----------
    url : str
        The URL of the dataset.
    application: a WSGI application object | None
        When set, we are dealing with a local application, and a webob.response is
        returned. When None, a requests.Response object is returned.
    session : requests.Session
        A requests session object.
    output_grid : bool Default is True
        Whether to output grid arrays or not. If `False` only main arrays are
        retrieved and not the coordinate axes.
    timeout : int
        The timeout for the request.
    verify : bool
        Verify SSL certificates.
    user_charset : str
        The charset to use when decoding strings.
    protocol : str | bool (Default: None)
        The OPeNDAP protocol to use when creating the OPeNDAP request. Default is
        `None`. Other  options are 'dap2' and 'dap4'. When None, pydap attempts to
        infer the protocol from the URL. If the URL ends with '.dap', the protocol
        is 'dap4'. If the URL ends with '.dods', the protocol is 'dap2'. Another
        option to specify the protocol is to use replace the url scheme (http, https)
        with 'dap2' or 'dap4'.
    use_cache : bool (Default: False)
        Whether to use the cache or not in the requests.
    session_kwargs: dict | None
        keyword arguments used to create a new session object. Only used if
        session is None. A `token` for authentication can be passed here.
    cache_kwargs: dict | None
        keyword arguments used to create a new cache object. Only used if
        use_cache is True. See `pydap.net.GET`.
    get_kwargs: dict | None
        additional keyword arguments passed to `requests.get`.


    Returns:
        pydap.model.dataset
    """

    if not session:
        session = create_session(
            use_cache=use_cache,
            session_kwargs=session_kwargs,
            cache_kwargs=cache_kwargs,
        )
    handler = DAPHandler(
        url,
        application,
        session,
        output_grid,
        timeout=timeout,
        verify=verify,
        user_charset=user_charset,
        protocol=protocol,
        get_kwargs=get_kwargs,
    )
    dataset = handler.dataset
    dataset._session = session

    # attach server-side functions
    dataset.functions = Functions(url, application, session, timeout=timeout)

    return dataset


def open_dap4murl(
    urls,
    session=None,
    protocol=None,
    ncores=None,
):
    """Opens multiple OPeNDAP DAP4 URL

    Parameters
    ----------
    urls : list
        The URLs of the datasets that define a datacube.
        session : requests.Session or requests-cache.CachedSession
            A requests session object.
        ncores : int
            The number of cores to use for the requests. Default is 4 times the
            number of CPUs.
    Returns:
        requests-cache.CachedSession
    """

    if not session:
        session = create_session()
    if not isinstance(urls, list):
        print("raise error: urls must be a list of len > 1")
    scheme = urlparse(urls[0]).scheme
    if not scheme == "dap4":
        print("warning: only dap4 urls are supported")
        dmr_urls = [urls[i].replace(scheme, "dap4") for i in range(len(urls))]
    else:
        dmr_urls = urls
        URLs = [urls[i].replace("dap4", "http") for i in range(len(urls))]
    if not ncores:
        ncores = min(len(urls), os.cpu_count() * 4)
    query = "?"
    if query in urls[0]:
        dmr_urls = [url.replace(query, ".dmr" + query) for url in urls]
    else:
        dmr_urls = [url + ".dmr" for url in urls]
    # this caches the dmr
    with session as Session:  # Authenticate once
        with ThreadPoolExecutor(max_workers=ncores) as executor:
            results = list(
                executor.map(lambda url: open_url(url, session=Session), dmr_urls)
            )

    # Download once dimensions and construct cache key their dap responses
    base_url = URLs[0].split("?")[0]
    # identify dimensions that repeat across the urls
    nested = [list(results[i].dimensions) for i in range(len(results))]
    dims = set([item for sublist in nested for item in sublist])
    if not dims:
        print("Error: No dimensions found")
    new_urls = [
        base_url
        + ".dap?dap4.ce="
        + dim
        + "%5B0:1:"
        + str(len(results[0][dim]) - 1)
        + "%5D"
        for dim in list(dims)
    ]
    # ces should not be escaped? xarray does not escaped them
    dim_ces = set(
        [dim + "[0:1:" + str(len(results[0][dim]) - 1) + "]" for dim in list(dims)]
    )
    print("datacube has dimensions", dim_ces)
    # create custom cache keys
    if isinstance(session, CachedSession):
        patch_session_for_shared_dap_cache(
            session, shared_vars=dim_ces, known_url_list=URLs
        )
        with session as Session:  # Authenticate once
            with ThreadPoolExecutor(max_workers=ncores) as executor:
                results = list(
                    executor.map(lambda url: fetch_url(url, session=Session), new_urls)
                )
    return session


def open_file(file_path, das_path=None):
    extension = file_path.split(".")[-1]
    if extension == "dods":
        return open_dods_file(file_path=file_path, das_path=das_path)
    elif extension == "dap":
        return open_dap_file(file_path=file_path, das_path=das_path)
    elif extension == "dds":
        pass
    elif extension == "dmr":
        return open_dmr_file(file_path=file_path)


def open_dmr(path, session=None):
    """Retrieves a remote dmr from a server and returns an empty dataset.
    If the path is to a local file, then it is opened directly.
    """
    if path is None:
        return None
    if path.startswith("http") and "dmr" in path:
        # Open a remote dmr
        if session is None:
            session = create_session()
        r = session.get(path)
        dmr = r.text
        dataset = DMRParser(dmr).init_dataset()
        # dataset._session = session
        return dataset
    else:
        try:
            return open_dmr_file(path)
        except FileNotFoundError:
            print(f"File {path} not found.")
            return None


def open_dmr_file(file_path):
    """
    Opens a DMR. This differs from a dap response, since it is a single chunk,
    and there is no chunk header at the top of the file.
    """
    with open(file_path, "rb") as f:
        dmr = f.read()
    dmr = dmr.decode("ascii")
    dataset = dmr_to_dataset(dmr)
    return dataset


def open_dap_file(file_path):
    """Open a file downloaded from a `.dap` (dap4) response, returning a
    dataset.
    """
    with open(file_path, "rb") as f:
        return UNPACKDAP4DATA(f).dataset


def open_dods_file(file_path, das_path=None):
    """Open a file downloaded from a `.dods` (dap2) response, returning a
    dataset.

    Optionally, read also the `.das` response to assign attributes to the
    dataset.

    """
    dds = ""
    # This file contains both ascii _and_ binary data
    # Let's handle them separately in sequence
    # Without ignoring errors, the IO library will
    # actually read past the ascii part of the
    # file (despite our break from iteration) and
    # will error out on the binary data
    with open(
        file_path, "rt", buffering=1, encoding="ascii", newline="\n", errors="ignore"
    ) as f:
        for line in f:
            if line.strip() == "Data:":
                break
            dds += line
    dataset = pydap.parsers.dds.dds_to_dataset(dds)
    pos = len(dds) + len("Data:\n")

    with open(file_path, "rb") as f:
        f.seek(pos)
        dataset.data = pydap.handlers.dap.unpack_dap2_data(f, dataset)

    if das_path is not None:
        with open(das_path) as f:
            das = pydap.parsers.das.parse_das(f.read())
            pydap.parsers.das.add_attributes(dataset, das)

    return dataset


def open_dods_url(
    url,
    metadata=False,
    application=None,
    session=None,
    timeout=DEFAULT_TIMEOUT,
    verify=True,
):
    """Open a `.dods` response directly, returning a dataset."""

    r = pydap.net.GET(url, application, session, timeout=timeout)

    dds, data = r.body.split(b"\nData:\n", 1)
    dds = dds.decode(r.content_encoding or "ascii")
    dataset = pydap.parsers.dds.dds_to_dataset(dds)
    stream = pydap.handlers.dap.StreamReader(BytesIO(data))
    dataset.data = pydap.handlers.dap.unpack_dap2_data(stream, dataset)

    if metadata:
        scheme, netloc, path, params, query, fragment = urlparse(url)
        dasurl = urlunparse(
            (scheme, netloc, path[:-4] + "das", params, query, fragment)
        )
        r = pydap.net.GET(dasurl, application, session, timeout=timeout, verify=verify)

        das = pydap.parsers.das.parse_das(r.text)
        pydap.parsers.das.add_attributes(dataset, das)

    return dataset


class Functions(object):
    """Proxy for server-side functions."""

    def __init__(
        self, baseurl, application=None, session=None, timeout=DEFAULT_TIMEOUT
    ):
        self.baseurl = baseurl
        self.application = application
        self.session = session
        self.timeout = timeout

    def __getattr__(self, attr):
        return ServerFunction(
            self.baseurl, attr, self.application, self.session, timeout=self.timeout
        )


class ServerFunction(object):
    """A proxy for a server-side function.

    Instead of returning datasets, the function will return a proxy object,
    allowing nested requests to be performed on the server.

    """

    def __init__(
        self,
        baseurl,
        name,
        application=None,
        session=None,
        timeout=DEFAULT_TIMEOUT,
    ):
        self.baseurl = baseurl
        self.name = name
        self.application = application
        self.session = session
        self.timeout = timeout

    def __call__(self, *args):
        params = []
        for arg in args:
            if isinstance(arg, (pydap.model.DapType, ServerFunctionResult)):
                params.append(arg.id)
            else:
                params.append(pydap.lib.encode(arg))
        id_ = self.name + "(" + ",".join(params) + ")"
        return ServerFunctionResult(
            self.baseurl, id_, self.application, self.session, timeout=self.timeout
        )


class ServerFunctionResult(object):
    """A proxy for the result from a server-side function call."""

    def __init__(
        self,
        baseurl,
        id_,
        application=None,
        session=None,
        timeout=DEFAULT_TIMEOUT,
    ):
        self.id = id_
        self.dataset = None
        self.application = application
        self.session = session
        self.timeout = timeout

        scheme, netloc, path, params, query, fragment = urlparse(baseurl)
        self.url = urlunparse((scheme, netloc, path + ".dods", params, id_, None))

    def __getitem__(self, key):
        if self.dataset is None:
            self.dataset = open_dods_url(
                self.url, True, self.application, self.session, self.timeout
            )
        return self.dataset[key]

    def __getattr__(self, name):
        return self[name]


def fetch_url(url, session):
    """Fetch a URL and return its status code."""
    try:
        response = session.get(url, stream=True)
        return url, response.status_code
    except requests.RequestException as e:
        return url, f"Error: {e}"


def compute_base_url_prefix(url_list):
    """
    Compute the longest common base path across a list of URLs.
    Returns the common prefix as a normalized base URL.
    """
    parsed_paths = [urlparse(url).path for url in url_list]
    common_path = os.path.dirname(commonprefix(parsed_paths))
    parsed_example = urlparse(url_list[0])
    return f"{parsed_example.scheme}://{parsed_example.netloc}{common_path}"


def patch_session_for_shared_dap_cache(session, shared_vars, known_url_list=None):
    """
    Patch CachedSession to normalize cache keys for:
    - Earthdata URLs: group by DAAC + collection_id
    - General POSIX-style URLs: group by shared base path (computed from known_url_list)
    """
    original_create_key = session.cache.create_key
    general_base = compute_base_url_prefix(known_url_list) if known_url_list else None

    def custom_create_key(request, **kwargs):
        parsed = urlparse(request.url)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)
        dap4_ce = query.get("dap4.ce", [None])[0]
        if dap4_ce:
            dap4_ce = unquote(dap4_ce)

        if dap4_ce in shared_vars:
            # Handle Earthdata-style URLs
            if parsed.netloc == "opendap.earthdata.nasa.gov":
                match = re.search(r"(/providers/[^/]+/collections/[^/]+)", path)
                if match:
                    dataset_path = match.group(1)
                    base_url = (
                        f"{parsed.scheme}://{parsed.netloc}{dataset_path}/shared.dap"
                    )
                    normalized_url = f"{base_url}?{urlencode({'dap4.ce': dap4_ce})}"
                    return normalized_url

            # Handle general POSIX-style URLs
            base_path = urlparse(general_base).path
            if general_base and path.startswith(base_path):
                # Use the computed shared base + virtual shared filename
                # url_path=urlparse(general_base).path
                base_url = f"{parsed.scheme}://{parsed.netloc}{base_path}/shared.nc"
                normalized_url = f"{base_url}?{urlencode({'dap4.ce': dap4_ce})}"
                return normalized_url

        return original_create_key(request, **kwargs)

    session.cache.create_key = custom_create_key


def earth_patch_session_for_shared_dap_cache(session, shared_vars):
    """
    Patch a CachedSession so that all requests to the same dataset
    (same DAAC and collection_id) with identical dap4.ce values share a cache key.

    Example matching URLs:
    https://.../providers/DAAC/collections/COLL_ID/granules/GRAN_ID.dap?dap4.ce=...

    Args:
        session: requests-cache CachedSession
        shared_vars: Set of dap4.ce values (decoded) that should be shared across
        granules
        verbose: Whether to log cache key generation
    """
    original_create_key = session.cache.create_key

    def custom_create_key(request, **kwargs):
        parsed = urlparse(request.url)
        path = unquote(parsed.path)
        query = parse_qs(parsed.query)
        dap4_ce = query.get("dap4.ce", [None])[0]

        # Normalize dap4.ce (decode and check)
        if dap4_ce:
            dap4_ce = unquote(dap4_ce)

        if dap4_ce in shared_vars and path.endswith(".dap"):
            # Extract /providers/<DAAC>/collections/<COLLECTION_ID>
            match = re.search(r"(/providers/[^/]+/collections/[^/]+)", path)
            if match:
                dataset_path = match.group(1)
                base_url = f"{parsed.scheme}://{parsed.netloc}{dataset_path}/shared.dap"
                normalized_url = f"{base_url}?{urlencode({'dap4.ce': dap4_ce})}"
                return normalized_url

        return original_create_key(request, **kwargs)

    session.cache.create_key = custom_create_key


if __name__ == "__main__":
    fname = "/home/griessbaum/Dropbox/UCSB/pydap_cpt/pydap_notebooks/data/"
    ds = open_file(fname + "coads_climatology.nc.dmr")
    print(ds)
