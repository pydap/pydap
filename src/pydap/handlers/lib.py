"""Basic functions for handlers.

Pydap handlers are responsible for reading data in different formats -- NetCDF,
SQL databases, CSV files, etc. -- and convert them into the internal data model
so that the data may be served using different responses.

"""

from __future__ import division

import sys
import re
import operator
import itertools
import ast
import copy

import numpy as np
from webob import Request
import pkg_resources
from numpy.lib.arrayterator import Arrayterator

from pydap.responses.lib import load_responses
from pydap.responses.error import ErrorResponse
from pydap.parsers import parse_ce, parse_selection
from pydap.exceptions import (
    ConstraintExpressionError, ExtensionNotSupportedError)
from pydap.lib import walk, fix_shorthand, get_var, encode
from pydap.model import *


# buffer size in bytes, for streaming data
BUFFER_SIZE = 2**27

CORS_RESPONSES = ['dds', 'das', 'dods', 'ver', 'json']


def load_handlers(working_set=pkg_resources.working_set):
    r"""Load all handlers, returning them on a list.

    Passing ``working_set`` is used only for unit testing. Check the following
    discussion for an explanation about this:

        http://grokbase.com/t/python/distutils-sig/074rc4a6hb/ \
                distutils-programmatically-adding-entry-points

    """
    return [ep.load() for ep in working_set.iter_entry_points("pydap.handler")]


def get_handler(filepath, handlers=None):
    """Given a filepath, return the corresponding instantiated handler."""
    # Check each handler to see which one handles this file.
    for handler in handlers or load_handlers():
        p = re.compile(handler.extensions)
        if p.match(filepath):
            return handler(filepath)

    raise ExtensionNotSupportedError(
        'No handler available for file {filepath}.'.format(filepath=filepath))


class BaseHandler(object):

    """Base class for Pydap handlers.

    Handlers are WSGI applications that parse the client request and build the
    corresponding dataset. The dataset is passed to proper Response (DDS, DAS,
    etc.)

    """

    # load all available responses
    responses = load_responses()

    def __init__(self, dataset=None):
        self.dataset = dataset
        self.additional_headers = []

    def __call__(self, environ, start_response):
        req = Request(environ)
        path, response = req.path.rsplit('.', 1)
        if response == 'das':
            req.query_string = ''
        projection, selection = parse_ce(req.query_string)
        buffer_size = environ.get('pydap.buffer_size', BUFFER_SIZE)

        try:
            # build the dataset and pass it to the proper response, returning a
            # WSGI app
            dataset = self.parse(projection, selection, buffer_size)
            app = self.responses[response](dataset)

            # now build a Response and set additional headers
            res = req.get_response(app)
            for key, value in self.additional_headers:
                res.headers.add(key, value)

            # CORS for Javascript requests
            if response in CORS_RESPONSES:
                res.headers.add('Access-Control-Allow-Origin', '*')
                res.headers.add(
                    'Access-Control-Allow-Headers',
                    'Origin, X-Requested-With, Content-Type')

            return res(environ, start_response)
        except:
            # should the exception be catched?
            if environ.get('x-wsgiorg.throw_errors'):
                raise
            else:
                res = ErrorResponse(info=sys.exc_info())
                return res(environ, start_response)

    def parse(self, projection, selection, buffer_size=BUFFER_SIZE):
        """Parse the constraint expression, returning a new dataset."""
        if self.dataset is None:
            raise NotImplementedError(
                "Subclasses must define a ``dataset`` attribute pointing to a"
                "``DatasetType`` object.")

        # make a copy of the dataset, so we can filter sequences inplace
        dataset = copy.copy(self.dataset)

        # apply the selection to the dataset, inplace
        apply_selection(selection, dataset)

        # wrap data in Arrayterator, to optimize projection/selection
        dataset = wrap_arrayterator(dataset, buffer_size)

        # fix projection
        if projection:
            projection = fix_shorthand(projection, dataset)
        else:
            projection = [[(key, ())] for key in dataset.keys()]
        dataset = apply_projection(projection, dataset)

        return dataset


def wrap_arrayterator(dataset, size):
    """Wrap `BaseType` objects in an Arrayterator.

    This function is used to optimize access to huge datasets. It returns a new
    dataset with data wrapped in Arrayterators. This way the data is read in
    blocks instead of buffering everything in memory.

    Since the buffer size of the Arrayterator is in elements, not bytes, we
    convert according to the data item size.

    """
    for var in walk(dataset, BaseType):
        if (not isinstance(var.data, Arrayterator) and
                var.data.dtype.itemsize and var.data.shape):
            elements = size // var.data.dtype.itemsize
            var.data = Arrayterator(var.data, elements)

    return dataset


def apply_selection(selection, dataset):
    """Apply a given selection to a dataset, modifying it inplace.

    Returns the original dataset.

    """
    for seq in walk(dataset, SequenceType):
        # apply only relevant selections
        conditions = [
            condition for condition in selection
            if re.match(
                '%s\.[^\.]+(<=|<|>=|>|=|!=)' % re.escape(seq.id), condition)]
        for condition in conditions:
            id1, op, id2 = parse_selection(condition, dataset)
            seq.data = seq[op(id1, id2)].data
    return dataset


def apply_projection(projection, dataset):
    """Apply a given projection to a dataset.

    This function builds and returns a new dataset by adding those variables
    that were requested on the projection.

    """
    out = DatasetType(name=dataset.name, attributes=dataset.attributes)

    # first collect all the variables
    for p in projection:
        target, template = out, dataset
        for i, (name, slice_) in enumerate(p):
            candidate = template[name]

            # add variable to target
            if isinstance(candidate, StructureType):
                if name not in target.keys():
                    if i < len(p) - 1:
                        # if there are more children to add we need to clear
                        # the candidate so it has only explicitly added
                        # children; also, Grids are degenerated into Structures
                        if isinstance(candidate, GridType):
                            candidate = StructureType(
                                candidate.name, candidate.attributes)
                        candidate._keys = []
                    target[name] = candidate
                target, template = target[name], template[name]
            else:
                target[name] = candidate

    # fix sequence data to include only variables that are in the sequence
    for seq in walk(out, SequenceType):
        seq.data = get_var(dataset, seq.id)[tuple(seq.keys())].data

    # apply slices
    for p in projection:
        target = out
        for name, slice_ in p:
            target, parent = target[name], target

            if slice_:
                if isinstance(target, BaseType):
                    target.data = target[slice_]
                elif isinstance(target, SequenceType):
                    parent[name] = target[slice_[0]]
                elif isinstance(target, GridType):
                    parent[name] = target[slice_]

    return out


class ConstraintExpression(object):

    """An object representing a selection on a constraint expression.

    These can be accumulated so that they are evaluated only once.

    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def __unicode__(self):
        return unicode(self.value)

    def __and__(self, other):
        """Join two CEs together, returning a new object."""
        return self.__class__(self.value + '&' + str(other))

    def __or__(self, other):
        raise ConstraintExpressionError(
            "OR constraints not allowed in the Opendap specification.")


class IterData(object):

    """Class for manipulating complex data streams as structured arrays.

    A structured array is a Numpy construct that has some very interesting
    properties for working with tabular data:

    """

    shape = ()

    def __init__(self, stream, descr, names=None, ifilter=None, imap=None,
                 islice=None):
        self.descr = descr
        self.names = names or descr
        self.stream = self.fix(stream, self.names)

        # these are used to lazily evaluate the data stream
        self.ifilter = ifilter or []
        self.imap = imap or []
        self.islice = islice or []

        self.id = self.names[0]
        self.level = 1

    def fix(self, stream, names):
        """Wrap nested data."""
        wrap = lambda row, names=names: tuple(
            col if isinstance(name, basestring)
            else IterData(col, ("%s.%s" % (names[0], name[0]), name[1]))
            for col, name in zip(row, names[1]))
        return map(wrap, stream)

    def __repr__(self):
        return repr(self.stream)

    @property
    def dtype(self):
        """Return Numpy dtype of the object."""
        if isinstance(self.names, basestring):
            peek = iter(self).next()
            return np.array(peek).dtype
        else:
            return [(name, self[name].dtype) for name in self.names[1]]

    def __iter__(self):
        data = iter(self.stream)

        for f in self.ifilter:
            data = itertools.ifilter(f, data)
        for m in self.imap:
            data = itertools.imap(m, data)
        for s in self.islice:
            data = itertools.islice(data, s.start, s.stop, s.step)

        return data

    def __copy__(self):
        """Return a lightweight copy of the object."""
        return IterData(self.stream, self.descr, self.names, self.ifilter[:],
                        self.imap[:], self.islice[:])

    def __getitem__(self, key):
        out = copy.copy(self)
        out.level = self.level

        # return a child, and adjust the data so that only the corresponding
        # column is returned
        if isinstance(key, basestring):
            out.id = "%s.%s" % (self.id, key)
            out.level += 1
            for col, obj in enumerate(self.names[1]):
                if key == obj:
                    out.names = out.id
                    break
                elif isinstance(obj, tuple) and key == obj[0]:
                    out.names = out.id, obj[1]
                    break
            else:
                raise KeyError(key)
            out.imap.append(deepmap(operator.itemgetter(col), out.level-1))

        # return a new sequence with the selected children; data is adjusted
        # accordingly, and order is changed following the request using a DSU
        elif isinstance(key, list):
            children = []
            for col, obj in enumerate(self.names[1]):
                if obj in key:
                    children.append((key.index(obj), col, obj))
                elif isinstance(obj, tuple) and obj[0] in key:
                    children.append((key.index(obj[0]), col, obj))
            children.sort()
            out.names = self.id, tuple(child for pos, col, child in children)
            indexes = [col for pos, col, child in children]
            out.imap.append(deepmap(
                lambda row: [row[i] for i in indexes], out.level))

        # slice the data; if ``self`` is the main sequence the data can be
        # sliced using ``itertools.islice``, but if it's a child variable the
        # slicing must be applied deeper in the data
        elif isinstance(key, (int, slice)):
            if out.level > 1:
                out.imap.append(deepmap(lambda data: data[key], out.level-1))
            elif isinstance(key, int):
                out.islice.append(slice(key, key+1))
            else:
                out.islice.append(key)

        # filter the data; like slicing it, we can use ``itertools.ifilter``
        # only if the selection is applied to the outermost sequence, otherwise
        # we need to do a deep map
        elif isinstance(key, ConstraintExpression):
            f, level = build_filter(key, self.descr)
            if level > 1:
                out.imap.append(deepmap(lambda data: filter(f, data), level-1))
            else:
                out.ifilter.append(f)

        return out

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            right = other.id
        else:
            right = encode(other)
        return ConstraintExpression('%s=%s' % (self.id, right))

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            right = other.id
        else:
            right = encode(other)
        return ConstraintExpression('%s!=%s' % (self.id, right))

    def __ge__(self, other):
        if isinstance(other, self.__class__):
            right = other.id
        else:
            right = encode(other)
        return ConstraintExpression('%s>=%s' % (self.id, right))

    def __le__(self, other):
        if isinstance(other, self.__class__):
            right = other.id
        else:
            right = encode(other)
        return ConstraintExpression('%s<=%s' % (self.id, right))

    def __gt__(self, other):
        if isinstance(other, self.__class__):
            right = other.id
        else:
            right = encode(other)
        return ConstraintExpression('%s>%s' % (self.id, right))

    def __lt__(self, other):
        if isinstance(other, self.__class__):
            right = other.id
        else:
            right = encode(other)
        return ConstraintExpression('%s<%s' % (self.id, right))


def deepmap(function, level):
    """Map a function inside a nested list, returning the modified data."""
    def out(row, level=level):
        if level == 1:
            return function(row)
        else:
            return [out(value, level-1) for value in row]
    return out


def build_filter(expression, descr):
    """Return a filter function based on a comparison expression."""
    id1, op, id2 = re.split('(<=|>=|!=|=~|>|<|=)', str(expression), 1)

    # get the list of variables in the sequence
    descr = descr,
    base1, name1 = id1.rsplit(".", 1)
    level = 0
    for token in base1.split("."):
        level += 1
        for obj in descr:
            if isinstance(obj, tuple) and token == obj[0]:
                descr = obj[1]
                break

    try:
        a = operator.itemgetter(descr.index(name1))
    except:
        raise ConstraintExpressionError(
            'Invalid constraint expression: "{expression}"'
            '("{id}" is not a valid variable)'.format(
                expression=expression, id=id1))

    # if we're comparing two variables they must be on the same sequence, so
    # ``base1`` must be equal to ``base2``
    if id2.rsplit(".", 1)[0] == base1:  # base2 == base1
        b = operator.itemgetter(descr.index(id2.rsplit(".")[-1]))
    else:
        try:
            value = ast.literal_eval(id2)
            b = lambda row, value=value: value
        except:
            raise ConstraintExpressionError(
                'Invalid constraint expression: "{expression}"'
                '("{id}" is not valid)'.format(
                    expression=expression, id=id2))

    op = {
        '<':  operator.lt,
        '>':  operator.gt,
        '!=': operator.ne,
        '=':  operator.eq,
        '>=': operator.ge,
        '<=': operator.le,
        '=~': lambda a, b: re.match(b, a),
    }[op]

    f = lambda row, op=op, a=a, b=b: op(a(row), b(row))

    return f, level
