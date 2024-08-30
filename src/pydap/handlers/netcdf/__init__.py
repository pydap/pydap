"""pydap handler for NetCDF3/4 files."""

import os
import re
import time
from collections import OrderedDict
from email.utils import formatdate
from stat import ST_MTIME

import numpy as np

from pydap.exceptions import OpenFileError
from pydap.handlers.lib import BaseHandler
from pydap.model import BaseType, DatasetType, GridType
from pydap.pycompat import suppress

# Check for netCDF4 presence:
with suppress(ImportError):
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

    extensions = re.compile(r"^.*\.(nc4|nc|cdf)$", re.IGNORECASE)

    def __init__(self, filepath):
        BaseHandler.__init__(self)

        self.filepath = filepath
        try:
            with netcdf_file(self.filepath, "r") as source:
                self.additional_headers.append(
                    (
                        "Last-modified",
                        (
                            formatdate(
                                time.mktime(time.localtime(os.stat(filepath)[ST_MTIME]))
                            )
                        ),
                    )
                )

                # shortcuts
                vars = source.variables
                dims = source.dimensions
                groups = source.groups

                # build dataset
                name = os.path.split(filepath)[1]
                self.dataset = DatasetType(
                    name, attributes=dict(NC_GLOBAL=attrs(source))
                )
                for dim in dims:
                    if dims[dim] is None:
                        self.dataset.attributes["DODS_EXTRA"] = {
                            "Unlimited_Dimension": dim,
                        }
                        break

                # add grids
                grids = [var for var in vars if var not in dims]
                for grid in grids:
                    self.dataset[grid] = GridType(grid, attrs(vars[grid]))
                    # add array
                    self.dataset[grid][grid] = BaseType(
                        grid,
                        LazyVariable(source, grid, grid, self.filepath),
                        vars[grid].dimensions,
                        attrs(vars[grid]),
                    )
                    # add maps
                    for dim in vars[grid].dimensions:
                        try:
                            data = vars[dim][:]
                            attributes = attrs(vars[dim])
                        except KeyError:
                            data = np.arange(dims[dim].size, dtype="i")
                            attributes = None
                        self.dataset[grid][dim] = BaseType(dim, data, None, attributes)

                fqn_dims = {}  # keep track of fully qualifying names of dims
                # start at root level
                path = source.path
                for vdim in source.dimensions:
                    fqn_dims.update({vdim: path + vdim})

                for group in groups:
                    path = source[group].path
                    if path[-1] != "/":
                        path = path + "/"
                    # create group and attrs + dims (non-fqn)
                    dims = source[group].dimensions
                    Dims = {}
                    for dim in dims:
                        if dim not in fqn_dims.keys():
                            fqn_dims.update({dim: path + dim})
                        Dims.update({source[group][dim].name: source[group][dim].size})
                    _attrs = dict(
                        (attr, source[group].getncattr(attr))
                        for attr in source[group].ncattrs()
                    )
                    self.dataset.createGroup(
                        source.name + group, dimensions=Dims, **_attrs
                    )
                    # now vars
                    Vars = source[group].variables
                    for var in Vars:
                        data = source[group][var][:].data  # extract data from file
                        dims = list(
                            source[group][var].dimensions
                        )  # these must have fqn
                        vdims = []  # create mapping for fqn
                        for dim in dims:
                            vdims.append(fqn_dims[dim])
                        print(vdims)
                        vattrs = dict(
                            (attr, source[group][var].getncattr(attr))
                            for attr in source[group][var].ncattrs()
                        )
                        self.dataset.createVariable(
                            path + var, data=data, dims=tuple(vdims), **vattrs
                        )

                # create basetype for dimensions that are also variables
                # this allows for `named dimension` like `nv`.
                vdims = [dim for dim in dims if dim in vars]
                for dim in vdims:
                    data = vars[dim][:]
                    attributes = attrs(vars[dim])
                    self.dataset[dim] = BaseType(dim, data, None, attributes)
        except Exception as exc:
            raise
            message = "Unable to open file %s: %s" % (filepath, exc)
            raise OpenFileError(message)


def group_fqn(_source, path=""):
    """function to help fully-qualified-names of DAP objects within a hierarchy.

    Parameters:
    ----------
        _source: <class netCDF4 >
            root, group, subgroup
        _path: str, parent name.
            default is root `/`

    Returns:

    Example

        Group_name = path + _source.name
        ds.createGroup(path+'SubGroup2',
                        dimensions={"X": 2, "Y": 2}, **atrs)

        ds.createVariable()
    """
    pass


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
        self._attributes = dict((attr, var.getncattr(attr)) for attr in var.ncattrs())
        return

    def chunking(self):
        return "contiguous"

    def filters(self):
        return None

    def get_var_chunk_cache(self):
        raise NotImplementedError("get_var_chunk_cache is not implemented")
        return

    def ncattrs(self):
        return self._attributes

    def getncattr(self, attr):
        return self._attributes[attr]

    def __getattr__(self, name):
        # from netcdf4-python
        # if name in _private_atts, it is stored at the python
        # level and not in the netCDF file.
        if name.startswith("__") and name.endswith("__"):
            # if __dict__ requested, return a dict with netCDF attributes.
            if name == "__dict__":
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
        with netcdf_file(self.filepath, "r") as source:
            # Avoid applying scale_factor, see
            # https://github.com/pydap/pydap/issues/190
            source.set_auto_scale(False)
            return (
                np.asarray(source[self.path][key])
                .astype(self.dtype)
                .reshape(self._reshape)
            )

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
            raise TypeError("len() of unsized object")
        else:
            return self.shape[0]

    def _getdims(self):
        return self.dimensions


if __name__ == "__main__":
    import sys

    from werkzeug.serving import run_simple

    application = NetCDFHandler(sys.argv[1])
    run_simple("localhost", 8001, application, use_reloader=True)
