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

import pkg_resources
from webob import Request, Response, exc
from webob.static import DirectoryApp
from webob.dec import wsgify
import selector

from jinja2 import Environment, PackageLoader, FileSystemLoader, ChoiceLoader

from pydap.lib import __version__
from pydap.handlers.lib import get_handler, load_handlers


class DapServer(DirectoryApp):

    """A directory app that creates file listings and handle DAP requests."""

    def __init__(self, path, templates=None):
        super(DapServer, self).__init__(path, hide_index_with_redirect=True)

        # the default loader reads templates from the package
        loaders = [PackageLoader("pydap", "wsgi/templates")]
        if templates is not None:
            loaders.insert(0, FileSystemLoader(templates))
        self.env = Environment(loader=ChoiceLoader(loaders))
        self.env.filters["format_size"] = format_size

        # cache available handlers
        self.handlers = load_handlers()

    @wsgify
    def __call__(self, req):
        """WSGI application callable.

        We first pass the request to the super class, and if it returns 404 we
        strip the extension assuming it's a DAP request and check for an
        existing and supported file.

        """
        res = super(DapServer, self).__call__(req)
        if not isinstance(res, exc.HTTPNotFound):
            return res

        # strip DAP extension (``.das``, eg) and see if the file exists
        path = os.path.abspath(
            os.path.join(self.path, *req.path_info.split('/')))
        base, ext = os.path.splitext(path)

        if not base.startswith(self.path):
            return exc.HTTPForbidden()
        elif os.path.isfile(base):
            # pass the request to the proper handler
            req.env['pydap.jinja2.environment'] = self.env
            return req.get_response(get_handler(base, self.handlers))
        else:
            # return the original 404
            return res

    def index(self, req, path):
        """Build a directory listing."""
        directory, index = os.path.split(path)
        content = [
            os.path.join(directory, name) for name in os.listdir(directory)]

        files = [{
            "name": os.path.split(path)[1],
            "size": os.path.getsize(path),
            "modified": os.path.getmtime(path),
            "supported": supported(path, self.handlers),
        } for name in content if os.path.isfile(path)]
        files.sort(key=lambda d: alphanum_key(d['name']))

        directories = [
            os.path.split(path)[1] for path in content if os.path.isdir(path)]
        directories.sort(key=alphanum_key)

        context = {
            "directories": directories,
            "files": files,
            "version": __version__,
        }
        template = self.env.get_template("index.html")
        return Response(
            body=template.render(context),
            content_type="text/html",
            charset="utf-8")


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


def format_size(size):                                                          
    """Return file size as a human readable string."""                          
    if not size:
        return "Empty"                                                          
                                                                                
    for units in ["bytes", "KB", "MB", "GB", "TB"]:                             
        if size < 1024:                                                         
            return "%d %s" % (size, units)                                      
        size /= 1024                                                            
    return "%d PB" % size


class ResourceStaticServer(object):

    """Server for static files stored in Python package.
    
    This is used to load static assets from the package when no directory is
    specified by the user."""

    def __init__(self, package, resource_path):
        self.package = package
        self.resource_path = resource_path

    @wsgify
    def __call__(self, req):
        resource = os.path.join(
            self.resource_path, *req.path_info.split('/'))
        if not pkg_resources.resource_exists(self.package, resource):
            return exc.HTTPNotFound(req.path_info)

        content_type, content_encoding = mimetypes.guess_type(resource)
        return Response(
            body=pkg_resources.resource_string(self.package, resource),
            content_type=content_type,
            content_encoding=content_encoding)


def main():
    import multiprocessing

    from docopt import docopt
    from gunicorn.app.pasterapp import paste_server

    arguments = docopt(__doc__, version="Pydap %s" % __version__)

    # create an app to serve static files from the templates
    templates = arguments["--templates"]
    if templates and os.path.exists(os.path.join(templates, "static")):
        static = DirectoryApp(os.path.join(templates, "static"))
    else:
        # load templates from the package
        static = ResourceStaticServer("pydap", "wsgi/templates/static")

    # set the pydap server
    pydap = DapServer(arguments["--data"], templates)

    # configure the WSGI app which will route requests
    app = selector.Selector()
    app.parser = lambda x: x
    app.add("^\/static\/", GET=static)
    app.add(".*", GET=pydap, POST=pydap)

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
