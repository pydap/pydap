import copy
import re
import operator

from pydap.model import *
from pydap.lib import walk, parse_qs, fix_shn
from pydap.util.safeeval import expr_eval


def constrain(dataset, ce):
    """
    A constraint expression applier.

        >>> dataset = DatasetType(name='test')
        >>> dataset['seq'] = SequenceType(name='seq')
        >>> dataset['seq']['index'] = BaseType(name='index', type=Int32)
        >>> dataset['seq']['temperature'] = BaseType(name='temperature', type=Float32)
        >>> dataset['seq']['site'] = BaseType(name='site', type=String)

        >>> dataset['seq'].data = [
        ...         (10, 17.2, 'Diamont_St'),
        ...         (11, 15.1, 'Blacktail_Loop'),
        ...         (12, 15.3, 'Platinum_St'),
        ...         (13, 15.1, 'Kodiak_Trail')]
        >>> for struct_ in dataset.seq:
        ...     print struct_.data
        (10, 17.2, 'Diamont_St')
        (11, 15.1, 'Blacktail_Loop')
        (12, 15.3, 'Platinum_St')
        (13, 15.1, 'Kodiak_Trail')

        >>> dataset2 = constrain(dataset, 'seq.index>11')
        >>> for struct_ in dataset2.seq:
        ...     print struct_.data
        (12, 15.3, 'Platinum_St')
        (13, 15.1, 'Kodiak_Trail')
        >>> dataset2 = constrain(dataset, 'seq.index>11&seq.temperature<15.2')
        >>> for struct_ in dataset2.seq:
        ...     print struct_.data
        (13, 15.1, 'Kodiak_Trail')

        >>> dataset.clear()
        >>> dataset['casts'] = SequenceType(name='casts')
        >>> dataset['casts']['lat'] = BaseType(name='lat', type=Float32)
        >>> dataset['casts']['lon'] = BaseType(name='lon', type=Float32)
        >>> dataset['casts']['time'] = BaseType(name='time', type=Float64)
        >>> dataset['casts']['profile'] = SequenceType(name='profile')
        >>> dataset['casts']['profile']['t'] = BaseType(name='t', type=Float32)
        >>> dataset['casts']['profile']['s'] = BaseType(name='s', type=Float32)
        >>> dataset['casts']['profile']['p'] = BaseType(name='p', type=Float32)
        >>> dataset['casts'].data = [
        ...         (-10.0, 290.0, 1.0, [(21.0, 35.0, 100.0), (20.5, 34.9, 200.0), (19.0, 33.0, 300.0)]),
        ...         (-11.0, 295.0, 2.0, [(22.0, 35.5, 100.0), (21.0, 35.4, 200.0), (20.0, 33.5, 300.0), (19.0, 33.0, 500.0)])]
        >>> dataset2 = constrain(dataset, 'casts.lat>-11')
        >>> for struct_ in dataset2.casts:
        ...     print struct_.data
        (-10.0, 290.0, 1.0, array([[21.0, 35.0, 100.0],
               [20.5, 34.9, 200.0],
               [19.0, 33.0, 300.0]], dtype=object))

    Filtering is guaranteed to work only in outer sequences, but not in inner
    sequences like this::

        >>> dataset2 = constrain(dataset, 'casts.profile.p>100')
        >>> for struct_ in dataset2.casts:
        ...     print struct_.data
        (-10.0, 290.0, 1.0, array([[21.0, 35.0, 100.0],
               [20.5, 34.9, 200.0],
               [19.0, 33.0, 300.0]], dtype=object))
        (-11.0, 295.0, 2.0, array([[22.0, 35.5, 100.0],
               [21.0, 35.4, 200.0],
               [20.0, 33.5, 300.0],
               [19.0, 33.0, 500.0]], dtype=object))
        
    Instead, inner sequences have to be filtered inside a loop::

        >>> for struct_ in dataset.casts:
        ...     for profile in struct_.profile[ struct_.profile.p > 100 ]:
        ...         print profile.data
        (20.5, 34.9, 200.0)
        (19.0, 33.0, 300.0)
        (21.0, 35.4, 200.0)
        (20.0, 33.5, 300.0)
        (19.0, 33.0, 500.0)

    """
    projection, selection = parse_qs(ce)
    projection = projection or [[(key, ())]
            for key in dataset.keys()]
    projection = fix_shn(projection, dataset)

    # Make a copy of the dataset.
    filtered = copy.deepcopy(dataset)

    # Filter sequences.
    for seq in walk(filtered, SequenceType):
        if seq._nesting_level == 1:
            filter_ = []
            # Check only selections that apply to the direct children of this sequence
            # (ie, skip children from nested sequences).
            for cond in [cond for cond in selection
                    if re.match('%s\.[^\.]+(<=|<|>=|>|=|!=)' % re.escape(seq.id), cond)]:
                id_, op, other = parse_selection(cond, dataset)
                filter_.append(op(id_, other))
            if filter_:
                seq.data = seq[ reduce(lambda c1, c2: c1 & c2, filter_) ].data

    # Create a new empty dataset to build it up.
    new_ = DatasetType(name=filtered.name,
            attributes=filtered.attributes.copy())

    for var in projection:
        target, template = new_, filtered
        while var:
            name, slice_ = var.pop(0)
            candidate = copy.deepcopy(template[name])
            if slice_:
                if isinstance(candidate, SequenceType):
                    candidate = candidate[slice_[0]]
                elif isinstance(candidate, BaseType):
                    candidate.data = candidate[slice_]
                    candidate.shape = candidate.data.shape
                else:
                    candidate = candidate[slice_] 

            if isinstance(candidate, StructureType):
                if var:
                    # Convert degenerate grids into structures.
                    if isinstance(candidate, GridType):
                        candidate.__class__ = StructureType
                    candidate.clear()
                if name not in target or not var:
                    target[name] = candidate
                target, template = target[name], template[name]
            else:
                target[name] = candidate

    return new_


def parse_selection(cond, dataset):
    """
    Convert a URL selection to 3 tokens.

    """
    id_, op, other = re.split('(<=|>=|!=|=~|>|<|=)', cond)

    op = { '<=': operator.le, '>=': operator.ge,
            '!=': operator.ne, '=': operator.eq,
            '>': operator.gt, '<': operator.lt }[op]
    try:
        names = [dataset] + id_.split('.')
        id_ = reduce(operator.getitem, names)
    except:
        id_ = expr_eval(id_)
    try:
        names = [dataset] + other.split('.')
        other = reduce(operator.getitem, names)
    except:
        other = expr_eval(other)

    return id_, op, other


def _test():
    import doctest
    doctest.testmod()


if __name__ == "__main__":
    _test()

