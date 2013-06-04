"""
A simple Pydap server configured through YAML.

Usage: pydap [options] <config.yaml>

Options:
  -h --help                 Show this help message and exit
  -i IP --ip=IP             The ip to listen to [default: 127.0.0.1]
  -p PORT --port=PORT       The port to connect [default: 8001]

The configuration syntax is based on Google App Engine:

    name: my-server
    version: 1
    api_version: 1

    handlers:
    - url: /model
      dir: /path/to/files

    - url: /pirata
      file: /path/to/file.sql

In the example above the dataset defined in the `file.sql` will be available
at http://localhost:8001/pirata. All files in the `/path/to/files` directory
will be available under the /model path.

A listing of all served files can be found in http://localhost:8001/catalog.json

"""
import os
from stat import ST_MTIME
import re
from threading import Lock

import yaml
from webob import Request, Response
from simplejson import dumps

from pydap.handlers.lib import get_handler


class DapServer(object):
    def __init__(self, filepath):
        self.filepath = filepath
        self.mtime = None
        self.lock = Lock()

    @property
    def config(self):
        """
        Read configuration if it has changed.

        """
        mtime = os.stat(self.filepath)[ST_MTIME]
        if self.mtime is None or self.mtime < mtime:
            with self.lock:
                with open(self.filepath, 'Ur') as fp:
                    self._config = yaml.load(fp)
                self.mtime = mtime
        return self._config

    def __call__(self, environ, start_response):
        req = Request(environ)

        if req.path_info == '/catalog.json':
            urls = list(self.catalog(req))
            res = Response(
                    body=dumps(urls, indent=4),
                    content_type='application/json',
                    charset='utf-8')
        else:
            for handler in self.config['handlers']:
                if re.match(handler['url'], req.path):
                    if 'file' in handler:
                        res = get_handler(handler['file'])
                    elif 'dir' in handler:
                        path = req.path[len(handler['url'].rstrip('/'))+1:].rsplit('.', 1)[0]
                        filepath = os.path.join(handler['dir'], path)
                        res = get_handler(filepath)
                    break
            else:
                res = Response(status='404 Not Found')

        return res(environ, start_response)

    def catalog(self, req):
        """
        Return a JSON listing of the datasets served.

        """
        for handler in self.config['handlers']:
            if 'file' in handler:
                yield req.application_url + handler['url']
            elif 'dir' in handler:
                for root, dirs, files in os.walk(handler['dir']):
                    for filename in files:
                        yield req.application_url + handler['url'] + os.path.abspath(os.path.join(root, filename))[len(handler['dir']):]


def main():
    from docopt import docopt
    from werkzeug.serving import run_simple

    arguments = docopt(__doc__)
    app = DapServer(arguments['<config.yaml>'])
    run_simple(arguments['--ip'], int(arguments['--port']), app)


if __name__ == '__main__':
    main()
