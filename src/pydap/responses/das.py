from collections import Iterable

from pydap.model import *
from pydap.lib import encode, quote
from pydap.responses.lib import BaseResponse
from pydap.responses.dds import typemap


INDENT = ' ' * 4


class DASResponse(BaseResponse):
    def __init__(self, dataset):
        BaseResponse.__init__(self, dataset)
        self.headers.extend([
            ('Content-description', 'dods_das'),
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


def dispatch(var, level=0):
    types = [
            (DatasetType, dataset),
            (GridType, base),
            #(SequenceType, sequence),
            (StructureType, structure),
            (BaseType, base),
    ]

    for class_, func in types:
        if isinstance(var, class_):
            return func(var, level)


def build_attributes(attr, values, level=0):
    """
    Recursive function to build the DAS.
    
    """
    # check for metadata
    if isinstance(values, dict):
        yield '{indent}{attr} {{\n'.format(indent=(level)*INDENT, attr=attr)
        for k, v in values.items():
            for line in build_attributes(k, v, level+1):
                yield line
        yield '{indent}}}\n'.format(indent=(level)*INDENT)
    else:
        # get type
        type = get_type(values)

        # encode values
        if isinstance(values, basestring) or not isinstance(values, Iterable):
            values = [encode(values)]
        else:
            values = map(encode, values)

        yield '{indent}{type} {attr} {values};\n'.format(
                indent=(level)*INDENT,
                type=type,
                attr=quote(attr),
                values=', '.join(values))


def get_type(values):
    if hasattr(values, 'dtype'):
        return typemap[values.dtype.char]
    elif isinstance(values, basestring) or not isinstance(values, Iterable):
        return type_convert(values)
    else:
        # if there are several values, they may have different types, so we need
        # to convert all of them and use a precedence table
        types = map(type_convert, values)
        precedence = ['String', 'Float64', 'Int32']
        types.sort(key=precedence.index)
        return types[0]


def type_convert(obj):
    """
    Map Python objects to the corresponding Opendap types.

    """
    if isinstance(obj, float):
        return 'Float64'
    elif isinstance(obj, (long, int)):
        return 'Int32'
    else:
        return 'String'


def dataset(var, level=0):
    yield '{indent}Attributes {{\n'.format(indent=level*INDENT)

    for attr, values in var.attributes.items():
        for line in build_attributes(attr, values, level+1):
            yield line

    for child in var.children():
        for line in dispatch(child, level=level+1):
            yield line
    yield '{indent}}}\n'.format(indent=level*INDENT)


def sequence(var, level=0):
    for child in var.children():
        for line in dispatch(child, level=level):
            yield line


def structure(var, level=0):
    yield '{indent}{name} {{\n'.format(indent=level*INDENT, name=var.name)

    for attr, values in var.attributes.items():
        for line in build_attributes(attr, values, level+1):
            yield line

    for child in var.children():
        for line in dispatch(child, level=level+1):
            yield line
    yield '{indent}}}\n'.format(indent=level*INDENT)


def base(var, level=0):
    yield '{indent}{name} {{\n'.format(indent=level*INDENT, name=var.name)

    for attr, values in var.attributes.items():
        for line in build_attributes(attr, values, level+1):
            yield line
    yield '{indent}}}\n'.format(indent=level*INDENT)
