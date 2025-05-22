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
import re
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO, open
from os.path import commonprefix
from urllib.parse import parse_qs, unquote, urlencode

from requests.exceptions import (
    ConnectionError,
    SSLError,
)
from requests.utils import urlparse, urlunparse
from requests_cache import CachedSession

from .handlers.dap import UNPACKDAP4DATA, DAPHandler, StreamReader, unpack_dap2_data
from .lib import DEFAULT_TIMEOUT as DEFAULT_TIMEOUT
from .lib import encode
from .model import DapType
from .net import GET, create_session
from .parsers.das import add_attributes, parse_das
from .parsers.dds import dds_to_dataset
from .parsers.dmr import DMRParser, dmr_to_dataset


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


def consolidate_metadata(
    urls, session, concat_dim=None, safe_mode=False, verbose=False
):
    """Consolidates the metadata of a collection of OPeNDAP DAP4 URLs belonging to
    data cube, i.e. urls share identical variables and dimensions. This is done
    by caching the DMR response of each URL, and the DAP response of all dimensions
    in the datacube.

    Parameters
    ----------
    urls : list
        The URLs of the datasets that define a datacube. Each URL must begin
        with the same base URL, and begin with `dap4://`.
    session : requests-cache.CachedSession
        A requests-cache session object. Currently, only the sqlite and memory
        backend are fully tested. The filesystem backend is not yet supported. 
    concat_dim : str, optional (default=None)
        A dimensions name (string) to concatenate across the datasets to form
        a datacube. If `None`, all dimensions present across the datacube
        are assigned to a single cache key, i.e. that of the first URL.
        When `concat_dim` is provided, no cache key is assigned to the
        dimension, and the dap response associated with that dimension
        is then downloaded for each URL.
    safe_mode : bool, optional (default=False)
        If `True`, the DMR response is downloaded for each URL, creating a
        empty pydap dataset. dimensions are checked for datacube consistency.
        When `False`, only the first URL DMR response is
        downloaded, and the rest of the DMRs are assigned the same
        cache key as the first URL, to avoid downloading the DMR
        response for each URL. This is much faster, but does not check
        for consistency across the URLs.
    verbose: bool, optional (default=False)
        For debugging purposes. If `True`, prints various URLs, normalized
        cache-keys, and other information.

    """

    if not isinstance(session, CachedSession):
        warnings.warn("session must be a requests_cache.CachedSession")
        return None
    if not isinstance(urls, list) or len(urls) == 1:
        raise TypeError("urls must be a list of `len` >= 2. Try again!")

    # check elements in urls are strings
    if not all(isinstance(url, str) for url in urls):
        raise TypeError("`urls` must be a list of string urls")

    schemes = [urlparse(urls[n]).scheme for n in range(len(urls))]
    # check if all urls have the same scheme
    scheme = set(schemes)
    if len(scheme) > 1:
        raise ValueError(
            "URLs must have the same scheme. Try again with the same protocol."
        )
    if not scheme.pop() == "dap4":
        warnings.warn(
            "URLs must be a dap4 URL and begin with `dap4://`. To "
            " learn about da4p2 urls, please visit the following link: \n "
            " https://pydap.github.io/pydap/en/faqs/dap2_or_dap4_url.html"
        )
        return None
    # All URLs begin with dap4 - to make sure DAP4 compliant
    URLs = ["https" + urls[i][4:] for i in range(len(urls))]
    ncores = min(len(urls), os.cpu_count() * 4)
    dmr_urls = [
        url + ".dmr" if "?" not in url else url.replace("?", ".dmr?") for url in URLs
    ]
    if safe_mode:
        with session as Session:  # Authenticate once
            with ThreadPoolExecutor(max_workers=ncores) as executor:
                results = list(
                    executor.map(lambda url: open_dmr(url, session=Session), dmr_urls)
                )
        if [ds.dimensions for ds in results].count(results[0].dimensions) != len(
            results
        ):
            warnings.warn(
                "The dimensions of the datasets are identical across all urls. "
                "Please check the URLs and try again."
            )
            return None
    else:
        #  Caches a single dmr and creates a cache key for all dmr urls
        #  to avoid downloading multiple dmr responses.
        patch_session_for_shared_dap_cache(
            session, {}, known_url_list=dmr_urls, verbose=verbose
        )
        results = [open_dmr(dmr_urls[0], session=session)]
        # Does not download the dmr responses, as a cached key was created.
        # But needs to run so the URL is assigned the key.
        with session as Session:
            _ = download_all_urls(Session, dmr_urls, ncores=ncores)

    # Download dimensions once and construct cache key their dap responses
    base_url = URLs[0].split("?")[0]
    # identify dimensions that repeat across the urls
    dims = set(list(results[0].dimensions.keys()))
    # check if all urls have the same dimensions
    # TODO: make sure count of dimensions is the same as the number of urls

    if concat_dim is not None and set([concat_dim]).issubset(dims):
        dims.remove(concat_dim)
        concat_dim_urls = [
            url.split("?")[0]
            + ".dap?dap4.ce="
            + concat_dim
            + "[0:1:"
            + str(results[0].dimensions[concat_dim] - 1)
            + "]"
            for i, url in enumerate(URLs)
        ]
    else:
        concat_dim_urls = []

    new_urls = [
        base_url
        + ".dap?dap4.ce="
        + dim
        + "%5B0:1:"
        + str(results[0].dimensions[dim] - 1)
        + "%5D"
        for dim in list(dims)
    ]
    # add the non-cached urls to download dimension dap data.
    new_urls.extend(concat_dim_urls)

    # xarray does not escaped CE
    dim_ces = set(
        [
            dim + "[0:1:" + str(results[0].dimensions[dim] - 1) + "]"
            for dim in list(dims)
        ]
    )
    if dims:
        if verbose:
            print("==========================================")
            print(
                "\ndatacube has dimensions", dim_ces, ", and concat dim: ", concat_dim
            )
        patch_session_for_shared_dap_cache(
            session, shared_vars=dim_ces, known_url_list=URLs, verbose=verbose
        )
        with session as Session:  # Authenticate once / download dap for each dim
            _ = download_all_urls(Session, new_urls, ncores=ncores)
            # with ThreadPoolExecutor(max_workers=ncores) as executor:
            #     _ = executor.map(lambda url: Session.get(url), new_urls)
    return None


def fetch_dim(url, session, timeout=5):
    try:
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp
    except (ConnectionError, SSLError) as e:
        parsed = urlparse(url)
        if parsed.scheme == "https":
            url = url.replace("https://", "http://")
            resp = session.get(url)
            resp.raise_for_status()
            return resp
        else:
            raise e


def download_all_urls(session, urls, ncores=10, delay=0):
    results = []
    with ThreadPoolExecutor(max_workers=ncores) as executor:
        future_to_url = {executor.submit(fetch_dim, url, session): url for url in urls}
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                print(f"[ERROR] Unexpected failure for {url}: {e}")
    return results


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
        try:
            r = session.get(path)
        except (ConnectionError, SSLError) as e:
            parsed = urlparse(path)
            if parsed.scheme == "https":
                path = path.replace("https://", "http://")
                r = session.get(path)
            else:
                raise e
        dmr = r.text
        dataset = DMRParser(dmr).init_dataset()
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
    dataset = dds_to_dataset(dds)
    pos = len(dds) + len("Data:\n")

    with open(file_path, "rb") as f:
        f.seek(pos)
        dataset.data = unpack_dap2_data(f, dataset)

    if das_path is not None:
        with open(das_path) as f:
            das = parse_das(f.read())
            add_attributes(dataset, das)

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

    r = GET(url, application, session, timeout=timeout)

    dds, data = r.body.split(b"\nData:\n", 1)
    dds = dds.decode(r.content_encoding or "ascii")
    dataset = dds_to_dataset(dds)
    stream = StreamReader(BytesIO(data))
    dataset.data = unpack_dap2_data(stream, dataset)

    if metadata:
        scheme, netloc, path, params, query, fragment = urlparse(url)
        dasurl = urlunparse(
            (scheme, netloc, path[:-4] + "das", params, query, fragment)
        )
        r = GET(dasurl, application, session, timeout=timeout, verify=verify)

        das = parse_das(r.text)
        add_attributes(dataset, das)

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
            if isinstance(arg, (DapType, ServerFunctionResult)):
                params.append(arg.id)
            else:
                params.append(encode(arg))
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


def compute_base_url_prefix(url_list):
    """
    Compute the longest common base path across a list of URLs.
    Returns the common prefix as a normalized base URL.
    """
    if not isinstance(url_list, list) or len(url_list) < 2:
        raise ValueError("url_list must be a list of at least two URLs.")
    if not all(isinstance(url, str) for url in url_list):
        raise ValueError("url_list must contain only strings.")
    if not all(url.startswith("http") for url in url_list):
        raise ValueError("url_list must contain valid HTTP URLs.")
    parsed_paths = [urlparse(url).path.split("?")[0] for url in url_list]
    parsed_paths = [("/").join(path.split("/")[:-1]) + "/" for path in parsed_paths]
    common_path = os.path.dirname(commonprefix(parsed_paths))
    if common_path == "/":
        raise ValueError("No common path found in the provided URLs.")
    # Normalize the common path
    parsed_example = urlparse(url_list[0])
    return f"{parsed_example.scheme}://{parsed_example.netloc}{common_path}"


def try_generate_custom_key(request, config, verbose=False):
    parsed = urlparse(request.url)
    path = parsed.path
    ext = path.split(".")[-1]  # e.g. 'dap' or 'dmr'
    query = parse_qs(parsed.query)
    dap4_ce = query.get("dap4.ce", [None])[0]
    if dap4_ce:
        dap4_ce = unquote(dap4_ce)

    shared_vars = config.get("shared_vars", set())
    general_base = config.get("general_base")
    known_url_list = config.get("known_url_list", [])
    is_dmr = config.get("is_dmr", False)

    if ext == "dmr" and not is_dmr:
        return None
    if ext == "dap" and (not shared_vars or dap4_ce not in shared_vars):
        return None

    if verbose:
        print("-------------------------------------------------------")
        print("request.url: ", request.url)
        print("-------------------------------------------------------")
        print("shared_vars: ", shared_vars)
        print("query: ", query)
        print("known urls", known_url_list)
        print("is_dmr: ", is_dmr)

    shared_ext = ext

    # Earthdata URLs
    if parsed.netloc == "opendap.earthdata.nasa.gov":
        match = re.search(r"(/providers/[^/]+/collections/[^/]+)", path)
        if match:
            dataset_path = match.group(1)
            base_url = (
                f"{parsed.scheme}://{parsed.netloc}{dataset_path}/shared.{shared_ext}"
            )
            if verbose:
                print("-------------------------------------------------------")
                print("match")
                print("-------------------------------------------------------")
                print(
                    f"{base_url}?{urlencode({'dap4.ce': dap4_ce})}"
                    if dap4_ce
                    else base_url
                )
            return (
                f"{base_url}?{urlencode({'dap4.ce': dap4_ce})}" if dap4_ce else base_url
            )

    # General POSIX-style URLs
    if general_base and path.startswith(urlparse(general_base).path):
        base_path = urlparse(general_base).path
        base_url = f"{parsed.scheme}://{parsed.netloc}{base_path}/shared.{shared_ext}"
        if verbose:
            print("======== NON-cloud url ========")
            print(
                f"{base_url}?{urlencode({'dap4.ce': dap4_ce})}" if dap4_ce else base_url
            )
        return f"{base_url}?{urlencode({'dap4.ce': dap4_ce})}" if dap4_ce else base_url

    return None


def patch_session_for_shared_dap_cache(
    session, shared_vars, known_url_list=None, verbose=False
):
    """
    Patch CachedSession to support multiple incremental cache key configurations.
    Repeated calls extend the list of supported URL patterns.
    """
    if known_url_list is None:
        known_url_list = []

    # Compute new config entry
    # queries = [urlparse(url).query for url in known_url_list]
    is_dmr = len(known_url_list) > 0 and all(".dmr" in url for url in known_url_list)
    general_base = compute_base_url_prefix(known_url_list) if known_url_list else ""

    new_config = {
        "shared_vars": set(shared_vars),
        "known_url_list": known_url_list,
        "general_base": general_base,
        "is_dmr": is_dmr,
    }

    # Initialize list of configs if needed
    if not hasattr(session, "_dap_cache_configs"):
        session._dap_cache_configs = []
        original_create_key = session.cache.create_key

        def custom_create_key(request, **kwargs):
            # Skip auth URLs
            if any(x in request.url for x in ["urs", "oauth", "login"]):
                return original_create_key(request, **kwargs)

            # Try each config in order
            for cfg in session._dap_cache_configs:
                key = try_generate_custom_key(request, cfg, verbose)
                if key:
                    return key

            # Fall back to original behavior
            return original_create_key(request, **kwargs)

        session.cache.create_key = custom_create_key

    # Append the new config to the session
    session._dap_cache_configs.append(new_config)


if __name__ == "__main__":
    fname = "/home/griessbaum/Dropbox/UCSB/pydap_cpt/pydap_notebooks/data/"
    ds = open_file(fname + "coads_climatology.nc.dmr")
    print(ds)
