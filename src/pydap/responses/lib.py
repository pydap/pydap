from pkg_resources import iter_entry_points

from pydap.model import *
from pydap.lib import __version__


def load_responses():
    return dict((r.name, r.load()) for r in iter_entry_points('pydap.response'))


class BaseResponse(object):
    def __init__(self, dataset):
        self.dataset = dataset
        self.headers = [
                ('XDODS-Server', 'pydap/%s' % __version__),
        ]

    def __call__(self, environ, start_response):
        start_response('200 OK', self.headers)
        return self

    def x_wsgiorg_parsed_response(self, type):
        if type is DatasetType:
            return self.dataset

    def __iter__(self):
        raise NotImplementedError(
            'Subclasses must implement __iter__')

    def close(self):
        if hasattr(self.dataset, 'close'):
            return self.dataset.close()
