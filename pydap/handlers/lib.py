import sys
import re
import logging

from pkg_resources import iter_entry_points
from paste.httpexceptions import HTTPException
from paste.deploy.converters import asbool

from pydap.lib import parse_qs
from pydap.handlers.helper import constrain
from pydap.responses.error import ErrorResponse
from pydap.exceptions import ExtensionNotSupportedError


def load_handlers():
    return [ep.load() for ep in iter_entry_points("pydap.handler")]


def get_handler(filepath, handlers=None):
    # Check each handler to see which one handles this file.
    for handler in handlers or load_handlers():
        p = re.compile(handler.extensions)
        if p.match(filepath):
            return handler(filepath)

    raise ExtensionNotSupportedError(
            'No handler available for file %s.' % filepath)


class BaseHandler(object):
    """
    Base class for pydap handlers.

    This class is the base class for the different handlers. The job
    of building a given dataset from a given request is passed to the
    ``parse_constraints`` method, which should be defined in each
    specific handler. The dataset is then passed to a response class,
    which is simply a WSGI application that is returned.

    """

    # Load all the different supported responses (DDS/DAS/etc.).
    response_map = dict((r.name, r.load())
            for r in iter_entry_points('pydap.response'))

    def __call__(self, environ, start_response):
        path_info = environ.get('PATH_INFO') or environ.get('SCRIPT_NAME', '')
        path_info = path_info.lstrip('/')
        path, type_ = path_info.rsplit('.', 1)
        # For DAS, we need to clear the constraint expression to get the
        # full dataset.
        if type_ == 'das': environ['QUERY_STRING'] = ''

        # Add some vars to the environment.
        environ['pydap.path'] = path
        environ['pydap.response'] = type_
        environ['pydap.ce'] = parse_qs(environ.get('QUERY_STRING', ''))
        environ['pydap.logger'] = logging.getLogger('pydap')
        environ['pydap.headers'] = []  # additional headers
        
        try:
            # Build the dataset using the proper subclass method and
            # pass it to a response (DAS/DDS/etc.) builder.
            dataset = self.parse_constraints(environ)
            response = self.response_map[type_]
            responder = response(dataset)
            return responder(environ, start_response)
        except HTTPException, exc:
            # Some responses (like HTML) raise an HTTPRedirect when the
            # form is posted, so we need this here.
            return exc(environ, start_response)
        except:
            # We silently capture and format exceptions, unless this
            # environ flag says otherwise.
            if asbool(environ.get('x-wsgiorg.throw_errors')):
                raise
            return ErrorResponse(info=sys.exc_info())(environ, start_response)
        
    def parse_constraints(self, environ):
        raise NotImplementedError(
                'Subclasses must implement parse_constraints')


class SimpleHandler(BaseHandler):
    """
    A simple handler for ``dap.model.DatasetType`` datasets.

    This handler takes care of datasets built by hand from the types in
    ``pydap.model``.

    """
    def __init__(self, dataset, debug=False):
        self.dataset = dataset
        self.debug = debug

    def parse_constraints(self, environ):
        """
        Parse the request.

        This method uses the magic ``constrain`` function, which handles
        arbitrary datasets/constraint expressions according to the DAP spec.

        """
        environ['x-wsgiorg.throw_errors'] = self.debug
        new_dataset = constrain(self.dataset, environ.get('QUERY_STRING', ''))
        if hasattr(self.dataset, 'close'): self.dataset.close()
        return new_dataset
