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
from pydap.model import BaseType, DatasetType
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

                # Add dimensions when creating the DatasetType
                Dims = {}
                fqn_dims = OrderedDict()  # keep track of fully qualifying names of dims
                for dim in dims:
                    fqn_dims.update({"/" + dim: dim})
                    if dims[dim] is None:
                        self.dataset.attributes["DODS_EXTRA"] = {
                            "Unlimited_Dimension": dim,
                        }
                    else:
                        Dims.update({dims[dim].name: dims[dim].size})
                # build dataset

                name = os.path.split(filepath)[1]
                self.dataset = DatasetType(
                    name, dimensions=Dims, attributes=dict(attrs(source))
                )

                # add grids
                grids = [var for var in vars if var not in dims]
                for grid in grids:
                    # make dimension a fully qualifying name
                    dimensions = ["/" + dim for dim in vars[grid].dimensions]
                    self.dataset[grid] = BaseType(
                        grid,
                        LazyVariable(source[grid], grid, grid, self.filepath),
                        dims=dimensions,
                        **attrs(vars[grid]),
                    )

                if len(source.groups) > 0:
                    # start at root level
                    path = source.path
                    for vdim in source.dimensions:
                        fqn_dims.update({path + vdim: vdim})  # fqn is unique
                    fqn_dims = group_fqn(self.dataset, source, self.filepath, fqn_dims)

                vdims = [dim for dim in dims if dim in vars]
                for dim in vdims:
                    data = vars[dim][:]
                    attributes = attrs(vars[dim])
                    self.dataset[dim] = BaseType(dim, data, None, attributes)
                    self.dataset[dim].dims = ["/" + dim]
        except Exception as exc:
            raise
            message = "Unable to open file %s: %s" % (filepath, exc)
            raise OpenFileError(message)


def group_fqn(_dataset, _source, _filepath, _fqn_dims=OrderedDict()):
    """Function to create nested DAP objects with fully-qualified-names
    within a hierarchy. Returns a dictionary with mapping between dimension
    names used at the group/array level and their fully qualifying names.

    Parameters:
    ----------
        dataset: <pydap DatasetType>
            dataset to `write` object to.
        _source: <class netCDF4 >
            root, group, subgroup.
        _fqn_dims: dict,
            dict to create mapping between dimension names
            and their full-qualyfing names.

    Returns:
        _fqn_dims: dict
            Updated dict with mapping `dim_name` <--> fqn
    """
    for group in _source.groups:
        _path = _source[group].path
        if _path[-1] != "/":
            _path = _path + "/"
        # create group and attrs + dims (non-fqn)
        dims = _source[group].dimensions
        Dims = {}
        for dim in dims:
            if dim not in _fqn_dims.items():
                _fqn_dims.update({_path + dim: dim})
            Dims.update(
                {
                    _source[group]
                    .dimensions[dim]
                    .name: _source[group]
                    .dimensions[dim]
                    .size
                }
            )
        _attrs = dict(
            (attr, _source[group].getncattr(attr)) for attr in _source[group].ncattrs()
        )
        if "path" in _attrs:
            del _attrs["path"]
        _dataset.createGroup(_source[group].path, dimensions=Dims, **_attrs)
        # now vars
        Vars = _source[group].variables
        for var in Vars:
            data = _source[group][var]
            dims = list(_source[group][var].dimensions)  # these must have fqn
            vdims = []  # create mapping for fqn
            for dim in dims:
                for key, value in _fqn_dims.items():
                    if dim == value:
                        match_dim = key  # overwrites until the last one (most recent)
                vdims.append(match_dim)
            vattrs = dict(
                (attr, _source[group][var].getncattr(attr))
                for attr in _source[group][var].ncattrs()
            )
            if "path" in vattrs:
                del vattrs["path"]
            _dataset.createVariable(
                _path + var,
                data=LazyVariable(data, var, _path + var, _filepath),
                dims=vdims,
                path=("/").join(_path.split("/")[:-1]),
                **vattrs,
            )
        # check if there are nested group
        if len(_source[group].groups) > 0:
            _fqn_dims = group_fqn(_dataset, _source[group], _filepath, _fqn_dims)
    return _fqn_dims


class LazyVariable:
    def __init__(self, var, name, path, filepath):
        self.filepath = filepath
        self.path = path
        # var = source[self.path]
        # self.dimensions = fqn_dims
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
