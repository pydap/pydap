from datetime import datetime, timedelta
import re

import numpy as np
import coards

from pydap.model import *
from pydap.lib import walk
from pydap.exceptions import ConstraintExpressionError


def bounds(dataset, xmin, xmax, ymin, ymax, zmin, zmax, tmin, tmax):
    """
    Version 1.0

    This function is used by GrADS to access Sequences, eg:

        http://server.example.com/dataset.dods?sequence&bounds(0,360,-90,90,500,500,00Z01JAN1970,00Z01JAN1970)

    We assume the dataset has only a single Sequence, which is modified inplace.

    """
    # find sequence
    for sequence in walk(dataset, SequenceType):
        break  # get first sequence
    else:
        raise ConstraintExpressionError('Function "bounds" should be used on a Sequence.')

    for child in sequence.children():
        if child.attributes.get('axis', '').lower() == 'x':
            if xmin == xmax:
                sequence.data = sequence[ child == xmin ].data
            else:
                sequence.data = sequence[ (child >= xmin) & (child <= xmax) ].data
        elif child.attributes.get('axis', '').lower() == 'y':
            if ymin == ymax:
                sequence.data = sequence[ child == ymin ].data
            else:
                sequence.data = sequence[ (child >= ymin) & (child <= ymax) ].data
        elif child.attributes.get('axis', '').lower() == 'z':
            if zmin == zmax:
                sequence.data = sequence[ child == zmin ].data
            else:
                sequence.data = sequence[ (child >= zmin) & (child <= zmax) ].data
        elif child.attributes.get('axis', '').lower() == 't':
            start = datetime.strptime(tmin, '%HZ%d%b%Y')
            end = datetime.strptime(tmax, '%HZ%d%b%Y')
            units = child.attributes.get('units', 'seconds since 1970-01-01')

            # if start and end are equal, add the step
            if start == end and 'grads_step' in child.attributes:
                dt = parse_step(child.attributes['grads_step'])
                end = start + dt 
                tmin = coards.format(start, units)
                tmax = coards.format(end, units)
                sequence.data = sequence[ (child >= tmin) & (child < tmax) ].data
            else:
                tmin = coards.format(start, units)
                tmax = coards.format(end, units)
                sequence.data = sequence[ (child >= tmin) & (child <= tmax) ].data

    return sequence


def parse_step(step):
    """
    Parse a GrADS time step into a timedelta.

    """
    value, units = re.search('(\d+)(.*)', step).groups()
    value = int(value)
    if units.lower() == 'mn':
        return timedelta(minutes=value)
    if units.lower() == 'hr':
        return timedelta(hours=value)
    if units.lower() == 'dy':
        return timedelta(days=value)
    if units.lower() == 'mo':
        raise NotImplementedError('Need to implement month time step')
    if units.lower() == 'yr':
        raise NotImplementedError('Need to implement year time step')


def mean(dataset, var, axis=0):
    """
    Version 1.0

    Calculates the mean of an array along a given axis.

    """
    axis = int(axis)
    dims = tuple(dim for i, dim in enumerate(var.dimensions) if i != axis)

    if isinstance(var, BaseType):
        return BaseType(name=var.name, data=np.mean(var.data[:], axis=axis),
                dimensions=dims, attributes=var.attributes)

    elif isinstance(var, GridType):
        out = GridType(name=var.name, attributes=var.attributes)
        out[var.array.name] = BaseType(name=var.array.name, 
                data=np.mean(var.array.data[:], axis=axis), 
                dimensions=dims, attributes=var.array.attributes)
        for dim in dims:
            out[dim] = BaseType(name=dim, data=var[dim].data[:],
                    dimensions=(dim,), attributes=var[dim].attributes)
        return out
    else:
        raise ConstraintExpressionError('Function "mean" should be used on an array or grid.')
