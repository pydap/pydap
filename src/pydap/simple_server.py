from webob.request import Request
import threading
import time

from werkzeug.serving import run_simple
from .handlers.csv import CSVHandler
from .wsgi.ssf import ServerSideFunctions


def run_simple_server(test_file, port=8000, handler=CSVHandler):
    application = handler(test_file)
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
    return ['Server is shutting down.']


class LocalTestServer:
    """
    Simple server instance that can be used to test pydap.
    Relies on threading and is usually slow (it has to
    start and shutdown which typically takes ~2 sec).

    Usage:
    >>> from pydap.handlers.csv import CSVHandler
    >>> from pydap.client import open_url
    >>> server = LocalTestServer("test.csv", handler=CSVHandler)
    >>> server.connect()
    >>> dataset = open_url("http://localhost:%s" % server.port)
    >>> server.disconnect()

    Or as an instance:
    >>> with LocalTestServer("test.csv", handler=CSVHandler) as server:
    >>>     dataset = open_url("http://localhost:%s" % server.port)
    """

    def __init__(self, file_name, port=8000,
                 handler=CSVHandler,
                 wait=1):
        self.file_name = file_name
        self._port = port
        self.handler = handler
        self._wait = wait

    def connect(self):
        # Start a simple WSGI server:
        self.server_process = (threading
                               .Thread(target=run_simple_server,
                                       args=(self.file_name,
                                             self.port,
                                             self.handler)))
        self.server_process.start()
        # Wait a little while for the server to start:
        time.sleep(self._wait)

    @property
    def port(self):
        return self._port

    def __enter__(self):
        self.connect()
        return self

    def disconnect(self):
        # Shutdown the server:
        (Request
         .blank("http://0.0.0.0:%s/shutdown" % self.port)
         .get_response())
        time.sleep(self._wait)
        self.server_process.join()
        del(self.server_process)

    def __exit__(self, *_):
        self.disconnect()
