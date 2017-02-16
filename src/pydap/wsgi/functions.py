"""Server-side functions for Pydap.

Pydap maps function calls in the request URL to functions defined through entry
points. For example, Pydap defines an entry point on the group "pydap.function"
with the name "density"; from ``setup.py``:

    [pydap.function]
    density = pydap.wsgi.functions.density

When a DAP client makes a request to the URL calling this function:

    ?cast.oxygen&density(cast.salt,cast.temp,cast.press)>1024

Pydap will call the ``density`` function passing the dataset itself as the
first argument, followed by the variables from the sequence "cast".

New functions can be defined in third-party modules. Simply create a package
and declare the entry point in its ``setup.py`` file. The server will
automatically discover the new functions from the system.

"""

from datetime import datetime, timedelta
import re

import numpy as np
import coards
import gsw

from pydap.model import SequenceType, GridType, BaseType
from pydap.lib import walk
from pydap.exceptions import ConstraintExpressionError, ServerError


def density(dataset, salinity, temperature, pressure):
    """Calculate in-situ density.

    This function calculated in-situ density from absolute salinity and
    conservative temperature, using the `gsw.rho` function. Returns a new
    sequence with the data.

    """
    # find sequence
    for sequence in walk(dataset, SequenceType):
        break
    else:
        raise ConstraintExpressionError(
            'Function "bounds" should be used on a Sequence.')

    selection = sequence[salinity.name, temperature.name, pressure.name]
    rows = [tuple(row) for row in selection]
    data = np.rec.fromrecords(
        rows, names=['salinity', 'temperature', 'pressure'])
    rho = gsw.rho(data['salinity'], data['temperature'], data['pressure'])

    out = SequenceType("result")
    out['rho'] = BaseType("rho", units="kg/m**3")
    out.data = np.rec.fromrecords(rho.reshape(-1, 1), names=['rho'])
    return out


density.__version__ = "0.1"


def bounds(dataset, xmin, xmax, ymin, ymax, zmin, zmax, tmin, tmax):
    r"""Bound a sequence in space and time.

    This function is used by GrADS to access Sequences, eg:

        http://server.example.com/dataset.dods?sequence& \
                bounds(0,360,-90,90,500,500,00Z01JAN1970,00Z01JAN1970)

    We assume the dataset has only a single Sequence, which will be returned
    modified in place.

    """
    # find sequence
    for sequence in walk(dataset, SequenceType):
        break  # get first sequence
    else:
        raise ConstraintExpressionError(
            'Function "bounds" should be used on a Sequence.')

    for child in sequence.children():
        if child.attributes.get('axis', '').lower() == 'x':
            if xmin == xmax:
                sequence.data = sequence[child == xmin].data
            else:
                sequence.data = sequence[
                    (child >= xmin) & (child <= xmax)].data
        elif child.attributes.get('axis', '').lower() == 'y':
            if ymin == ymax:
                sequence.data = sequence[child == ymin].data
            else:
                sequence.data = sequence[
                    (child >= ymin) & (child <= ymax)].data
        elif child.attributes.get('axis', '').lower() == 'z':
            if zmin == zmax:
                sequence.data = sequence[child == zmin].data
            else:
                sequence.data = sequence[
                    (child >= zmin) & (child <= zmax)].data
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
                sequence.data = sequence[
                    (child >= tmin) & (child < tmax)].data
            else:
                tmin = coards.format(start, units)
                tmax = coards.format(end, units)
                sequence.data = sequence[
                    (child >= tmin) & (child <= tmax)].data

    return sequence


bounds.__version__ = "1.0"


def parse_step(step):
    """Parse a GrADS time step returning a timedelta."""
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
    raise ServerError('Unknown units: "%s".' % units)


def mean(dataset, var, axis=0):
    """Calculate the mean of an array along a given axis.

    The input variable should be either a ``GridType`` or ``BaseType``. The
    function will return an object of the same type with the mean applied.

    """
    if not isinstance(var, (GridType, BaseType)):
        raise ConstraintExpressionError(
            'Function "mean" should be used on an array or grid.')

    axis = int(axis)
    dims = tuple(dim for i, dim in enumerate(var.dimensions) if i != axis)

    # process basetype
    if isinstance(var, BaseType):
        return BaseType(
            name=var.name, data=np.mean(var.data[:], axis=axis),
            dimensions=dims, attributes=var.attributes)

    # process grid
    out = GridType(name=var.name, attributes=var.attributes)
    out[var.array.name] = BaseType(
        name=var.array.name, data=np.mean(var.array.data[:], axis=axis),
        dimensions=dims, attributes=var.array.attributes)
    for dim in dims:
        out[dim] = BaseType(
            name=dim, data=var[dim].data[:], dimensions=(dim,),
            attributes=var[dim].attributes)
    return out


mean.__version__ = "1.0"
