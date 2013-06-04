from pydap.model import DatasetType
from pydap.lib import __dap__


class BaseResponse(object):
    def __init__(self, dataset):
        self.dataset = dataset
        self.headers = [
                ('XDODS-Server', 'dods/%s' % '.'.join([str(i) for i in __dap__])),
                ]

    @staticmethod
    def serialize(dataset):
        raise NotImplementedError(
                'Subclasses must implement serialize')

    def __call__(self, environ, start_response):
        headers = self.headers + environ['pydap.headers']
        start_response('200 OK', headers)

        if environ.get('x-wsgiorg.want_parsed_response'):
            return ResponseSerializer(self.dataset, self.serialize)
        else:
            return self.serialize(self.dataset)
        

class ResponseSerializer(object):
    """
    A serializer for responses that keeps the dataset
    for modification by WSGI middleware.

    Follows this specification::

      http://wsgi.org/wsgi/Specifications/avoiding_serialization

    """
    def __init__(self, dataset, serializer):
        self.dataset = dataset
        self.serializer = serializer

    def x_wsgiorg_parsed_response(self, type):
        if type is DatasetType:
            return self.dataset

    def __iter__(self):
        return iter(self.serializer(self.dataset))
