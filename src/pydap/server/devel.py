import math
import multiprocessing
import socket
import sys
import threading
import time
from wsgiref.simple_server import make_server

import numpy as np
from requests.exceptions import HTTPError
from webob.request import Request

from ..handlers.lib import BaseHandler
from ..model import BaseType, DatasetType
from ..net import get_response

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


def run_server_in_process(httpd, shutdown, **kwargs):
    _server = threading.Thread(target=httpd.serve_forever, kwargs=kwargs)
    _server.start()
    shutdown.wait()
    httpd.shutdown()
    _server.join()


class LocalTestServer(object):
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
    ...     dataset = open_url("http://localhost:%s" % server.port, protocol='dap2')
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
    >>> dataset = open_url("http://localhost:%s" % server.port, protocol='dap2')
    >>> dataset
    <DatasetType with children 'byte', 'string', 'short'>
    >>> print(dataset['byte'].data[:])
    [0 1 2 3 4]
    >>> server.shutdown()
    """

    def __init__(
        self,
        application=BaseHandler(DefaultDataset),
        port=None,
        wait=0.5,
        polling=1e-2,
        as_process=False,
    ):
        self._port = port or get_open_port()
        self.application = application
        self._wait = wait
        self._polling = polling
        self._as_process = as_process
        self._address = "0.0.0.0"

    @property
    def url(self):
        return "http://{0}:{1}/".format(self._address, self.port)

    def start(self):
        # Start a simple WSGI server:
        application = self.application

        self._httpd = make_server(self._address, self.port, application)
        kwargs = {"poll_interval": 0.1}

        if self._as_process:
            self._shutdown = multiprocessing.Event()
            if sys.platform in ["darwin", "win32"]:
                # see https://github.com/python/cpython/issues/77906
                # no long term solution, simply temporaty fix
                ctx = multiprocessing.get_context("fork")
                Process = ctx.Process
            else:
                Process = multiprocessing.Process
            self._server = Process(
                target=run_server_in_process,
                args=(self._httpd, self._shutdown),
                kwargs=kwargs,
            )
        else:
            self._server = threading.Thread(
                target=self._httpd.serve_forever, kwargs=kwargs
            )

        self._server.start()
        self.poll_server()

    def poll_server(self):
        # Poll the server
        ok = False
        for trial in range(int(math.ceil(self._wait / self._polling))):
            try:
                # When checking whether server has started, do
                # not verify ssl:
                resp = get_response(
                    Request.blank(self.url + ".dds"), self.application, verify=False
                )
                ok = resp.status_code == 200
            except HTTPError:
                pass
            if ok:
                break
            time.sleep(self._polling)

        if not ok:
            self.shutdown()
            raise Exception(
                (
                    "LocalTestServer did not start in {0}s. "
                    "Try using LocalTestServer(..., wait={1}"
                ).format(self._wait, 2 * self._wait)
            )

    @property
    def port(self):
        return self._port

    def __enter__(self):
        self.start()
        return self

    def shutdown(self):
        # Tell the server to shutdown:
        if self._as_process:
            self._shutdown.set()
        else:
            self._httpd.shutdown()
        self._server.join()
        self._httpd.server_close()

    def __exit__(self, *_):
        self.shutdown()
