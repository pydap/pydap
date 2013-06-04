from __future__ import division

import sys
import re
import operator
import itertools
import ast

import numpy as np
from webob import Request
from webob.exc import HTTPException
from pkg_resources import iter_entry_points
from numpy.lib.arrayterator import Arrayterator

from pydap.responses.lib import load_responses
from pydap.responses.error import ErrorResponse
from pydap.parsers import parse_ce
from pydap.exceptions import ConstraintExpressionError, ExtensionNotSupportedError
from pydap.lib import walk, fix_shorthand, get_var, encode, combine_slices
from pydap.model import *


# buffer size in bytes, for streaming data
BUFFER_SIZE = 2**27


def load_handlers():
    return [ep.load() for ep in iter_entry_points("pydap.handler")]


def get_handler(filepath, handlers=None):
    # Check each handler to see which one handles this file.
    for handler in handlers or load_handlers():
        p = re.compile(handler.extensions)
        if p.match(filepath):
            return handler(filepath)

    raise ExtensionNotSupportedError(
            'No handler available for file {filepath}.'.format(filepath=filepath))


class BaseHandler(object):
    """
    Base class for Pydap handlers.

    Handlers are WSGI applications that parse the client request and build the
    corresponding dataset. The dataset is passed to proper Response (DDS, DAS,
    etc.)

    """

    # load all available responses
    responses = load_responses()

    def __init__(self, dataset=None):
        self.dataset = dataset
        self.additional_headers = []  #NYAN

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
            app.close = self.close

            # now build a Response and set additional headers
            res = req.get_response(app)
            for key, value in self.additional_headers:
                res.headers.add(key, value)

            return res(environ, start_response)
        except HTTPException, exc:
            # HTTP exceptions are used to redirect the user
            return exc(environ, start_response)
        except:
            # should the exception be catched?
            # http://wsgi.readthedocs.org/en/latest/specifications/throw_errors.html
            if environ.get('x-wsgiorg.throw_errors'):
                raise
            else:
                res = ErrorResponse(info=sys.exc_info())
                return res(environ, start_response)

    def parse(self, projection, selection, buffer_size=BUFFER_SIZE):
        """
        Parse the constraint expression.

        """
        if self.dataset is None:
            raise NotImplementedError(
                "Subclasses must define a dataset attribute pointing to a DatasetType.")

        # make a copy of the dataset, so we can filter sequences inplace
        dataset = self.dataset.clone()

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
        pass


def wrap_arrayterator(dataset, size):
    """
    Wrap `BaseType` objects in an Arrayterator.

    Since the buffer size of the Arrayterator is in elements, not bytes, we 
    convert according to the data item size.

    """
    for var in walk(dataset, BaseType):
        elements = size // var.data.dtype.itemsize
        var.data = Arrayterator(var.data, elements)

    return dataset


def apply_selection(selection, dataset):
    """
    Apply a given selection to a dataset, modifying it inplace.

    """
    for seq in walk(dataset, SequenceType):
        # apply only relevant selections
        conditions = [condition for condition in selection
                if re.match('%s\.[^\.]+(<=|<|>=|>|=|!=)' % re.escape(seq.id), condition)]
        for condition in conditions:
            id1, op, id2 = parse_selection(condition, dataset)
            seq.data = seq[ op(id1, id2) ].data
    return dataset


def apply_projection(projection, dataset):
    """
    Apply a given projection to a dataset.

    The function returns a new dataset object, after applying the projection to
    the original dataset.

    """
    out = DatasetType(name=dataset.name, attributes=dataset.attributes)

    for var in projection:
        target, template = out, dataset
        while var:
            name, slice_ = var.pop(0)
            candidate = template[name]
            
            # apply slice
            if slice_:
                if isinstance(candidate, BaseType):
                    candidate.data = candidate[slice_]
                elif isinstance(candidate, SequenceType):
                    candidate = candidate[slice_[0]]
                elif isinstance(candidate, GridType):
                    candidate = candidate[slice_]

            # handle structures
            if isinstance(candidate, StructureType):
                # add variable to target
                if name not in target.keys():
                    if var:
                        # if there are more children to add we need to clear the
                        # candidate so it has only explicitly added children; 
                        # also, Grids are degenerated into Structures
                        if isinstance(candidate, GridType):
                            candidate = StructureType(candidate.name, candidate.attributes)
                        candidate._keys = []
                    target[name] = candidate
                target, template = target[name], template[name]
            else:
                target[name] = candidate

    # fix sequence data, including only variables that are in the sequence
    for seq in walk(out, SequenceType):
        seq.data = get_var(dataset, seq.id)[tuple(seq.keys())].data

    return out


def parse_selection(expression, dataset):
    """
    Parse a selection expression into its elements.

    This function will parse a selection expression into three tokens: two
    variables or values and a comparison operator. Variables are returned as 
    Pydap objects from a given dataset, while values are parsed using
    `ast.literal_eval`.

    """
    id1, op, id2 = re.split('(<=|>=|!=|=~|>|<|=)', expression, 1)

    op = {
        '<=': operator.le,
        '>=': operator.ge,
        '!=': operator.ne,
        '=': operator.eq,
        '>': operator.gt, 
        '<': operator.lt,
    }[op]

    try:
        id1 = get_var(dataset, id1)
    except:
        id1 = ast.literal_eval(id1)

    try:
        id2 = get_var(dataset, id2)
    except:
        id2 = ast.literal_eval(id2)

    return id1, op, id2


class ConstraintExpression(object):
    """
    An object representing a selection on a constraint expression.
    
    These can be accumulated and evaluated only once.
    
    """
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)
        
    def __unicode__(self):
        return unicode(self.value)

    def __and__(self, other):
        """Join two CEs together."""
        return self.__class__(self.value + '&' + str(other))

    def __or__(self, other):
        raise ConstraintExpressionError('OR constraints not allowed in the Opendap specification.')


class IterData(object):
    """
    Class that emulates structured arrays from iterators.

    """
    
    shape = ()

    def __init__(self, id, vars, cols=None, selection=None, slice_=None):
        self.id = id
        self.vars = vars
        self.cols = vars if cols is None else cols
        self.selection = [] if selection is None else selection
        self.slice = (slice(None),) if slice_ is None else slice_

    @property
    def dtype(self):
        peek = iter(self).next()
        return np.array(peek).dtype

    def gen(self):
        """
        Iterator that yields data.

        """
        raise NotImplementedError(
            "Subclasses must define a gen() method.")

    def __iter__(self):
        stream = self.gen()

        cols = self.cols if isinstance(self.cols, tuple) else (self.cols,)
        indexes = [self.vars.index(col) for col in cols]

        # prepare data
        data = itertools.ifilter(len, stream)
        data = itertools.ifilter(build_filter(self.selection, self.vars), data)
        data = itertools.imap(lambda line: [line[i] for i in indexes], data)  
        data = itertools.islice(data, 
                self.slice[0].start, self.slice[0].stop, self.slice[0].step)

        # return data from a children BaseType, not a Sequence
        if not isinstance(self.cols, tuple):
            data = itertools.imap(operator.itemgetter(0), data)

        return data

    def __getitem__(self, key):                                                 
        out = self.clone()                                                      
                                                                                
        # return the data for a children                                        
        if isinstance(key, basestring):                                         
            out.id = '{id}.{child}'.format(id=self.id, child=key)               
            out.cols = key                                                      
                                                                                
        # return a new object with requested columns                            
        elif isinstance(key, list):                                             
            out.cols = tuple(key)                                               
                                                                                
        # return a copy with the added constraints                              
        elif isinstance(key, ConstraintExpression):                             
            out.selection.extend( str(key).split('&') )                         
                                                                                
        # slice data                                                            
        else:                                                                   
            if isinstance(key, int):                                            
                key = slice(key, key+1)                                         
            out.slice = combine_slices(self.slice, (key,))                      
                                                                                
        return out

    def clone(self):
        return self.__class__(self.id, self.vars[:], self.cols[:],
            self.selection[:], self.slice[:])

    def __eq__(self, other): return ConstraintExpression('%s=%s' % (self.id, encode(other)))
    def __ne__(self, other): return ConstraintExpression('%s!=%s' % (self.id, encode(other)))
    def __ge__(self, other): return ConstraintExpression('%s>=%s' % (self.id, encode(other)))
    def __le__(self, other): return ConstraintExpression('%s<=%s' % (self.id, encode(other)))
    def __gt__(self, other): return ConstraintExpression('%s>%s' % (self.id, encode(other)))
    def __lt__(self, other): return ConstraintExpression('%s<%s' % (self.id, encode(other)))


def build_filter(selection, cols):                                              
    filters = [bool]                                                          
                                                                                
    for expression in selection:                                                
        id1, op, id2 = re.split('(<=|>=|!=|=~|>|<|=)', expression, 1)           
                                                                                
        # a should be a variable in the children                                
        name1 = id1.split('.')[-1]                                              
        if name1 in cols:                                                       
            a = operator.itemgetter(cols.index(name1))                          
        else:                                                                   
            raise ConstraintExpressionError(                                    
                    'Invalid constraint expression: "{expression}" ("{id}" is not a valid variable)'.format(
                    expression=expression, id=id1))                             
                                                                                
        # b could be a variable or constant                                     
        name2 = id2.split('.')[-1]                                              
        if name2 in cols:                                                       
            b = operator.itemgetter(cols.index(name2))                          
        else:                                                                   
            b = lambda line, id2=id2: ast.literal_eval(id2)                     
                                                                                
        op = {                                                                  
                '<' : operator.lt,                                              
                '>' : operator.gt,                                              
                '!=': operator.ne,                                              
                '=' : operator.eq,                                              
                '>=': operator.ge,                                              
                '<=': operator.le,                                              
                '=~': lambda a, b: re.match(b, a),                              
        }[op]                                                                   
                                                                                
        filter_ = lambda line, op=op, a=a, b=b: op(a(line), b(line))            
        filters.append(filter_)                                                 
                                                                                
    return lambda line: reduce(lambda x, y: x and y, [f(line) for f in filters])


NYAN = [
    ('X-Nyan-00', ' [m+      o     +              o            '),
    ('X-Nyan-01', ' [m    +             o     +       +        '),
    ('X-Nyan-02', ' [mo          +                             '),
    ('X-Nyan-03', ' [m    o  +           +        +            '),
    ('X-Nyan-04', ' [m+        o     o       +        o        '),
    ('X-Nyan-05', ' [1;31m_-_-_-_-_-_-_-[m,------,      o    '),
    ('X-Nyan-06', ' [1;33m-_-_-_-_-_-_-_[m|   /\_/\          '),
    ('X-Nyan-07', ' [1;32m_-_-_-_-_-_-_[m~|__( ^ .^)  +     +'),
    ('X-Nyan-08', ' [1;34m-_-_-_-_-_-_-_[m""  ""             '),
    ('X-Nyan-09', ' [m+      o         o   +       o           '),
    ('X-Nyan-10', ' [m    +         +                          '),
    ('X-Nyan-11', ' [mo        o         o      o     +        '),
    ('X-Nyan-12', ' [m    o           +                        '),
    ('X-Nyan-13', ' [m+      +     o        o      +           '),
    ('X-Nyan-Credit', ' Chairman Jonty <jonty@nyan.cat.idea>'),
]
