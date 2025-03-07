import ssl
import warnings

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import HTTPError
from requests.utils import urlparse, urlunparse
from requests_cache import CachedSession
from urllib3 import Retry
from webob.request import Request as webob_Request

from .lib import DEFAULT_TIMEOUT, _quote


def GET(
    url,
    application=None,
    session=None,
    timeout=DEFAULT_TIMEOUT,
    verify=True,
    use_cache=False,
    session_kwargs=None,
    cache_kwargs=None,
    get_kwargs=None,
):
    """Open a remote URL returning a requests.GET object

    Parameters:
    -----------
        url: str
            open a remote URL
        application: a WSGI application object | None
            When set, we are dealing with a local application, and a webob.response is
            returned. When None, a requests.Response object is returned.
        session: requests.Session() | None
            object (potentially) containing authentication cookies.
        timeout: int | None (default: 512)
            timeout in seconds.
        verify: bool (default: True)
            verify SSL certificates
        session_kwargs: dict | None
            keyword arguments used to create a new session object. Only used if
            session is None.
        cache_kwargs: dict | None
            keyword arguments used to create a new cache object. Only used if
            use_cache is True.
        get_kwargs: dict | None
            optional dict containing keyword arguments passed to `requests.get`.

    Returns:
    --------
        response: requests.Response object | webob.Response object
    """
    if application:
        _, _, path, _, query, fragment = urlparse(url)
        url = urlunparse(("", "", path, "", _quote(query), fragment))

    res = create_request(
        url,
        application=application,
        session=session,
        timeout=timeout,
        verify=verify,
        use_cache=use_cache,
        session_kwargs=session_kwargs,
        cache_kwargs=cache_kwargs,
        get_kwargs=get_kwargs,
    )
    if isinstance(res, webob_Request):
        res = get_response(res, application, verify=verify)
        # requests library automatically decodes the response
        res.decode_content()
    return res


def get_response(req, application=None, verify=True):
    """
    If verify=False, use the ssl library to temporarily disable
    ssl verification.
    """
    if verify:
        resp = req.get_response(application)
    else:
        # Here, we use monkeypatching. Webob does not provide a way
        # to bypass SSL verification.
        # This approach is never ideal but it appears to be the only option
        # here.
        # This only works in python 2.7 and >=3.5. Python 3.4
        # does not require it because by default contexts are not
        # verified.
        try:
            _create_default_https_ctx = ssl._create_default_https_context
            _create_unverified_ctx = ssl._create_unverified_context
            ssl._create_default_https_context = _create_unverified_ctx
        except AttributeError:
            _create_default_https_ctx = None

        try:
            resp = req.get_response(application)
        finally:
            if _create_default_https_ctx is not None:
                # Restore verified context
                ssl._create_default_https_context = _create_default_https_ctx
    return resp


def create_request(
    url,
    application=None,
    timeout=DEFAULT_TIMEOUT,
    verify=True,
    session=None,
    use_cache=False,
    session_kwargs=None,
    cache_kwargs=None,
    get_kwargs=None,
):
    """
    Creates a requests.get request object for a local or remote url.
    If application is set, then we are dealing with a local application
    and we need to create a webob request object.

    Parameters:
    -----------
        url: str
            open a remote URL
        application: a WSGI application object | None
            When set, we are dealing with a local application, and a webob.response is
            returned. When None, a requests.Response object is returned.
        timeout: int | None (default: 512)
            timeout in seconds.
        verify: bool (default: True)
            verify SSL certificates
        session: requests.Session() | None
            object (potentially) containing authentication cookies. If not set,
            a new session is created, but not returned. Only the request object is
            returned. Thus, the session will not be persisted.
        use_cache: bool
        session_kwargs: dict | None
            keyword arguments used to create a new session object. Only used if
            session is None.
        cache_kwargs: dict | None
            keyword arguments used to create a new cache object. Only used if
            use_cache is True.
        get_kwargs: dict | None
            Dict containing optional keyword arguments passed to `requests.get`.
    """
    if application:
        # local dataset, webob request.
        req = webob_Request.blank(url)
        req.environ["webob.client.timeout"] = timeout
        return req
    else:
        get_kwargs = get_kwargs or {}
        # remote dataset, requests request.
        if session is None:
            args = {
                "use_cache": use_cache,
                "session_kwargs": session_kwargs,
                "cache_kwargs": cache_kwargs,
            }
            session = create_session(**args)
        if "Authorization" in session.headers:
            get_kwargs["auth"] = None
        req = session.get(
            url, timeout=timeout, verify=verify, allow_redirects=True, **get_kwargs
        )
        try:
            req.raise_for_status()
            return req
        except HTTPError as http_err:
            raise HTTPError(
                f"HTTP Error occurred {http_err} - Failed to fetch data from `{url}`"
            ) from http_err


def create_session(
    use_cache=False,
    session_kwargs=None,
    cache_kwargs=None,
):
    """
    Creates a request.Session object with the specified parameters.

    Parameters:
    -----------
        use_cache: bool (default: False)
            use cache to store requests. Uses the `requests_cache` library.
        session_kwargs: dict | None
            keyword arguments used to create a new session object. Only used if
            session is None. Included here are options for `retry_args`, which are
            then passed as Retry object to the session via requests.HTTPAdapter
        cache_kwargs: dict | None
            keyword arguments used to create a new cache object. Only used if
            use_cache is True. When `None`, and `use` is `True`, the default
            cache settings used are as follows: {
                "cache_name": "http_cache",
                "backend": "sqlite",
                "use_temp": True,
                "expire_after": 86400, # 1 day default
            }
            See `requests_cache` documentation for more information.
    Returns:
        session: requests.Session()
    """
    session_kwargs = session_kwargs or {}
    token = session_kwargs.pop("token", None)
    cache_kwargs = cache_kwargs or {}
    if use_cache:
        expire_after = cache_kwargs.pop("expire_after", None)
        if not expire_after:
            expire_after = 86400  # default
        else:
            if not isinstance(expire_after, int):
                raise ValueError(
                    f"expire_after must be an integer, not {type(expire_after)}"
                )
        if len(cache_kwargs) == 0:
            cache_kwargs = {
                "cache_name": "http_cache",
                "backend": "sqlite",
                "use_temp": True,
                "expire_after": expire_after,
            }
            # Create a new session with cache
        session = CachedSession(**{**session_kwargs, **cache_kwargs})
    else:
        if len(cache_kwargs) > 0:
            warnings.warn(
                "`cache_kwargs` are being set, but use_cache is `False`. "
                " when `use_cache` is `False`, `cache_kwargs` are ignored."
                " set `use_cache` to `True` to use `cache_kwargs`, or remove "
                "`cache_kwargs`. ",
                category=UserWarning,
                stacklevel=1,
            )
        # Create a new session with user-specified kwargs
        session = requests.Session()
        for key, value in session_kwargs.items():
            setattr(session, key, value)
    # Handle retry arguments separately
    retry_args = session_kwargs.pop("retry_args", {})
    if "total" not in retry_args:
        retry_args.setdefault("total", 5)
    if "status_forcelist" not in retry_args:
        retry_args.setdefault("status_forcelist", [500, 502, 503, 504])
    if "backoff_factor" not in retry_args:
        retry_args.setdefault("backoff_factor", 0.1)
    if "allowed_methods" not in retry_args:
        retry_args.setdefault("allowed_methods", ["GET"])

    retries = Retry(**retry_args)
    adapter = HTTPAdapter(max_retries=retries)

    # Mount the adapter to the session
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    if token:
        session.headers.update({"Authorization": f"Bearer {token}"})
    return session
