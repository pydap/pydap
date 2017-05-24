"""Pydap handler for NetCDF3/4 files."""

import os
import re
import time
from stat import ST_MTIME
from email.utils import formatdate
import numpy as np

from pkg_resources import get_distribution

from pydap.model import DatasetType, GridType, BaseType
from pydap.handlers.lib import BaseHandler
from pydap.exceptions import OpenFileError

from collections import OrderedDict

# Check for netCDF4 presence:
try:
    from netCDF4 import Dataset as netcdf_file

    def attrs(var):
        return dict((k, getattr(var, k)) for k in var.ncattrs())
except ImportError:
    from scipy.io.netcdf import netcdf_file

    def attrs(var):
        return var._attributes


class NetCDFHandler(BaseHandler):

    """A simple handler for NetCDF files.
    Here's a standard dataset for testing sequential data:
    """

    __version__ = get_distribution("pydap").version
    extensions = re.compile(r"^.*\.(nc|cdf)$", re.IGNORECASE)

    def __init__(self, filepath):
        BaseHandler.__init__(self)

        self.filepath = filepath
        try:
            with netcdf_file(self.filepath, 'r') as source:
                self.additional_headers.append(('Last-modified',
                                               (formatdate(
                                                time.mktime(
                                                    time.localtime(
                                                        os.stat(filepath)
                                                        [ST_MTIME])
                                                        )))))

                # shortcuts
                vars = source.variables
                dims = source.dimensions

                # build dataset
                name = os.path.split(filepath)[1]
                self.dataset = DatasetType(name,
                                           attributes=dict(
                                                      NC_GLOBAL=attrs(source)))
                for dim in dims:
                    if dims[dim] is None:
                        self.dataset.attributes['DODS_EXTRA'] = {
                            'Unlimited_Dimension': dim,
                        }
                        break

                # add grids
                grids = [var for var in vars if var not in dims]
                for grid in grids:
                    self.dataset[grid] = GridType(grid, attrs(vars[grid]))
                    # add array
                    self.dataset[grid][grid] = BaseType(grid,
                                                        LazyVariable(
                                                            source,
                                                            grid,
                                                            grid,
                                                            self.filepath),
                                                        vars[grid].dimensions,
                                                        attrs(vars[grid]))
                    # add maps
                    for dim in vars[grid].dimensions:
                        self.dataset[grid][dim] = BaseType(dim, vars[dim][:],
                                                           None,
                                                           attrs(vars[dim]))

                # add dims
                for dim in dims:
                    self.dataset[dim] = BaseType(dim, vars[dim][:], None,
                                                 attrs(vars[dim]))
        except Exception as exc:
            raise
            message = 'Unable to open file %s: %s' % (filepath, exc)
            raise OpenFileError(message)


class LazyVariable:
    def __init__(self, source, name, path, filepath):
        self.filepath = filepath
        self.path = path
        var = source[self.path]
        self.dimensions = var._getdims()
        self.dtype = np.dtype(var.dtype)
        self.datatype = var.dtype
        self.ndim = len(var.dimensions)
        self._shape = var.shape
        self._reshape = var.shape
        self.scale = True
        self.name = name
        self.size = np.prod(self.shape)
        self._attributes = dict((attr, var.getncattr(attr))
                                for attr in var.ncattrs())
        return

    def chunking(self):
        return 'contiguous'

    def filters(self):
        return None

    def get_var_chunk_cache(self):
        raise NotImplementedError('get_var_chunk_cache is not implemented')
        return

    def ncattrs(self):
        return self._attributes

    def getncattr(self, attr):
        return self._attributes[attr]

    def __getattr__(self, name):
        # from netcdf4-python
        # if name in _private_atts, it is stored at the python
        # level and not in the netCDF file.
        if name.startswith('__') and name.endswith('__'):
            # if __dict__ requested, return a dict with netCDF attributes.
            if name == '__dict__':
                names = self.ncattrs()
                values = []
                for name in names:
                    values.append(self._attributes[name])
                return OrderedDict(zip(names, values))
            else:
                raise AttributeError
        else:
            return self.getncattr(name)

    def getValue(self):
        return self[...]

    def __array__(self):
        return self[...]

    def __getitem__(self, key):
        with netcdf_file(self.filepath, 'r') as source:
            return (np.asarray(source[self.path][key])
                    .astype(self.dtype).reshape(self._reshape))

    def reshape(self, *args):
        if len(args) > 1:
            self._reshape = args
        else:
            self._reshape = args
        return self

    @property
    def shape(self):
        return self._shape

    def __len__(self):
        if not self.shape:
            raise TypeError('len() of unsized object')
        else:
            return self.shape[0]

    def _getdims(self):
        return self.dimensions


if __name__ == "__main__":
    import sys
    from werkzeug.serving import run_simple

    application = NetCDFHandler(sys.argv[1])
    run_simple('localhost', 8001, application, use_reloader=True)
