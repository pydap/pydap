"""Response with information about pydap version."""

import sys
from json import dumps

from pkg_resources import iter_entry_points
from webob import Response

from ..lib import __dap__, __version__


class VersionResponse(object):
    """A specialized response for debugging.

    This is a special response used to display information about the server.

    """

    __version__ = __version__

    def __init__(self, dataset):
        output = {
            "pydap": __version__,
            "dap": __dap__,
            "handlers": dict(
                (ep.name, getattr(ep.load(), "__version__", "Unknown"))
                for ep in iter_entry_points("pydap.handler")
            ),
            "responses": dict(
                (ep.name, getattr(ep.load(), "__version__", "Unknown"))
                for ep in iter_entry_points("pydap.response")
            ),
            "functions": dict(
                (ep.name, getattr(ep.load(), "__version__", "Unknown"))
                for ep in iter_entry_points("pydap.function")
            ),
            "python": sys.version,
        }
        self.body = dumps(output, indent=4)

    def __call__(self, environ, start_response):
        res = Response()
        res.text = str(self.body)
        res.status = "200 OK"
        res.content_type = "application/json"
        res.charset = "utf-8"
        res.headers.add("Content-description", "dods_version")
        res.headers.add("XDODS-Server", "pydap/%s" % __version__)

        return res(environ, start_response)
