"""Basic functions for handlers.

pydap handlers are responsible for reading data in different formats -- NetCDF,
SQL databases, CSV files, etc. -- and convert them into the internal data model
so that the data may be served using different responses.

"""

from __future__ import division

import ast
import copy
import itertools
import operator
import re
import sys
from importlib.metadata import entry_points

import numpy as np
from numpy.lib import Arrayterator
from webob import Request

from pydap.exceptions import ConstraintExpressionError, ExtensionNotSupportedError
from pydap.lib import encode, fix_shorthand, get_var, walk
from pydap.model import BaseType, DatasetType, GridType, SequenceType, StructureType
from pydap.parsers import parse_ce, parse_selection
from pydap.responses.error import ErrorResponse
from pydap.responses.lib import load_responses

# buffer size in bytes, for streaming data
BUFFER_SIZE = 2**27

CORS_RESPONSES = ["dds", "das", "dods", "ver", "json", "dmr"]


def load_handlers():
    r"""Load all handlers, returning them on a list."""
    eps = entry_points(group="pydap.handler")
    Rs = [r for r in eps if r.module[:5] == "pydap"]
    nRs = [r for r in eps if r.module[:5] != "pydap"]
    base_dict = dict((r.name, r.load()) for r in Rs)

    opts_dict = dict((r.name, r.load()) for r in nRs)
    base_dict.update(opts_dict)
    return base_dict.values()


def get_handler(filepath, handlers=None, instantiate=True):
    """Given a filepath, return the corresponding instantiated handler."""
    # Check each handler to see which one handles this file.
    for handler in handlers or load_handlers():
        p = re.compile(handler.extensions)
        if p.match(filepath):
            # only check if extension is supported - don't return instance
            if not instantiate:
                return None
            return handler(filepath)

    raise ExtensionNotSupportedError(
        "No handler available for file {filepath}.".format(filepath=filepath)
    )


class BaseHandler(object):
    """Base class for pydap handlers.

    Handlers are WSGI applications that parse the client request and build the
    corresponding dataset. The dataset is passed to proper Response (DDS, DAS,
    etc.)

    """

    # load all available responses
    #    import pdb; pdb.set_trace()
    responses = load_responses()

    def __init__(self, dataset=None, gzip=False):
        self.dataset = dataset
        self.additional_headers = []
        self._gzip = gzip

    def __call__(self, environ, start_response):
        req = Request(environ)
        path, response = req.path.rsplit(".", 1)
        if response == "das":
            req.query_string = ""
        projection, selection = parse_ce(req.query_string)
        buffer_size = environ.get("pydap.buffer_size", BUFFER_SIZE)

        try:
            # build the dataset and pass it to the proper response, returning a
            # WSGI app
            dataset = self.parse(projection, selection, buffer_size)
            app = self.responses[response](dataset)
            app.close = self.close

            # now build a Response and set additional headers
            res = req.get_response(app)
            for key, value in self.additional_headers:
                res.headers.add(key, value)

            # CORS for Javascript requests
            if response in CORS_RESPONSES:
                res.headers.add("Access-Control-Allow-Origin", "*")
                res.headers.add(
                    "Access-Control-Allow-Headers",
                    "Origin, X-Requested-With, Content-Type",
                )

            if self._gzip:
                res.encode_content()
            return res(environ, start_response)
        except Exception:
            # should the exception be catched?
            if environ.get("x-wsgiorg.throw_errors"):
                raise
            else:
                res = ErrorResponse(info=sys.exc_info())
                return res(environ, start_response)

    def parse(self, projection, selection, buffer_size=BUFFER_SIZE):
        """Parse the constraint expression, returning a new dataset."""
        if self.dataset is None:
            raise NotImplementedError(
                "Subclasses must define a ``dataset`` attribute pointing to a"
                "``DatasetType`` object."
            )

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

    def close(self):
        """Optional method for closing the dataset."""
        pass


def wrap_arrayterator(dataset, size):
    """Wrap `BaseType` objects in an Arrayterator.

    This function is used to optimize access to huge datasets. It returns a new
    dataset with data wrapped in Arrayterators. This way the data is read in
    blocks instead of buffering everything in memory.

    Since the buffer size of the Arrayterator is in elements, not bytes, we
    convert according to the data item size.

    """
    for var in walk(dataset, BaseType):
        if (
            not isinstance(var.data, Arrayterator)
            and var.data.dtype.itemsize
            and var.data.shape
        ):
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
            condition
            for condition in selection
            if re.match(r"%s\.[^\.]+(<=|<|>=|>|=|!=)" % re.escape(seq.id), condition)
        ]
        for condition in conditions:
            id1, op, id2 = parse_selection(condition, dataset)
            seq.data = seq[op(id1, id2)].data
    return dataset


def degenerate_grid_to_structure(candidate):
    if isinstance(candidate, GridType):
        candidate = StructureType(candidate.name, candidate.attributes)
    return candidate


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
                        # A shallow copy of the candidate is created
                        candidate = candidate.__shallowcopy__()
                        # Grids are degenerated into Structures
                        candidate = degenerate_grid_to_structure(candidate)
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
                else:
                    raise ConstraintExpressionError("Invalid projection!")

    return out


class ConstraintExpression(object):
    """An object representing a selection on a constraint expression.

    These can be accumulated so that they are evaluated only once.

    """

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def __and__(self, other):
        """Join two CEs together, returning a new object."""
        return self.__class__(self.value + "&" + str(other))

    def __or__(self, other):
        raise ConstraintExpressionError(
            "OR constraints not allowed in the Opendap specification."
        )


class IterData(object):
    """Class for manipulating data streams as structured arrays.

    A structured array is a Numpy construct that has some very interesting
    properties for working with tabular data.

    """

    shape = ()

    def __init__(self, stream, template, ifilter=None, imap=None, islice=None, level=0):
        self.stream = stream
        self.template = template
        self.level = level

        # these are used to lazily evaluate the data stream
        self.ifilter = ifilter or []
        self.imap = imap or [fix_nested(template)]
        self.islice = islice or []

    @property
    def dtype(self):
        """Return Numpy dtype of the object."""

        def array_dtype(x, template):
            if hasattr(template, "keys") and len(list(template.keys())) > 1:
                peek = x
                if isinstance(x, IterData):
                    peek = next(iter(x))
                return np.dtype(
                    [
                        (col, array_dtype(val, template[col]))
                        for col, val in zip(template.keys(), peek)
                    ]
                )
            else:
                return np.array(x).dtype

        return array_dtype(next(iter(self)), self.template)

    def iterdata(self):
        """Included for code symmetry with Types"""
        return iter(self)

    def __iter__(self):
        data = iter(self.stream)

        for f in self.ifilter:
            data = filter(f, data)
        for m in self.imap:
            data = map(m, data)
        for s in self.islice:
            data = itertools.islice(data, s.start, s.stop, s.step)

        return data

    def __copy__(self):
        """Return a lightweight copy of the object."""
        return IterData(
            self.stream,
            copy.copy(self.template),
            self.ifilter[:],
            self.imap[:],
            self.islice[:],
            self.level,
        )

    def __repr__(self):
        return "<IterData to stream %r>" % self.stream

    def __getitem__(self, key):
        out = copy.copy(self)

        # return a child, and adjust the data so that only the corresponding
        # column is returned
        if isinstance(key, str):
            try:
                col = list(self.template._all_keys()).index(key)
            except ValueError:
                raise KeyError(key)
            out.level += 1
            out.template = out.template[key]
            out.imap.append(deep_map(operator.itemgetter(col), out.level))

        # return a new sequence with the selected children
        elif isinstance(key, list):
            cols = [list(self.template.keys()).index(k) for k in key]
            out.template._visible_keys = key
            out.imap.append(
                deep_map(lambda row: tuple(row[i] for i in cols), out.level + 1)
            )

        # slice the data
        elif isinstance(key, (int, slice)):
            if isinstance(key, int):
                out.islice.append(slice(key, key + 1))
            else:
                out.islice.append(key)

        # filter the data; like slicing it, we can use ``itertools.ifilter``
        # only if the selection is applied to the outermost sequence, otherwise
        # we need to do a deep map
        elif isinstance(key, ConstraintExpression):
            f, m = build_filter(key, self.template)
            out.ifilter.append(f)
            out.imap.append(m)

        else:
            raise KeyError(key)

        return out

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            right = other.template.id
        else:
            right = encode(other)
        return ConstraintExpression("%s=%s" % (self.template.id, right))

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            right = other.template.id
        else:
            right = encode(other)
        return ConstraintExpression("%s!=%s" % (self.template.id, right))

    def __ge__(self, other):
        if isinstance(other, self.__class__):
            right = other.template.id
        else:
            right = encode(other)
        return ConstraintExpression("%s>=%s" % (self.template.id, right))

    def __le__(self, other):
        if isinstance(other, self.__class__):
            right = other.template.id
        else:
            right = encode(other)
        return ConstraintExpression("%s<=%s" % (self.template.id, right))

    def __gt__(self, other):
        if isinstance(other, self.__class__):
            right = other.template.id
        else:
            right = encode(other)
        return ConstraintExpression("%s>%s" % (self.template.id, right))

    def __lt__(self, other):
        if isinstance(other, self.__class__):
            right = other.template.id
        else:
            right = encode(other)
        return ConstraintExpression("%s<%s" % (self.template.id, right))


def fix_nested(template):
    """Apply ``IterData`` to nested sequences on iteration."""

    def func(row):
        return tuple(
            IterData(col, child) if isinstance(child, SequenceType) else col
            for col, child in zip(row, template.children())
        )

    return func


def deep_map(function, level):
    """Map a function inside a nested list, returning the modified data."""

    def out(row, level=level):
        if level == 1:
            return function(row)
        else:
            return [out(value, level - 1) for value in row]

    return out


def build_filter(expression, template):
    """Return a filter function based on a comparison expression."""
    id1, op, id2 = re.split("(<=|>=|!=|=~|>|<|=)", str(expression), 1)

    # calculate the column index were filtering and how deep it is
    try:
        id1 = id1[len(template.id) + 1 :]
        target = template
        for level, token in enumerate(id1.split(".")):
            parent1 = target.id
            keys = list(target._all_keys())
            col = keys.index(token)
            target = target[token]
        a = operator.itemgetter(col)
    except Exception:
        raise ConstraintExpressionError(
            'Invalid constraint expression: "{expression}" '
            '("{id}" is not a valid variable)'.format(expression=expression, id=id1)
        )

    # if we're comparing two variables they must be on the same sequence, so
    # ``parent1`` must be equal to ``parent2``
    if id2.rsplit(".", 1)[0] == parent1:  # parent2 == parent1
        keys = list(template._all_keys())
        col = keys.index(id2.split(".")[-1])
        b = operator.itemgetter(col)
    else:
        try:
            value = ast.literal_eval(id2)

            def b(row):
                return value

        except Exception:
            raise ConstraintExpressionError(
                'Invalid constraint expression: "{expression}" '
                '("{id}" is not valid)'.format(expression=expression, id=id2)
            )

    op = {
        "<": operator.lt,
        ">": operator.gt,
        "!=": operator.ne,
        "=": operator.eq,
        ">=": operator.ge,
        "<=": operator.le,
        "=~": lambda a, b: re.match(b, a),
    }[op]

    # if the filtering is applied in the outermost sequence we can simply pass
    # a filter, and ignore the map
    if level == 0:

        def f(row):
            return op(a(row), b(row))

        def m(row):
            return row

    # if the filtering is applied to a nested sequence we actually need to map
    # the outer data so that the inner data is filtered
    else:
        f = bool

        def recurse(row, tokens, target):
            token = tokens.pop(0)

            # return the filtered inner data
            if not tokens:
                return [col for col in row if op(a(col), b(col))]

            # navigate inside the sequence
            col = list(target.keys()).index(token)
            target = target[col]

            # modify data in place; we need to convert tuple to list
            row = list(row)
            row[col] = recurse(row[col], tokens, target)
            return tuple(row)

        def m(row):
            tokens = id1.split(".")
            return recurse(row, tokens, template)

    return f, m
