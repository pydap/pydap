import multiprocessing
import sys
import time

from werkzeug.serving import run_simple

from ..handlers.lib import BaseHandler
from ..wsgi.ssf import ServerSideFunctions
from .devel import DefaultDataset, LocalTestServer


def run_simple_server(
    application=BaseHandler(DefaultDataset), port=8000, ssl_context=None
):
    application = ServerSideFunctions(application)

    def app_check_for_shutdown(environ, start_response):
        if environ["PATH_INFO"].endswith("shutdown"):
            shutdown_server(environ)
            return shutdown_application(environ, start_response)
        else:
            return application(environ, start_response)

    run_simple("0.0.0.0", port, app_check_for_shutdown, ssl_context=ssl_context)


def shutdown_server(environ):
    pass
    # if 'werkzeug.server.shutdown' not in environ:
    #    raise RuntimeError('Not running the development server')
    # environ['werkzeug.server.shutdown']()


def shutdown_application(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"Server is shutting down."]


class LocalTestServerSSL(LocalTestServer):
    """
    Simple server instance that can be used to test pydap.
    Relies on multiprocessing and is usually slow (it has to
    start and shutdown which typically takes ~2 sec).

    Usage:
    >>> import numpy as np
    >>> import time
    >>> from pydap.handlers.lib import BaseHandler
    >>> from pydap.model import DatasetType, BaseType
    >>> DefaultDataset = DatasetType("Default")
    >>> DefaultDataset["byte"] = BaseType("byte", np.arange(5, dtype="B"))
    >>> DefaultDataset["string"] = BaseType("string", np.array(["one", "two"]))
    >>> DefaultDataset["short"] = BaseType("short", np.array(1, dtype="h"))
    >>> DefaultDataset
    <DatasetType with children 'byte', 'string', 'short'>

    As an instance:
    >>> from pydap.client import open_url
    >>> application = BaseHandler(DefaultDataset)
    >>> with LocalTestServerSSL(application) as server:
    ...     time.sleep(0.1)
    ...     dataset = open_url("http://localhost:%s" % server.port)


    Or by managing connection and deconnection:
    >>> server = LocalTestServerSSL(application)
    >>> server.start()
    >>> time.sleep(0.1)
    >>> dataset = open_url("http://localhost:%s" % server.port)
    >>> dataset
    <DatasetType with children 'byte', 'string', 'short'>
    >>> print(dataset['byte'].data[:])
    [0 1 2 3 4]
    >>> print(dataset['string'].data[:])
    [b'one' b'two']
    >>> print(dataset['short'].data[:])
    1
    >>> server.shutdown()
    """

    def __init__(
        self,
        application=BaseHandler(DefaultDataset),
        port=None,
        wait=0.5,
        polling=1e-2,
        as_process=False,
        ssl_context=None,
    ):
        super(LocalTestServerSSL, self).__init__(
            application, port, wait, polling, as_process
        )
        self._ssl_context = ssl_context

    @property
    def url(self):
        if self._ssl_context is None:
            return "http://{0}:{1}/".format(self._address, self.port)
        else:
            return "https://{0}:{1}/".format(self._address, self.port)

    def start(self):
        if sys.platform in ["darwin", "win32"]:
            # see https://github.com/python/cpython/issues/77906
            # no long term solution, simply temporaty fix
            ctx = multiprocessing.get_context("fork")
            Process = ctx.Process
        else:
            Process = multiprocessing.Process

        # Start a simple WSGI server:
        self._server = Process(
            target=run_simple_server,
            args=(self.application, self.port, self._ssl_context),
        )
        self._server.start()
        # Wait a little while for the server to start:
        self.poll_server()

    # https://werkzeug.palletsprojects.com/en/2.2.x/serving/#shutting-down-the-server
    def shutdown(self):
        # Shutdown the server:
        time.sleep(self._wait)
        self._server.terminate()
        del self._server
