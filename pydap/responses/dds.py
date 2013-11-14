from pydap.model import *
from pydap.lib import INDENT
from pydap.responses.lib import BaseResponse


class DDSResponse(BaseResponse):
    def __init__(self, dataset):
        BaseResponse.__init__(self, dataset)
        self.headers.extend([
                ('Content-description', 'dods_dds'),
                ('Content-type', 'text/plain; charset=utf-8'),
                ])

    @staticmethod
    def serialize(dataset):
        output = ''.join(dispatch(dataset)).encode("utf-8")
        if hasattr(dataset, 'close'): dataset.close()
        return [output]


def dispatch(var, level=0):
    dispatchers = [(DatasetType, structure_builder('Dataset')),
                   (SequenceType, structure_builder('Sequence')),
                   (GridType, _grid),
                   (StructureType, structure_builder('Structure')),
                   (BaseType, _base)]

    for klass, func in dispatchers:
        if isinstance(var, klass):
            return func(var, level)


def structure_builder(name):
    def func(var, level=0):
        yield '%s%s {\n' % (level * INDENT, name)

        # Get the DDS from stored variables.
        for child in var.walk():
            for line in dispatch(child, level=level+1):
                yield line
        yield '%s} %s;\n' % (level * INDENT, var.name)
    return func


def _grid(var, level=0):
    yield '%sGrid {\n' % (level * INDENT)

    yield '%sArray:\n' % ((level+1) * INDENT)
    for line in _base(var.array, level=level+2):
        yield line

    yield '%sMaps:\n' % ((level+1) * INDENT)
    for map_ in var.maps.values():
        for line in _base(map_, level=level+2):
            yield line

    yield '%s} %s;\n' % (level * INDENT, var.name)


def _base(var, level=0):
    if var.dimensions:
        dims = ['%s = %d' % dim for dim in zip(var.dimensions, var.shape)]
    else:
        if len(var.shape) == 1:
            dims = ['%s = %d' % (var.name, var.shape[0])]
        else:
            dims = ['%d' % i for i in var.shape]
    shape = dims and '[%s]' % ']['.join(dims) or ''
    yield '%s%s %s%s;\n' % (level * INDENT, var.type.descriptor, var.name, shape)
