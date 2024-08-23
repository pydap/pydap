import logging

from netCDF4 import Dataset

from ..handlers.lib import BaseHandler
from ..server.devel import LocalTestServer

_logger = logging.getLogger(__name__)

_private_atts = ["server"]


class NetCDF(Dataset):
    def __init__(self, dataset, *args, **kwargs):
        self.server = LocalTestServer(
            application=BaseHandler(dataset=dataset), as_process=True
        )
        self.server.start()
        super(NetCDF, self).__init__(self.server.url, *args, **kwargs)

    def __setattr__(self, name, value):
        if name in _private_atts:
            self.__dict__[name] = value
        else:
            super(Dataset, self).__setattr__(name, value)

    def __getattr__(self, name):
        if name in _private_atts:
            return self.__dict__[name]
        else:
            return super(Dataset, self).__getattr__(name)

    def __delattr__(self, name):
        if name not in _private_atts:
            super(Dataset, self).__delattr__(name)

    def close(self):
        # Shutdown server on close:
        self.server.shutdown()

        # Close but without checking for error:
        Dataset._close(self, False)
