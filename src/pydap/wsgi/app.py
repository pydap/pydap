"""A file-based pydap server running on Gunicorn.

Usage:
  pydap [options]

Options:
  -h --help                     Show this help message and exit
  --version                     Show pydap version
  -i --init DIR                 Create directory with templates
  -b ADDRESS --bind ADDRESS     The ip to listen to [default: 127.0.0.1]
  -p PORT --port PORT           The port to connect [default: 8001]
  -d DIR --data DIR             The directory with files [default: .]
  -t DIR --templates DIR        The directory with templates
  --workers INT                 Number of workers [default: 1]
  --threads INT                 Number of threads [default: 1]
  --worker-class=CLASS          Gunicorn worker class [default: sync]
"""

import importlib.resources
import mimetypes
import os
import re
import shutil
from datetime import datetime

from docopt import docopt
from gunicorn.app.wsgiapp import WSGIApplication
from jinja2 import ChoiceLoader, Environment, FileSystemLoader, PackageLoader

# from requests.utils import unquote
from webob import Response
from webob.dec import wsgify
from webob.exc import HTTPForbidden, HTTPNotFound
from webob.static import DirectoryApp, FileApp

from ..exceptions import ExtensionNotSupportedError
from ..handlers.lib import get_handler, load_handlers
from ..lib import __version__, unquote
from .ssf import ServerSideFunctions


class DapServer(object):
    """A directory app that creates file listings and handle DAP requests."""

    def __init__(self, path, templates=None):
        self.path = os.path.abspath(path)

        # the default loader reads templates from the package
        loaders = [PackageLoader("pydap.wsgi", "templates")]

        # optionally, the user can also specify a template directory that will
        # override the default templates; this should have precedence over the
        # default templates
        if templates is not None:
            loaders.insert(0, FileSystemLoader(templates))

        # set the rendering environment; this is also used by pydap responses
        # that need to render templates (like HTML, WMS, KML, etc.)
        self.env = Environment(loader=ChoiceLoader(loaders))
        self.env.filters["datetimeformat"] = datetimeformat
        self.env.filters["datetimeformat_iso"] = datetimeformat_iso
        self.env.filters["unquote"] = unquote

        # cache available handlers, so we don't need to load them every request
        self.handlers = load_handlers()

    @wsgify
    def __call__(self, req):
        """WSGI application callable.

        Returns either a file download, directory listing or DAP response.

        """
        path = os.path.abspath(os.path.join(self.path, *req.path_info.split("/")))

        if not path.startswith(self.path):
            return HTTPForbidden()
        if path.endswith("catalog.xml"):
            return self.index(os.path.dirname(path), req, catalog=True)
        elif os.path.exists(path):
            if os.path.isdir(path):
                return self.index(path, req)
            else:
                return FileApp(path)

        # strip DAP extension (``.das``, eg) and see if the file exists
        base, ext = os.path.splitext(path)
        if os.path.isfile(base):
            req.environ["pydap.jinja2.environment"] = self.env
            app = ServerSideFunctions(get_handler(base, self.handlers))
            return req.get_response(app)
        else:
            return HTTPNotFound(comment=path)

    def index(self, directory, req, catalog=False):
        """Return a directory listing."""

        template_name = "index.html"
        response_content_type = "text/html"
        content = [os.path.join(directory, name) for name in os.listdir(directory)]

        files = [
            {
                "name": os.path.split(path)[1],
                "size": os.path.getsize(path),
                "last_modified": datetime.fromtimestamp(os.path.getmtime(path)),
                "supported": supported(path, self.handlers),
            }
            for path in content
            if os.path.isfile(path)
        ]
        files.sort(key=lambda d: alphanum_key(d["name"]))

        directories = [
            {
                "name": os.path.split(path)[1],
                "last_modified": datetime.fromtimestamp(os.path.getmtime(path)),
            }
            for path in content
            if os.path.isdir(path)
        ]
        directories.sort(key=lambda d: alphanum_key(d["name"]))

        tokens = req.path_info.split("/")[1:]
        breadcrumbs = [
            {
                "url": "/".join([req.application_url] + tokens[: i + 1]),
                "title": token,
            }
            for i, token in enumerate(tokens)
            if token
        ]

        context = {
            "root": req.application_url,
            "location": req.path_url,
            "breadcrumbs": breadcrumbs,
            "directories": directories,
            "files": files,
            "version": __version__,
        }

        if catalog:
            context["location"] = req.path.replace("catalog.xml", "")
            template_name = "catalog.xml"
            response_content_type = "application/xml"

        template = self.env.get_template(template_name)
        return Response(
            body=template.render(context),
            content_type=response_content_type,
            charset="utf-8",
        )


def supported(filepath, handlers=None):
    """Test if a file has a corresponding handler.

    Returns a boolean.

    """
    try:
        get_handler(filepath, handlers, instantiate=False)
        return True
    except ExtensionNotSupportedError:
        return False


def alphanum_key(s):
    """Parse a string, returning a list of string and number chunks.

        >>> alphanum_key("z23a")
        ['z', 23, 'a']

    Useful for sorting names in a natural way.

    From http://nedbatchelder.com/blog/200712.html#e20071211T054956

    """

    def tryint(s):
        try:
            return int(s)
        except Exception:
            return s

    return [tryint(c) for c in re.split("([0-9]+)", s)]


def datetimeformat(value, format="%Y-%m-%d %H:%M:%S"):
    """Return a formatted datetime object."""
    return value.strftime(format)


def datetimeformat_iso(value):
    """Return a formatted datetime object as ISO8601 representation."""
    return value.isoformat()


class StaticMiddleware(object):
    """WSGI middleware for static assets.

    The assets can be either specified as a directory, or retrieved from a
    Python package. Inspired by ``werkezeug.wsgi.SharedDataMiddleware``.

    """

    def __init__(self, app, static):
        self.app = app
        self.static = static

    @wsgify
    def __call__(self, req):
        if req.path_info_peek() != "static":
            return req.get_response(self.app)

        # strip "/static"
        req.path_info_pop()

        # statically serve the directory
        if isinstance(self.static, str):
            return req.get_response(DirectoryApp(self.static))

        # otherwise, load resource from package
        package, resource_path = self.static
        parts = resource_path.split("/")
        resources_path = importlib.resources.files(package)
        for i in range(len(parts)):
            resources_path /= parts[i]
        resource = req.path_info.split("/")[-1]
        full_path = resources_path / resource

        if not full_path.is_file():
            return HTTPNotFound(req.path_info)

        content_type, content_encoding = mimetypes.guess_type(full_path)
        package += (".").join([""] + parts)
        return Response(
            body=importlib.resources.read_text(package, resource),
            content_type=content_type,
            content_encoding=content_encoding,
        )


def init(directory):
    """Create directory with default templates."""
    # copy main templates
    templates = importlib.resources.files("pydap.wsgi") / "templates"
    with importlib.resources.as_file(templates) as path:
        shutil.copytree(templates, directory)

    # copy templates from HTML response
    for resource in importlib.resources.files(
        "pydap.responses.html.templates"
    ).iterdir():
        path = importlib.resources.files(
            "pydap.responses.html"
        ) / "templates/{0}".format(resource.name)
        with importlib.resources.as_file(path) as Path:
            shutil.copy(Path, directory)


class PyDapApplication(WSGIApplication):
    """An application interface for configuring and loading
    the various necessities for a given web framework."""

    def __init__(self, app, **local_config):

        self._app = app
        self._config = local_config
        self._config["bind"] = "%s:%s" % (
            local_config.pop("host", ""),
            local_config.pop("port", ""),
        )

        WSGIApplication.__init__(self)

    def load_config(self):
        for k, v in self._config.items():
            if v is not None:
                self.cfg.set(k.lower(), v)

    def load(self):
        return self._app


def main():  # pragma: no cover
    """Run server from the command line."""

    arguments = docopt(__doc__, version="pydap %s" % __version__)

    # init templates?
    if arguments["--init"]:
        init(arguments["--init"])
        return

    # create pydap app
    data, templates = arguments["--data"], arguments["--templates"]
    app = DapServer(data, templates)

    # configure app so that is reads static assets from the template directory
    # or from the package
    if templates and os.path.exists(os.path.join(templates, "static")):
        static = os.path.join(templates, "static")
    else:
        static = ("pydap.wsgi", "templates/static")
    app = StaticMiddleware(app, static)

    # configure WSGI server
    pydap_app = PyDapApplication(
        app,
        host=arguments["--bind"],
        port=int(arguments["--port"]),
        workers=arguments["--workers"],
        threads=arguments["--threads"],
        worker_class=arguments["--worker-class"],
    )
    pydap_app.run()


if __name__ == "__main__":
    main()
