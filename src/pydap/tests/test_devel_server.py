"""
This test module uses a simple development server
to test http-specific options like timeout
or caching.

It is based on CSV data but with more handlers
it could work with more data formats.
"""

import sys
import csv
import tempfile
import multiprocessing
import os
import time
import numpy as np
from nose.plugins.attrib import attr
import warnings

from pydap.handlers.csv import CSVHandler
from werkzeug.serving import run_simple
from webob.request import Request
from webob.exc import HTTPError
from pydap.wsgi.ssf import ServerSideFunctions
from pydap.client import open_url


if sys.version_info < (2, 7):
    import unittest2 as unittest
else:
    import unittest


def run_subprocess_server(test_file):
    import subprocess
    process_script = ['python', os.path.realpath(__file__),
                      test_file]
    try:
        from subprocess import check_output
        try:
            output = check_output(' '.join(process_script),
                                  shell=True,
                                  stderr=subprocess.STDOUT)
            # Capture subprocess errors to print output:
            for line in iter(output.splitlines()):
                print(line)
        except subprocess.CalledProcessError as e:
            # Capture subprocess errors to print output:
            for line in iter(e.output.splitlines()):
                print(line)
            raise
    except ImportError:
        # Python 2.6 use a simpler check_call
        subprocess.check_call(' '.join(process_script),
                              shell=True)


def run_simple_server(test_file):
    application = CSVHandler(test_file)
    application = ServerSideFunctions(application)

    def app_check_for_shutdown(environ, start_response):
        if environ['PATH_INFO'].endswith('shutdown'):
            shutdown_server(environ)
            return shutdown_application(environ, start_response)
        else:
            return application(environ, start_response)

    run_simple('0.0.0.0', 8000,
               app_check_for_shutdown,
               use_reloader=True)


def shutdown_server(environ):
    if 'werkzeug.server.shutdown' not in environ:
        raise RuntimeError('Not running the development server')
    environ['werkzeug.server.shutdown']()


def shutdown_application(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return ['Server is shutting down.']


@attr('server')
class TestCSVserver(unittest.TestCase):

    """Test that the handler creates the correct dataset from a URL."""
    data = [(10, 15.2, 'Diamond_St'),
            (11, 13.1, 'Blacktail_Loop'),
            (12, 13.3, 'Platinum_St'),
            (13, 12.1, 'Kodiak_Trail')]

    def setUp(self):
        """Create test data"""

        # Create tempfile:
        fileno, self.test_file = tempfile.mkstemp(suffix='.csv')
        # must close file number:
        os.close(fileno)
        with open(self.test_file, 'w') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
            writer.writerow(['index', 'temperature', 'site'])
            for row in self.data:
                writer.writerow(row)

        # Start a simple WSGI server:
        self.server_process = (multiprocessing
                               .Process(target=run_subprocess_server,
                                        args=(self.test_file,)))
        time.sleep(3)
        self.server_process.start()
        # Wait a little while for the server to start:
        time.sleep(3)

    def test_open(self):
        """Test that dataset has the correct data proxies for grids."""
        url = "http://0.0.0.0:8000/" + os.path.basename(self.test_file)
        dataset = open_url(url)
        seq = dataset['sequence']
        dtype = [('index', '<i4'),
                 ('temperature', '<f8'),
                 ('station', 'S40')]
        retrieved_data = [line for line in seq]

        np.testing.assert_array_equal(np.array(retrieved_data, dtype=dtype),
                                      np.array(self.data, dtype=dtype))

    def test_timeout(self):
        """Test that timeout raises the correct HTTPError"""
        url = "http://0.0.0.0:8000/" + os.path.basename(self.test_file)
        with self.assertRaises(HTTPError):
            with warnings.catch_warnings():
                # This is for python 2.6
                warnings.filterwarnings('error',
                                        category=DeprecationWarning,
                                        message='Currently pydap does not '
                                                'support '
                                                'user-specified timeouts in '
                                                'python 2.6')
                try:
                    open_url(url, timeout=1e-8)
                except DeprecationWarning:
                    raise HTTPError

    def tearDown(self):
        # Shutdown the server:
        (Request
         .blank("http://0.0.0.0:8000/shutdown")
         .get_response())
        self.server_process.terminate()
        self.server_process.join()
        del(self.server_process)
        # Remove test file:
        os.remove(self.test_file)


if __name__ == '__main__':
    run_simple_server(sys.argv[1])
