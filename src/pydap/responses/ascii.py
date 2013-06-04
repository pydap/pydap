from pydap.model import *
from pydap.lib import walk
from pydap.responses.lib import BaseResponse


class ASCIIResponse(BaseResponse):
    def __init__(self, dataset):
        BaseResponse.__init__(self, dataset)
        self.headers.extend([
            ('Content-description', 'dods_ascii'),
            ('Content-type', 'text/plain; charset=utf-8'),
        ])

    def __iter__(self):
        for line in dispatch(self.dataset):
            yield line

        if hasattr(self.dataset, 'close'):
            self.dataset.close()


def dispatch(var):
    if isinstance(var, SequenceType):
        yield var.id + '\n'
        yield ', '.join(var.keys()) + '\n'
        for rec in var:
            yield ', '.join(map(str, rec)) + '\n'
    elif isinstance(var, StructureType):
        for child in var:
            for line in dispatch(child):
                yield line
    else:
        yield var.id + '\n'
        for block in var.data:
            yield str(block.tolist()) + '\n'
