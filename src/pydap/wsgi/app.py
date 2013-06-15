"""A file-based Pydap server running on Gunicorn.

Usage: 
  pydap [options]

Options:
  -h --help                     Show this help message and exit
  --version                     Show version
  -b ADDRESS --bind ADDRESS     The ip to listen to [default: 127.0.0.1]
  -p PORT --port PORT           The port to connect [default: 8001]
  -d DIR --data DIR             The directory with files [default: .]
  -t dIR --templates DIR        The directory with templates
  --worker-class=CLASS          Gunicorn worker class [default: sync]
  
"""

import os
import re
import mimetypes
from datetime import datetime

from jinja2 import Environment, PackageLoader, FileSystemLoader, ChoiceLoader
from werkzeug.wrappers import Request, Response
from werkzeug.wsgi import responder
from werkzeug.exceptions import Unauthorized, NotFound

from pydap.lib import __version__
from pydap.handlers.lib import get_handler, load_handlers
from pydap.exceptions import ExtensionNotSupportedError


class DapServer(object):

    """A directory app that creates file listings and handle DAP requests."""

    def __init__(self, path, templates=None):
        self.path = os.path.abspath(path)

        # the default loader reads templates from the package
        loaders = [PackageLoader("pydap", "wsgi/templates")]

        # optionally, the user can specify a template directory that will 
        # override the default templates
        if templates is not None:
            loaders.insert(0, FileSystemLoader(templates))

        # set the environment; this is also used by pydap responses that need
        # to render templates (like HTML, WMS, KML, etc.)
        self.env = Environment(loader=ChoiceLoader(loaders))
        self.env.filters["formatsize"] = formatsize
        self.env.filters["datetimeformat"] = datetimeformat

        # cache available handlers
        self.handlers = load_handlers()

    @responder
    def __call__(self, environ, start_response):
        """WSGI application callable."""
        request = Request(environ)
        path = os.path.abspath(
            os.path.join(self.path, *request.path.split('/')))

        if not path.startswith(self.path):
            return Unauthorized()
        elif os.path.exists(path):
            if os.path.isdir(path):
                return self.index(path, request)
            else:
                return Response(open(path), direct_passthrough=True)

        # strip DAP extension (``.das``, eg) and see if the file exists
        path, ext = os.path.splitext(path)
        if os.path.isfile(path):
            request.environ['pydap.jinja2.environment'] = self.env
            return get_handler(path, self.handlers)
        else:
            return NotFound()

    def index(self, directory, request):
        """Build a directory listing."""
        content = [
            os.path.join(directory, name) for name in os.listdir(directory)]

        files = [{
            "name": os.path.split(path)[1],
            "size": os.path.getsize(path),
            "last_modified": datetime.fromtimestamp(os.path.getmtime(path)),
            "supported": supported(path, self.handlers),
        } for path in content if os.path.isfile(path)]
        files.sort(key=lambda d: alphanum_key(d["name"]))

        directories = [{
            "name": os.path.split(path)[1],
            "last_modified": datetime.fromtimestamp(os.path.getmtime(path)),
        } for path in content if os.path.isdir(path)]
        directories.sort(key=lambda d: alphanum_key(d["name"]))

        tokens = directory[len(self.path):].split('/')[1:]
        breadcrumbs = [{
            "url": request.url_root + '/'.join(tokens[:i+1]),
            "title": token,
        } for i, token in enumerate(tokens)]

        context = {
            "root": request.url_root,
            "breadcrumbs": breadcrumbs,
            "directories": directories,
            "files": files,
            "version": __version__,
        }
        template = self.env.get_template("index.html")
        return Response(
            response=template.render(context),
            content_type="text/html; charset=utf-8")


def supported(filepath, handlers=None):
    """Test if a file has a corresponding handler.

    Returns a boolean.

    """
    try:
        get_handler(filepath, handlers)
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
        except:
            return s
    return [tryint(c) for c in re.split('([0-9]+)', s)]


def formatsize(size):                                                          
    """Return file size as a human readable string."""                          
    if not size:
        return "Empty"                                                          
                                                                                
    for units in ["bytes", "KB", "MB", "GB", "TB"]:                             
        if size < 1024:                                                         
            return "%d %s" % (size, units)                                      
        size /= 1024                                                            
    return "%d PB" % size


def datetimeformat(value, format='%Y-%m-%d %H:%M:%S'):
    """Return a formatted datetime object."""
    return value.strftime(format)


def main():
    import multiprocessing

    from docopt import docopt
    from gunicorn.app.pasterapp import paste_server
    from werkzeug.wsgi import SharedDataMiddleware

    arguments = docopt(__doc__, version="Pydap %s" % __version__)

    # create pydap app
    data, templates = arguments["--data"], arguments["--templates"]
    app = DapServer(data, templates)
    
    # configure app so that is reads static assets from the template directory
    # or from the package
    if templates and os.path.exists(os.path.join(templates, "static")):
        static = os.path.join(templates, "static")
    else:
        static = ("pydap", "wsgi/templates/static")
    app = SharedDataMiddleware(app, {
        '/static': static,
    })

    # configure WSGI server
    workers = multiprocessing.cpu_count() * 2 + 1
    paste_server(
        app, 
        host=arguments["--bind"],
        port=int(arguments["--port"]),
        workers=workers,
        worker_class=arguments["--worker-class"])


if __name__ == "__main__":
    main()
