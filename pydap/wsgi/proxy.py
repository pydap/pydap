from urlparse import urljoin

from paste.proxy import Proxy

import pydap.lib
from pydap.client import open_url
from pydap.handlers.lib import SimpleHandler


def make_proxy(global_conf, url, responses, cache=None, **kwargs):
    from paste.deploy.converters import aslist
    responses = aslist(responses)
    return DapProxy(url, responses, verbose, cache, **kwargs)


class DapProxy(object):
    def __init__(self, url, responses, cache=None):
        self.url = url
        self.responses = responses
        pydap.lib.CACHE = cache

    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO', '')
        basename, response = path_info.rsplit('.', 1)

        if response in self.responses:
            dataset = open_url( urljoin(self.url, basename) )
            app = SimpleHandler(dataset)
        else:
            app = Proxy( urljoin(self.url, path_info) )

        return app(environ, start_response)


if __name__ == '__main__':
    app = DapProxy('http://localhost:8002/', ['html', 'ascii'])
    from paste import httpserver
    httpserver.serve(app, '127.0.0.1', port=8003)
