from __future__ import annotations

import re
import ssl
import warnings
from typing import Any, Dict, Literal, Optional, Tuple, Union

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import (
    ConnectionError,
    HTTPError,
    SSLError,
)
from requests.structures import CaseInsensitiveDict
from requests.utils import urlparse, urlunparse
from requests_cache import BaseCache, CachedSession
from urllib3 import Retry
from webob.request import Request as webob_Request

from pydap.lib import DEFAULT_TIMEOUT, __version__, _quote

_BEARER_RE = re.compile(r"^\s*Bearer\s+.+", re.IGNORECASE)

Backend = Literal["sqlite", "filesystem", "memory"]


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
        timeout: int | None (default: 120)
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
        cache_kwargs = cache_kwargs or {}
        session_kwargs = session_kwargs or {}
        try:
            req = get_request(
                url,
                base_session=session,
                timeout=timeout,
                verify=verify,
                get_kwargs=get_kwargs,
                backend=cache_kwargs.pop("backend", None),
                cache_name=cache_kwargs.pop("http-cache", None),
                backend_options=cache_kwargs.pop("backend_options", None),
                cache_kwargs=cache_kwargs,
                session_kwargs=session_kwargs,
            )
            req.raise_for_status()
            return req
        except HTTPError as http_err:
            raise HTTPError(
                f"HTTP Error occurred {http_err} - Failed to fetch data from `{url}`"
            ) from http_err


def should_skip_cache(url, session):
    """helper function to see if a url is permissible to cache
    or not. Must be used after `Consolidate_metadata`
    """
    from pydap.client import try_generate_custom_key

    for cfg in getattr(session, "_dap_cache_configs", []):
        key = try_generate_custom_key(type("Req", (), {"url": url}), cfg)
        if key is False:
            return True
    return False


def create_session(
    use_cache=False,
    session_kwargs=None,
    cache_kwargs=None,
    session=None,
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
    if isinstance(session, requests.Session):
        token_auth = session.headers.get("Authorization", None)
    else:
        token_auth = None

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
    if "status" not in retry_args:
        retry_args.setdefault("status", 2)
    if "connect" not in retry_args:
        retry_args.setdefault("connect", 1)
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
    if token_auth:
        session.headers.update({"Authorization": f"{token_auth}"})
    elif token:
        session.headers.update({"Authorization": f"Bearer {token}"})
    session.headers.update({"User-Agent": "pydap/" + f"{__version__}"})
    return session


def get_request(
    url: str,
    *,
    base_session: Optional[requests.Session] = None,
    timeout: float | None = None,
    verify: bool | str = True,
    get_kwargs: Dict[str, Any] | None = None,
    # Optional explicit cache config if not inheriting from a base CachedSession
    backend: str = "sqlite",
    cache_name: str = "http-cache",
    backend_options: Dict[str, Any] | None = None,
    cache_kwargs: Dict[str, Any] | None = None,
    session_kwargs: Dict[str, Any] | None = None,
) -> requests.Response:
    s = build_session(
        base_session=base_session,
        backend_options=backend_options,
        cache_kwargs=cache_kwargs,
        session_kwargs=session_kwargs,
    )
    try:
        if isinstance(s, CachedSession):
            skip = False
            if cache_kwargs:
                skip = cache_kwargs.pop("skip", None)
            if should_skip_cache(url, s) or skip:
                with s.cache_disabled():
                    req = s.get(
                        url,
                        timeout=timeout,
                        verify=verify,
                        allow_redirects=True,
                        **(get_kwargs or {}),
                    )
            else:
                req = s.get(
                    url,
                    timeout=timeout,
                    verify=verify,
                    allow_redirects=True,
                    **(get_kwargs or {}),
                )
        else:
            req = s.get(
                url,
                timeout=timeout,
                verify=verify,
                allow_redirects=True,
                **(get_kwargs or {}),
            )
    except (ConnectionError, SSLError) as e:
        # some opendap servers do not support https, but they do support http.
        parsed = urlparse(url)
        if parsed.scheme == "https":
            http_url = urlunparse(parsed._replace(scheme="http"))
            req = s.get(
                http_url,
                timeout=timeout,
                verify=verify,
                allow_redirects=True,
                **(get_kwargs or {}),
            )
        else:
            raise e
    return req


def new_session_with_same_store(base: CachedSession, **cache_kwargs) -> CachedSession:
    """
    Create a NEW CachedSession that points to the same underlying store as `base`
    """
    backend, cache_name = cache_store_id(base)
    if backend == "custom":
        # Unknown backend: reuse the object explicitly (Option 1 behavior)
        return CachedSession(backend=cache_name, **cache_kwargs)
    return CachedSession(
        backend=backend,
        cache_name=cache_name,
        **cache_kwargs,
    )


def inherit_bearer_header(target: requests.Session, base: requests.Session) -> None:
    src: CaseInsensitiveDict = getattr(base, "headers", CaseInsensitiveDict())
    val = src.get("Authorization")
    if val and _BEARER_RE.match(val):
        target.headers["Authorization"] = val.strip()


def build_session(
    *,
    base_session: Optional[requests.Session],  # may be CachedSession or plain Session
    backend_options: Dict[str, Any] | None = None,
    cache_kwargs: Dict[str, Any] | None = None,
    session_kwargs: Dict[str, Any] | None = None,
) -> requests.Session:
    backend_options = backend_options or {}
    cache_kwargs = cache_kwargs or {}
    session_kwargs = session_kwargs or {}

    if isinstance(base_session, CachedSession):

        s: requests.Session = new_session_with_same_store(base_session, **cache_kwargs)
        if base_session.settings.key_fn:
            s.settings.key_fn = base_session.settings.key_fn
    else:
        s = requests.Session(**session_kwargs)

    # Copy only the Bearer token header (if present)
    if base_session is not None:
        inherit_bearer_header(s, base_session)

    # Handle retry arguments separately
    retry_args = session_kwargs.pop("retry_args", {})
    if "total" not in retry_args:
        retry_args.setdefault("total", 5)
    if "status" not in retry_args:
        retry_args.setdefault("status", 2)
    if "connect" not in retry_args:
        retry_args.setdefault("connect", 1)
    if "status_forcelist" not in retry_args:
        retry_args.setdefault("status_forcelist", [500, 502, 503, 504])
    if "backoff_factor" not in retry_args:
        retry_args.setdefault("backoff_factor", 0.1)
    if "allowed_methods" not in retry_args:
        retry_args.setdefault("allowed_methods", ["GET"])

    retries = Retry(**retry_args)
    adapter = HTTPAdapter(max_retries=retries)

    # Mount the adapter to the session
    s.mount("http://", adapter)
    s.mount("https://", adapter)

    return s


def _as_cache(obj: Union[CachedSession, BaseCache]) -> BaseCache:
    return obj.cache if hasattr(obj, "cache") else obj


def detect_backend(obj: Union[CachedSession, BaseCache]) -> Backend:
    cache = _as_cache(obj)
    module = type(cache).__module__.lower()

    # Positive attribute checks first
    if hasattr(cache, "db_path"):
        return "sqlite"
    if hasattr(cache, "cache_dir"):
        return "filesystem"

    if module.endswith("requests_cache.backends.base"):
        # fallback to memory as backend
        return "memory"


def cache_store_id(obj: Union[CachedSession, BaseCache]) -> Tuple[Backend, str]:
    cache = _as_cache(obj)
    kind = detect_backend(cache)
    if kind == "sqlite":
        return kind, str(getattr(cache, "db_path"))
    if kind == "filesystem":
        return kind, str(getattr(cache, "cache_dir"))
    if kind == "memory":
        return kind, getattr(cache, "cache_name", type(cache).__name__)
