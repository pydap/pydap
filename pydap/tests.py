from wsgi_intercept import add_wsgi_intercept, httplib2_intercept
httplib2_intercept.install()

from pydap.lib import isiterable
from pydap.handlers.lib import SimpleHandler


def UnitTestServer(dataset, host='localhost', port=8080, script_name=''):
    """
    A quick fake server for Pydap datasets.

    """
    app = SimpleHandler(dataset)
    add_wsgi_intercept(host, port, lambda: app, script_name=script_name)
    return app


def to_list(L):
    """
    Convert an iterable object to a list.

    Works with nested iterables.
    """
    if isiterable(L): return [to_list(item) for item in L]
    else: return L
