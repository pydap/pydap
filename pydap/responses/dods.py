import numpy 

from pydap.responses.dds import dispatch as dds_dispatch
from pydap.responses.lib import BaseResponse
from pydap.xdr import DapPacker
from pydap.lib import walk
from pydap.model import *


class DODSResponse(BaseResponse):
    def __init__(self, dataset):
        BaseResponse.__init__(self, dataset)
        self.headers.extend([
                ('Content-description', 'dods_data'),
                ('Content-type', 'application/octet-stream'),
                ])

        size = calculate_size(dataset)
        if size is not None:
            self.headers.append(('Content-length', size))

    @staticmethod
    def serialize(dataset):
        # Generate DDS.
        for line in dds_dispatch(dataset):
            yield line
        yield 'Data:\n'
        for line in DapPacker(dataset):
            yield line
        if hasattr(dataset, 'close'): dataset.close()


def calculate_size(dataset):
    size = 0
    for var in walk(dataset):
        # Pydap can't calculate the size of a dataset with a 
        # Sequence since the data is streamed directly.
        if (isinstance(var, SequenceType) or
                (isinstance(var, BaseType) and
                    var.type in [Url, String])):
            return None
        elif isinstance(var, BaseType):
            # account for array size marker
            if var.shape:
                size += 8
            # calculate size
            if var.shape == ():
                vsize = 1
            else:
                vsize = numpy.prod(var.shape)
            if var.type == Byte:
                size += -vsize % 4
            else:
                size += vsize * var.type.size

    # account for DDS
    size += len(''.join(dds_dispatch(dataset))) + len('Data:\n')
    return str(size)
