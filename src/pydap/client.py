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

import datetime as dt
import os
import re
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO, open
from os.path import commonprefix
from urllib.parse import parse_qs, unquote, urlencode

import requests
from requests.exceptions import (
    ConnectionError,
    SSLError,
)
from requests.utils import urlparse, urlunparse
from requests_cache import CachedSession

from pydap.handlers.dap import (
    UNPACKDAP4DATA,
    DAPHandler,
    StreamReader,
    unpack_dap2_data,
)
from pydap.lib import DEFAULT_TIMEOUT as DEFAULT_TIMEOUT
from pydap.lib import encode
from pydap.model import DapType
from pydap.net import GET, create_session
from pydap.parsers.das import add_attributes, parse_das
from pydap.parsers.dds import dds_to_dataset
from pydap.parsers.dmr import DMRParser, dmr_to_dataset


def open_url(
    url,
    application=None,
    session=None,
    output_grid=False,
    timeout=DEFAULT_TIMEOUT,
    verify=True,
    checksums=True,
    user_charset="ascii",
    protocol=None,
    batch=False,
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
    batch: bool (Default: False)
        Flag that indicates download multiple arrays with single dap response. Only
        compatible with DAP4 protocol.
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
        checksums=checksums,
        user_charset=user_charset,
        protocol=protocol,
        get_kwargs=get_kwargs,
    )
    dataset = handler.dataset
    dataset._session = session
    if handler.protocol == "dap4" and application is None and batch:  # and batch
        # always enable batch mode for dap4 datasets
        dataset.enable_batch_mode()
    # attach server-side functions
    dataset.functions = Functions(url, application, session, timeout=timeout)

    return dataset


def consolidate_metadata(
    urls,
    session,
    concat_dim=None,
    safe_mode=True,
    set_maps=False,
    verbose=False,
    checksums=True,
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
    concat_dim : str, optional (default=None)
        A dimensions name (string) to concatenate across the datasets to form
        a datacube. If `None`, each dimension across the datacube
        are assigned to a single cache key, i.e. that of the first URL.
        When `concat_dim` is provided, no cache key is created for that
        dimension, and the dap response associated with that dimension
        is then downloaded for each URL.
    safe_mode : bool, optional (default=True)
        If `True`, all DMR responses are downloaded for each URL, creating a
        empty pydap dataset. dimensions names and sizes are checked for
        datacube consistency. When `False`, only the first URL DMR response is
        downloaded, and the rest of the DMRs are assigned the same
        cache key as the first URL, to avoid downloading the DMR
        response for each URL. This is faster, but does not check
        for consistency across the URLs.
        `NOTE`: If `concat_dim` is defined, and its dimension has a lenght
        greater than one, `safe_mode` is automatically set to `True` always.
    set_maps:
        False by default. Checks for Maps in the opendap model (similar to
        coords in xarray) that exist in the first remote url dataset. Then
        downloads all these within a single url. The url address is then
        stored in the session's headers as `Maps`.
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
    session.headers["consolidated"] = "True"
    if safe_mode:
        with session as Session:  # Authenticate once
            with ThreadPoolExecutor(max_workers=ncores) as executor:
                results = list(
                    executor.map(lambda url: open_dmr(url, session=Session), dmr_urls)
                )
        _dim_check = results[0].dimensions
        if not all(d == _dim_check for d in [ds.dimensions for ds in results]):
            warnings.warn(
                "The dimensions of the datasets are not identical across all remote "
                "dataset. Please check the URLs and try again."
            )
            return None
    else:
        #  Caches a single dmr and creates a cache key for all dmr urls
        #  to avoid downloading multiple dmr responses.
        patch_session_for_shared_dap_cache(
            session, {}, None, known_url_list=dmr_urls, verbose=verbose
        )
        results = [open_dmr(dmr_urls[0], session=session)]
        # Does not download the dmr responses, as a cached key was created.
        # But needs to run so the URL is assigned the key.
        with session as Session:
            _ = download_all_urls(Session, dmr_urls, ncores=ncores)
    # Download dimensions once and construct cache key their dap responses
    base_url = URLs[0].split("?")[0]
    dims = set(list(results[0].dimensions))
    add_dims = set()
    if not checksums:
        warnings.warn(
            "Checksums are not optional yet, but will be in a future release."
            " Setting `checksum=True`",
            stacklevel=2,
        )
    _check = "&dap4.checksum=true"
    if concat_dim is not None and set([concat_dim]).issubset(dims):
        dims.remove(concat_dim)
        concat_dim_urls = [
            url.split("?")[0]
            + ".dap?dap4.ce="
            + concat_dim
            + "%5B0:1:"
            + str(results[0].dimensions[concat_dim] - 1)
            + "%5D"
            + _check
            for i, url in enumerate(URLs)
        ]
    else:
        concat_dim_urls = []

    # check for named dimensions
    pyds = open_url(dmr_urls[0], session=session, protocol="dap4", batch=False)
    var_names = list(pyds.variables())
    new_dims = set.intersection(dims, var_names)
    named_dims = set.difference(dims, new_dims)
    dims = sorted(list(new_dims))

    constrains_dims = [
        dim + "%5B0%3A1%3A" + str(results[0].dimensions[dim] - 1) + "%5D"
        for dim in dims
        if dim != concat_dim
    ]
    if len(constrains_dims) > 0:
        new_urls = [base_url + ".dap?dap4.ce=" + "%3B".join(constrains_dims) + _check]
    else:
        new_urls = []
    new_urls.extend(concat_dim_urls)
    dim_ces = set(
        [
            ";".join(
                [
                    dim + "[0:1:" + str(results[0].dimensions[dim] - 1) + "]"
                    for dim in list(dims) + sorted(list(named_dims))
                ]
            )
        ]
    )
    maps_ces = None
    if set_maps:
        maps = None or set(
            [
                item.split("/")[-1]
                for var in list(pyds.variables())
                for item in pyds[var].Maps
                if item.split("/")[-1] not in pyds.dimensions
            ]
        )
        coords = set(
            [
                item
                for var in pyds.variables()
                if pyds[var].attributes.get("coordinates", None)
                for item in pyds[var].attributes.get("coordinates", None).split(" ")
            ]
        )
        coords = [
            item
            for item in coords
            if item not in list(pyds.dimensions) and item in pyds.variables()
        ]  # rename coords
        maps.update(coords)
        if maps:
            # may be 2 or 3D!
            map_urls = [
                var
                + "".join(
                    ["%5B0:1:" + str(length - 1) + "%5D" for length in pyds[var].shape]
                )
                for var in sorted(maps)
            ]
            map_urls = [base_url + ".dap?dap4.ce=" + ";".join(map_urls) + _check]
            maps_ces = set(
                [
                    coord + "[0:1:" + str(len(pyds[coord]) - 1) + "]"
                    for coord in list(maps)
                ]
            )
            new_urls.extend(map_urls)
    if dims or concat_dim:
        print(
            "datacube has dimensions",
            list(dim_ces)[0].split(";"),
            f", and concat dim: `{concat_dim}`",
        )
        dim_ces.update(add_dims)
        if maps_ces:
            dim_ces.update(maps_ces)
        with session as Session:
            _ = download_all_urls(Session, new_urls, ncores=ncores)
    return None


def fetch_dim(url, session, timeout=5):
    """helper function that enables catch of http vs https
    connection errors (mostly for testing).
    """
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


def download_all_urls(session, urls, ncores=4):
    """Helper function that enables parallel download of multiple
    responses. Enables to identify which URL failed.
    """
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
    ext = path.split(".")[-1]  # e.g., 'dap' or 'dmr'
    query = parse_qs(parsed.query)
    dap4_ce = query.get("dap4.ce", [None])[0]
    if dap4_ce:
        dap4_ce = unquote(dap4_ce)

    shared_vars = config.get("shared_vars", set())
    shared_base_vars = {v.split("[")[0] for v in shared_vars}
    concat_dim = config.get("concat_dim")
    is_dmr = config.get("is_dmr", False)

    if ext == "dmr" and not is_dmr:
        return None

    if ext != "dap" or not dap4_ce:
        return None

    # Extract variable names from dap4.ce (e.g., "THETA[0:1:100]" → "THETA")
    vars_in_ce = re.findall(r"([a-zA-Z_][\w]*)\s*\[", dap4_ce)
    vars_set = set(vars_in_ce)

    # === Case 1: All shared vars → reuse shared cache key
    if vars_set and vars_set.issubset(shared_base_vars):
        # Reuse across known_url_list → build common base
        if verbose:
            print(f"[SHARED] {dap4_ce} → shared key")
        return base_url_cache(parsed, config, ext, dap4_ce, verbose)

    # === Case 2: Exactly one var and it's the concat_dim → allow per-file caching
    if vars_set == {concat_dim}:
        if verbose:
            print(f"[PER-FILE] {dap4_ce} → fallback to default key")
        return None  # fallback to per-URL caching

    # === Case 3: Includes non-shared, non-concat → block caching
    if verbose:
        print(f"[BLOCK] Non-shared, non-concat vars in dap4.ce: {dap4_ce}")
    return False  # do not cache


def base_url_cache(parsed, config, shared_ext, dap4_ce, verbose):
    # Earthdata URLs
    general_base = config.get("general_base")
    path = parsed.path

    if parsed.netloc == "opendap.earthdata.nasa.gov":
        match = re.search(r"(/providers/[^/]+/collections/[^/]+)", path)
        if match:
            dataset_path = match.group(1)
            base_url = (
                f"{parsed.scheme}://{parsed.netloc}{dataset_path}/shared.{shared_ext}"
            )
            if verbose:
                print("======== normalized Earthdata url ========")
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
            print("======== Normalized url ========")
            print(
                f"{base_url}?{urlencode({'dap4.ce': dap4_ce})}" if dap4_ce else base_url
            )
        return f"{base_url}?{urlencode({'dap4.ce': dap4_ce})}" if dap4_ce else base_url


def patch_session_for_shared_dap_cache(
    session, shared_vars, concat_dim, known_url_list=None, verbose=False
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
        "concat_dim": concat_dim,
        "known_url_list": known_url_list,
        "general_base": general_base,
        "is_dmr": is_dmr,
    }

    # Initialize list of configs if needed
    if not hasattr(session, "_dap_cache_configs"):
        session._dap_cache_configs = []
        original_create_key = session.cache.create_key

        def custom_create_key(request, **kwargs):
            if any(x in request.url for x in ["urs", "oauth", "login"]):
                return original_create_key(request, **kwargs)

            for cfg in session._dap_cache_configs:
                key = try_generate_custom_key(request, cfg, verbose)
                if key is False:
                    if verbose:
                        print(
                            f"[BLOCK-CACHE] Preventing caching for URL: {request.url}"
                        )
                    return None  # <-- Critical: DO NOT fall back
                elif key:
                    return key
            # Fallback only if no config matched AND not explicitly blocked
            return original_create_key(request, **kwargs)

        session.cache.create_key = custom_create_key

    # Append the new config to the session
    session._dap_cache_configs.append(new_config)


def get_cmr_urls(
    ccid=None,
    doi=None,
    time_range=None,
    bounding_box: list | dict | None = None,
    point: list | dict | None = None,
    polygon: list | dict | None = None,
    line: list | dict | None = None,
    circle: list | dict | None = None,
    session=None,
    limit=50,
):
    """
    Get the granule OPeNDAP URLs associated with a given concept collection ID (ccid) or
    collection DOI (doi) from the CMR API. This functions allows you to filter
    the search by time range and spatial shapes (bounding box, point, polygon, line,
    circle)

    `NOTE`: A query could consist of multiple spatial parameters of different types, two
    bounding boxes and a polygon for example. If multiple spatial parameters are
    present, all the parameters irrespective of their type are AND-ed in a query. So, if
    a query contains two bounding boxes and a polygon for example, it will return only
    those collections which intersect both the bounding boxes and the polygon.

    `NOTE`: The spatial parameters are not mutually exclusive. You can use multiple
    spatial parameters in a single query. For example, you can use a bounding box and a
    polygon in the same query. When the spatial parameters are different types, theser
    are AND-ed together, meaning the search will return results that intersect all
    spatial parameters. For example, if you use a bounding box and a polygon in the same
    query, the results will include only those collections that intersect both the
    bounding box andf the polygon. When the spatial parameters are the same type, they
    are AND-ed together by default. However, it is possible to make them OR-ed by adding
    an extra key-value pair to the bounding box, point, polygon, line, or circle
    parameters (dict). The key is "Union" and the value can be `True` of `False`.
    If `True`, the spatial parameters are OR-ed together. For example, if you use two
    bounding boxes in the same query, and set the "Union" key to `True`, the results
    will include all collections that intersect either of the bounding boxes. If
    `False` (default), the results will include only those collections that intersect
    both bounding boxes. The same applies to the other spatial parameters.

    Parameters
    ----------
        ccid : str
            The collection concept ID to search for.
        doi : str
            The DOI of the collection to search for. This is an alternative to using
            the ccid parameter.
        time_range : list | None
            The time range to filter by. The time range is a list of two elements,
            each element a datetime.datetime object, of a string in the format
            YYYY-MM-DDTHH:MM:SSZ.
            Example1: ["2023-01-01T00:00:00Z", "2023-12-31T23:59:59Z"]
            Example2: [datetime.datetime(2023, 1, 1), datetime.datetime(2023, 12, 31)]

        bounding_box : list | dict | None
            The bounding box to filter by, in the format [west, south, east, north].
            Supports multiple bounding boxes.

            Example1: bounding_box = [lon1, lat1, lon2, lat2]
            Example2: bounding_box = {"box1": [lon1, lat1, lon2, lat2],
                                      "box2": [lon3, lat3, lon4, lat4]}
            Example3: bounding_box = {"box1": [lon1, lat1, lon2, lat2],
                                      "box2": [lon3, lat3, lon4, lat4],
                                      "Union": True}
            The "Union" key is optional (if not present is set to `False`).

        point: list | dict | None
            Search using a pair of values representing the point coordinates as
            parameters, in the format [longitude, latitude]. Supports multiple
            points, as a dictionary.

                Example1: point = [lon1, lat1]
                Example2: point = {"point1": [lon1, lat1], "point2": [lon2, lat2]}
                Example3: point = {"point1": [lon1, lat1], "point2": [lon2, lat2],
                                   "Union": True}
            The "Union" key is optional (if not present is set to `False`).

        polygon: list | dict | None
            The polygon to filter by. Polygon points are provided in counter-clockwise
            order. The last point should match the first point to close the polygon.
            The values are listed comma separated in longitude latitude order. Supports
            multiple polygons, in that case polygon MUST be a dictionary.

            Examples:
                polygon = [lon1, lat1, lon2, lat2, lon3, lat3, lon1, lat1]
                polygon = {"poly1": [lon1, lat1, lon2, lat2, ..., lon1, lat1],
                           "poly2": [lon1, lat1, lon2, lat2, ..., lon1, lat1],
                            "Union": True}
            The "Union" key is optional (if not present is set to `False`).

        line: list | dict | None
            Lines are provided as a list of comma separated values representing
            coordinates of points along the line. The coordinates are listed in the
            format [lon1, lat1, lon2, lat2, ...]. Multiple lines can be provided, and in
            that scenario it must be a dictionary.
            Examples:
                line = [lon1, lat1, lon2, lat2, ...]
                line = {'line1': [lon11, lat11, lon12, lat12, ...],
                        'line2': [lon21, lat21, lon22, lat22, ...]}

        circle: list | dict | None
            Circle defines a circle area on the earth with a center point and a radius.
            The center parameters must be 3 comma-separated numbers: longitude of the
            center point, latitude of the center point, radius of the circle in meters.
            Multiple circles can be provided as nested lists.
            Example:
                circle = [lon, lat, radius]
                circle = {"circle1": [lon1, lat1, radius1],
                          "circle2": [lon2, lat2, radius2]}

        session : requests.Session | None
            A requests session object. If None, a new session is created.

        limit : int
            The maximum number of results to return. Default is 50.

    Returns:
    ---------
        list
            A list of granule OPeNDAP URLs.

    See:
        https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html
        https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html#c-polygon
        https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html#c-bounding-box
        https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html#c-point
        https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html#c-line
    """

    if not ccid and not doi:
        raise ValueError("Either ccid or doi must be provided.")

    cmr_url = "https://cmr.earthdata.nasa.gov/search/granules"
    headers = {
        "Accept": "application/vnd.nasa.cmr.umm+json",
    }
    if session is None or not isinstance(session, (requests.Session, CachedSession)):
        session = create_session()
    params = {"page_size": limit}

    if doi:
        doisearch = "https://cmr.earthdata.nasa.gov/search/collections.json?doi=" + doi
        ccid = session.get(doisearch).json()["feed"]["entry"][0]["id"]

    params["concept_id"] = ccid

    if time_range and isinstance(time_range, list):
        if len(time_range) != 2:
            warnings.warn("time_range must be a list of two elements.")
            return None
        if all(isinstance(x, dt.datetime) for x in time_range):
            dt_format = "%Y-%m-%dT%H:%M:%SZ"
            temporal_str = (
                time_range[0].strftime(dt_format)
                + ","
                + time_range[1].strftime(dt_format)
            )
        else:
            try:
                dt.datetime.strptime(time_range[0], "%Y-%m-%dT%H:%M:%SZ")
                dt.datetime.strptime(time_range[1], "%Y-%m-%dT%H:%M:%SZ")
                temporal_str = time_range[0] + "," + time_range[1]
            except ValueError:
                warnings.warn(
                    "time_range must be a list of two elements each a string in the"
                    " format YYYY-MM-DDTHH:MM:SSZ."
                )
                return None
        params["temporal"] = temporal_str
    elif time_range and not isinstance(time_range, list):
        warnings.warn(
            "time_range must be a list of two elements or a string in the format"
            " YYYY-MM-DDTHH:MM:SSZ."
        )
        return None
    if bounding_box:
        if isinstance(bounding_box, list):
            cmr_url += "?bounding_box%5B%5D=" + "%2C".join(str(x) for x in bounding_box)
        elif isinstance(bounding_box, dict):
            ces = []
            if "Union" in bounding_box:
                extra = bounding_box.pop("Union", None)
            else:
                extra = False
            for key, value in bounding_box.items():
                if isinstance(value, list):
                    ces.append(
                        "bounding_box%5B%5D=" + "%2C".join(str(x) for x in value)
                    )
                else:
                    raise ValueError(
                        "bounding_box must be a list or a dictionary of lists."
                    )
            cmr_url += "?" + "&".join(ces)
            if extra:
                cmr_url += "&options%5Bbounding_box%5D%5Bor%5D=true"
        else:
            raise ValueError("`bounding_box` must be a list or a dictionary of lists.")
    if polygon:
        if isinstance(polygon, list):
            cmr_url += "?polygon%5B%5D=" + "%2C".join(str(x) for x in polygon)
        elif isinstance(polygon, dict):
            ces = []
            if "Union" in polygon:
                extra = polygon.pop("Union", None)
            else:
                extra = False
            for key, value in polygon.items():
                if isinstance(value, list):
                    ces.append("polygon%5B%5D=" + "%2C".join(str(x) for x in value))
                else:
                    raise ValueError("polygon must be a list or a dictionary of lists.")
            cmr_url += "?" + "&".join(ces)
            if extra:
                cmr_url += "&options%5Bpolygon%5D%5Bor%5D=true"
        else:
            raise ValueError("`polygon` must be a list or a dictionary of lists.")
    if line:
        if isinstance(line, list):
            cmr_url += "?line%5B%5D=" + "%2C".join(str(x) for x in line)
        elif isinstance(line, dict):
            ces = []
            if "Union" in line:
                extra = line.pop("Union", None)
            else:
                extra = False
            for key, value in line.items():
                if isinstance(value, list):
                    ces.append("line%5B%5D=" + "%2C".join(str(x) for x in value))
                else:
                    raise ValueError("line must be a list or a dictionary of lists.")
            cmr_url += "?" + "&".join(ces)
            if extra:
                cmr_url += "&options%5Bline%5D%5Bor%5D=true"
        else:
            raise ValueError("`line` must be a list or a dictionary of lists.")
    if circle:
        if isinstance(circle, list):
            cmr_url += "?circle%5B%5D=" + "%2C".join(str(x) for x in circle)
        elif isinstance(circle, dict):
            ces = []
            if "Union" in circle:
                extra = circle.pop("Union", None)
            else:
                extra = False
            for key, value in circle.items():
                if isinstance(value, list):
                    ces.append("circle%5B%5D=" + "%2C".join(str(x) for x in value))
                else:
                    raise ValueError("circle must be a list or a dictionary of lists.")
            cmr_url += "?" + "&".join(ces)
            if extra:
                cmr_url += "&options%5Bcircle%5D%5Bor%5D=true"
        else:
            raise ValueError("`circle` must be a list or a dictionary of lists.")
    if point:
        if isinstance(point, list):
            cmr_url += "?point%5B%5D=" + "%2C".join(str(x) for x in point)
        elif isinstance(point, dict):
            ces = []
            if "Union" in point:
                extra = point.pop("Union", None)
            else:
                extra = False
            for key, value in point.items():
                if isinstance(value, list):
                    ces.append("point%5B%5D=" + "%2C".join(str(x) for x in value))
                else:
                    raise ValueError("point must be a list or a dictionary of lists.")
            cmr_url += "?" + "&".join(ces)
            if extra:
                cmr_url += "&options%5Bpoint%5D%5Bor%5D=true"
        else:
            raise ValueError("`point` must be a list or a dictionary of lists.")

    try:
        r = session.get(cmr_url, params=params, headers=headers)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error - something went wrong: {e}")
        return None

    cmr_response = r.json()
    items = [
        cmr_response["items"][i]["umm"]["RelatedUrls"]
        for i in range(len(cmr_response["items"]))
    ]
    granules_urls = []
    for item in items:
        for i in range(len(item)):
            if (
                item[i].get("Description") == "OPeNDAP request URL"
                or item[i].get("Subtype") == "OPENDAP DATA"
            ):
                granules_urls.append(item[i]["URL"])

    return granules_urls


if __name__ == "__main__":
    fname = "/home/griessbaum/Dropbox/UCSB/pydap_cpt/pydap_notebooks/data/"
    ds = open_file(fname + "coads_climatology.nc.dmr")
    print(ds)
