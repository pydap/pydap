from pydap.lib import __version__, __dap__
from pydap.responses.lib import BaseResponse


class VersionResponse(BaseResponse):
    def __init__(self, dataset=None):
        BaseResponse.__init__(self, dataset)
        self.headers.extend([
                ('Content-description', 'dods_version'),
                ('Content-type', 'text/plain'),
                ])

    @staticmethod
    def serialize(dataset):
        output = """Core version: dods/%s
Server version: pydap/%s
""" % ('.'.join(str(d) for d in __dap__), '.'.join(str(d) for d in __version__))

        if hasattr(dataset, 'close'): dataset.close()
        return [output]

