from webob.request import Request
from webob.exc import HTTPError
import threading
import time
import math
import numpy as np
import socket

from werkzeug.serving import run_simple

from ..handlers.lib import BaseHandler
from ..model import BaseType, DatasetType
from ..wsgi.ssf import ServerSideFunctions

DefaultDataset = DatasetType("Default")
DefaultDataset["byte"] = BaseType("byte", np.arange(5, dtype="B"))
DefaultDataset["string"] = BaseType("string", np.array(["one", "two"]))
DefaultDataset["short"] = BaseType("short", np.array(1, dtype="h"))


def get_open_port():
    # http://stackoverflow.com/questions/2838244/
    # get-open-tcp-port-in-python/2838309#2838309
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    port = s.getsockname()[1]
    s.close()
    return port


def run_simple_server(port, application):
    application = ServerSideFunctions(application)

    def app_check_for_shutdown(environ, start_response):
        if environ['PATH_INFO'].endswith('shutdown'):
            shutdown_server(environ)
            return shutdown_application(environ, start_response)
        else:
            return application(environ, start_response)

    run_simple('0.0.0.0', port,
               app_check_for_shutdown)


def shutdown_server(environ):
    if 'werkzeug.server.shutdown' not in environ:
        raise RuntimeError('Not running the development server')
    environ['werkzeug.server.shutdown']()


def shutdown_application(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return [b'Server is shutting down.']


class LocalTestServer:
    """
    Simple server instance that can be used to test pydap.
    Relies on threading and is usually slow (it has to
    start and shutdown which typically takes ~2 sec).

    Usage:
    >>> import numpy as np
    >>> from pydap.handlers.lib import BaseHandler
    >>> from pydap.model import DatasetType, BaseType
    >>> DefaultDataset = DatasetType("Default")
    >>> DefaultDataset["byte"] = BaseType("byte", np.arange(5, dtype="B"))
    >>> DefaultDataset["string"] = BaseType("string", np.array(["one", "two"]))
    >>> DefaultDataset["short"] = BaseType("short", np.array(1, dtype="h"))
    >>> DefaultDataset
    <DatasetType with children 'byte', 'string', 'short'>
    >>> application = BaseHandler(DefaultDataset)
    >>> from pydap.client import open_url

    As an instance:
    >>> with LocalTestServer(application) as server:
    ...     dataset = open_url("http://localhost:%s" % server.port)
    ...     dataset
    ...     print(dataset['byte'].data[:])
    ...     print(dataset['string'].data[:])
    ...     print(dataset['short'].data[:])
    <DatasetType with children 'byte', 'string', 'short'>
    [0 1 2 3 4]
    [b'one' b'two']
    1

    Or by managing connection and deconnection:
    >>> server = LocalTestServer(application)
    >>> server.start()
    >>> dataset = open_url("http://localhost:%s" % server.port)
    >>> dataset
    <DatasetType with children 'byte', 'string', 'short'>
    >>> print(dataset['byte'].data[:])
    [0 1 2 3 4]
    >>> server.shutdown()
    """

    def __init__(self, application=BaseHandler(DefaultDataset),
                 port=None, wait=0.5, polling=1e-2):
        self._port = port or get_open_port()
        self.application = application
        self._wait = wait
        self._polling = polling

    def start(self):
        # Start a simple WSGI server:
        self.server_process = (threading
                               .Thread(target=run_simple_server,
                                       args=(self.port,
                                             self.application)))
        self.server_process.start()
        # Poll the server
        ok = False
        for trial in range(int(math.ceil(self._wait/self._polling))):
            try:
                resp = (Request
                        .blank("http://0.0.0.0:%s/.dds" % self.port)
                        .get_response())
                ok = (resp.status_code == 200)
            except HTTPError:
                pass
            if ok:
                break
            time.sleep(self._polling)

        if not ok:
            raise Exception(('LocalTestServer did not start in {0}s. '
                             'Try using LocalTestServer(..., wait={1}')
                            .format(self._wait, 2*self._wait))

    @property
    def port(self):
        return self._port

    def __enter__(self):
        self.start()
        return self

    def shutdown(self):
        # Shutdown the server:
        (Request
         .blank("http://0.0.0.0:%s/shutdown" % self.port)
         .get_response())
        self.server_process.join()

    def __exit__(self, *_):
        self.shutdown()
