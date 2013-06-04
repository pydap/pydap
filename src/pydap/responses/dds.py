from pydap.model import *
from pydap.responses.lib import BaseResponse


INDENT = ' ' * 4

typemap = {
        'd': 'Float64',
        'f': 'Float32',
        'h': 'Int16',
        'i': 'Int32', 'l': 'Int32', 'q': 'Int32',
        'b': 'Byte',
        'H': 'UInt16',
        'I': 'UInt32', 'L': 'UInt32', 'Q': 'UInt32',
        'B': 'Byte',
        'S': 'String',
        'U': 'String',
}


class DDSResponse(BaseResponse):
    def __init__(self, dataset):
        BaseResponse.__init__(self, dataset)
        self.headers.extend([
            ('Content-description', 'dods_dds'),
            ('Content-type', 'text/plain; charset=utf-8'),

            # CORS
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Headers',
                'Origin, X-Requested-With, Content-Type'),
        ])

    def __iter__(self):
        for line in dispatch(self.dataset):
            yield line

        if hasattr(self.dataset, 'close'):
            self.dataset.close()


def dispatch(var, level=0, sequence=0):
    types = [
            (DatasetType, structure('Dataset')),
            (SequenceType, structure('Sequence')),
            (GridType, grid),
            (StructureType, structure('Structure')),
            (BaseType, base),
    ]

    for class_, func in types:
        if isinstance(var, class_):
            return func(var, level, sequence)


def structure(type):
    def func(var, level=0, sequence=0):
        if type == 'Sequence':
            sequence += 1

        yield '{indent}{type} {{\n'.format(indent=level*INDENT, type=type)

        # Get the DDS from stored variables.
        for child in var.children():
            for line in dispatch(child, level+1, sequence):
                yield line
        yield '{indent}}} {name};\n'.format(indent=level*INDENT, name=var.name)
    return func


def grid(var, level=0, sequence=0):
    yield '{indent}Grid {{\n'.format(indent=level*INDENT)

    yield '{indent}Array:\n'.format(indent=(level+1)*INDENT)
    for line in base(var.array, level+2, sequence):
        yield line

    yield '{indent}Maps:\n'.format(indent=(level+1)*INDENT)
    for map_ in var.maps.values():
        for line in base(map_, level+2, sequence):
            yield line

    yield '{indent}}} {name};\n'.format(indent=level*INDENT, name=var.name)


def base(var, level=0, sequence=0):
    shape = var.shape[sequence:]

    if var.dimensions:
        shape = ''.join(map('[{0[0]} = {0[1]}]'.format, zip(var.dimensions, shape)))
    elif len(shape) == 1:
        shape = '[{} = {}]'.format(var.name, shape[0])
    else:
        shape = ''.join('[{}]'.format(len) for len in shape)

    yield '{indent}{type} {name}{shape};\n'.format(
            indent=level*INDENT,
            type=typemap[var.dtype.char], 
            name=var.name,
            shape=shape)
