"""
Based on netcdf4-python

This code aims to provide:

A (partial) compatibility layer with netcdf4-python.
In order to do so code was directly
borrowed from netcdf4-python package.

This should be considered beta at the current stage.

Frederic Laliberte, 2016

with special thanks to
Jeff Whitaker and co-contributors (netcdf4-python)
"""

import requests
import six

import numpy as np

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from ..exceptions import ServerError
from ..client import open_url
from ..lib import DEFAULT_TIMEOUT

default_encoding = 'utf-8'


class Dataset:
    def __init__(self, url, timeout=DEFAULT_TIMEOUT,
                 session=None, application=None,
                 output_grid=False):
        self._url = url
        # Provided for compatibility:
        self.data_model = 'pyDAP'
        self.file_format = self.data_model
        self.disk_format = 'DAP2'
        self._isopen = 1
        self.path = '/'
        self.parent = None
        self.keepweakref = False

        self._pydap_dataset = open_url(url, session=session,
                                       timeout=timeout,
                                       application=application,
                                       output_grid=output_grid)

        self.dimensions = self._get_dims(self._pydap_dataset)
        self.variables = self._get_vars(self._pydap_dataset)

        self.groups = OrderedDict()
        return

    def __enter__(self):
        return self

    def __exit__(self, atype, value, traceback):
        self.close()
        return

    def __getitem__(self, elem):
        # There are no groups. Simple mapping to variable:
        if elem in self.variables.keys():
            return self.variables[elem]
        else:
            raise IndexError('%s not found in %s' % (elem, self.path))

    def filepath(self):
        return self._url

    def __repr__(self):
        if six.PY3:
            return self.__unicode__()
        else:
            return six.text_type(self).encode(default_encoding)

    def __unicode__(self):
        # taken directly from netcdf4-python netCDF4.pyx
        ncdump = ['%r\n' % type(self)]
        dimnames = tuple([_tostr(dimname)+'(%s)' %
                          len(self.dimensions[dimname])
                          for dimname in self.dimensions.keys()])
        varnames = tuple([_tostr(self.variables[varname].dtype) +
                          ' \033[4m' + _tostr(varname) + '\033[0m' +
                          (((_tostr(self.variables[varname].dimensions)
                             .replace("u'", ""))
                            .replace("'", ""))
                          .replace(", ", ","))
                          .replace(",)", ")")
                          for varname in self.variables.keys()])
        grpnames = tuple([_tostr(grpname)
                          for grpname in self.groups.keys()])
        if self.path == '/':
            ncdump.append('root group (%s data model, file format %s):\n' %
                          (self.data_model, self.disk_format))
        else:
            ncdump.append('group %s:\n' % self.path)
        attrs = ['    %s: %s\n' % (name, self.getncattr(name)) for name in
                 self.ncattrs()]
        ncdump = ncdump + attrs
        ncdump.append('    dimensions(sizes): %s\n' % ', '.join(dimnames))
        ncdump.append('    variables(dimensions): %s\n' % ', '.join(varnames))
        ncdump.append('    groups: %s\n' % ', '.join(grpnames))
        return ''.join(ncdump)

    def close(self):
        self._isopen = 0
        return

    def isopen(self):
        return bool(self._isopen)

    def ncattrs(self):
        try:
            return self._pydap_dataset.attributes['NC_GLOBAL'].keys()
        except KeyError:
            return []

    def getncattr(self, attr):
        return self._pydap_dataset.attributes['NC_GLOBAL'][attr]

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
                    values.append(self
                                  ._pydap_dataset
                                  .attributes['NC_GLOBAL'][name])
                return OrderedDict(zip(names, values))
            else:
                raise AttributeError
        else:
            return self.getncattr(name)

    def set_auto_maskandscale(self, flag):
        raise NotImplementedError('set_auto_maskandscale is not '
                                  'implemented for pydap')
        return

    def set_auto_mask(self, flag):
        raise NotImplementedError('set_auto_mask is not implemented for pydap')
        return

    def set_auto_scale(self, flag):
        raise NotImplementedError('set_auto_scale is not implemented '
                                  'for pydap')
        return

    def get_variables_by_attributes(self, **kwargs):
        # From netcdf4-python
        vs = []

        has_value_flag = False
        for vname in self.variables:
            var = self.variables[vname]
            for k, v in kwargs.items():
                if callable(v):
                    has_value_flag = v(getattr(var, k, None))
                    if has_value_flag is False:
                        break
                # Must use getncattr
                elif hasattr(var, k) and var.getncattr(k) == v:
                    has_value_flag = True
                else:
                    has_value_flag = False
                    break
            if has_value_flag is True:
                vs.append(self.variables[vname])
        return vs

    def _get_dims(self, dataset):
        if ('DODS_EXTRA' in dataset.attributes.keys() and
           'Unlimited_Dimension' in dataset.attributes['DODS_EXTRA']):
            unlimited_dims = [dataset
                              .attributes['DODS_EXTRA']
                              ['Unlimited_Dimension']]
        else:
            unlimited_dims = []
        var_list = dataset.keys()
        var_id = np.argmax([len(dataset[varname].dimensions)
                            for varname in var_list])
        base_dimensions_list = dataset[var_list[var_id]].dimensions
        base_dimensions_lengths = dataset[var_list[var_id]].array.shape

        for varname in var_list:
            if not (set(base_dimensions_list)
                    .issuperset(dataset[varname].dimensions)):
                for dim_id, dim in enumerate(dataset[varname].dimensions):
                    if dim not in base_dimensions_list:
                        base_dimensions_list += (dim,)
                        base_dimensions_lengths += (dataset[varname]
                                                    .shape[dim_id],)
        dimensions_dict = OrderedDict()
        for dim, dim_length in zip(base_dimensions_list,
                                   base_dimensions_lengths):
            dimensions_dict[dim] = Dimension(dataset, dim,
                                             size=dim_length,
                                             isunlimited=(dim
                                                          in unlimited_dims))
        return dimensions_dict

    def _get_vars(self, dataset):
        return dict([(var, Variable(dataset[var], var, self))
                     for var in dataset.keys()])


class Variable:
    def __init__(self, var, name, grp):
        self._grp = grp
        self._var = var
        self.dimensions = self._getdims()

        self.datatype = self.dtype
        self.ndim = len(self.dimensions)
        self.scale = True
        self.name = name
        self.size = np.prod(self.shape)
        return

    @property
    def shape(self):
        return self._get_array_att('shape')

    @property
    def dtype(self):
        if self._get_array_att('dtype').char == 'S':
            if ('DODS' in self.ncattrs() and
                'dimName' in self.getncattr('DODS') and
               self.getncattr('DODS')['dimName'] in self.getncattr('DODS')):
                return np.dtype('S' +
                                str(self.getncattr('DODS')
                                    [self.getncattr('DODS')['dimName']]))
            else:
                # Default to length 100 strings:
                return np.dtype('S100')
        else:
            return np.dtype(self._get_array_att('dtype'))

    def chunking(self):
        return 'contiguous'

    def filters(self):
        return None

    def get_var_chunk_cache(self):
        raise NotImplementedError('get_var_chunk_cache is not implemented')
        return

    def ncattrs(self):
        return self._var.attributes.keys()

    def getncattr(self, attr):
        return self._var.attributes[attr]

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
                    values.append(self._var.attributes[name])
                return OrderedDict(zip(names, values))
            else:
                raise AttributeError
        else:
            return self.getncattr(name)

    def getValue(self):
        return self._var[...]

    def group(self):
        return self._grp

    def __array__(self):
        return self[...]

    def __repr__(self):
        if six.PY3:
            return self.__unicode__()
        else:
            return six.text_type(self).encode(default_encoding)

    def __getitem__(self, getitem_tuple):
        try:
            return self._var.array.__getitem__(getitem_tuple)
        except (AttributeError, ServerError,
                requests.exceptions.HTTPError):
            if (isinstance(getitem_tuple, slice) and
               getitem_tuple == _PhonyVariable()[:]):
                # A single dimension ellipsis was requested.
                # Use netCDF4 convention:
                return self[...]
            else:
                return self._var.__getitem__(getitem_tuple)

    def __len__(self):
        if not self.shape:
            raise TypeError('len() of unsized object')
        else:
            return self.shape[0]

    def set_auto_maskandscale(self, maskandscale):
        raise NotImplementedError('set_auto_maskandscale is '
                                  'not implemented for pydap')

    def set_auto_scale(self, scale):
        raise NotImplementedError('set_auto_scale is not implemented '
                                  'for pydap')

    def set_auto_mask(self, mask):
        raise NotImplementedError('set_auto_mask is not implemented for pydap')

    def __unicode__(self):
        # taken directly from netcdf4-python: netCDF4.pyx
        if not dir(self._grp._pydap_dataset):
            return 'Variable object no longer valid'
        ncdump_var = ['%r\n' % type(self)]
        dimnames = tuple([_tostr(dimname)
                          for dimname in self.dimensions])
        attrs = ['    %s: %s\n' % (name, self.getncattr(name)) for name in
                 self.ncattrs()]
        ncdump_var.append('%s %s(%s)\n' %
                          (self.dtype, self.name, ', '.join(dimnames)))
        ncdump_var = ncdump_var + attrs
        unlimdims = []
        for dimname in self.dimensions:
            dim = self._grp.dimensions[dimname]
            if dim.isunlimited():
                unlimdims.append(dimname)
        ncdump_var.append('unlimited dimensions: %s\n' % ', '.join(unlimdims))
        ncdump_var.append('current shape = %s\n' % repr(self.shape))
        return ''.join(ncdump_var)

    def _getdims(self):
        return self._var.dimensions

    def _get_array_att(self, att):
        if hasattr(self._var, att):
            return getattr(self._var, att)
        else:
            return getattr(self._var.array, att)


class Dimension:
    def __init__(self, grp, name, size=0, isunlimited=True):
        self._grp = grp

        self.size = size
        self._isunlimited = isunlimited

        self._name = name

    def __len__(self):
        return self.size

    def isunlimited(self):
        return self._isunlimited

    def group(self):
        return self._grp

    def __repr__(self):
        if six.PY3:
            return self.__unicode__()
        else:
            return six.text_type(self).encode(default_encoding)

    def __unicode__(self):
        # taken directly from netcdf4-python: netCDF4.pyx
        if not dir(self._grp):
            return 'Dimension object no longer valid'
        if self.isunlimited():
            return (repr(type(self)) +
                    " (unlimited): name = '%s', size = %s\n" %
                    (self._name, len(self)))
        else:
            return (repr(type(self))+": name = '%s', size = %s\n" %
                    (self._name, len(self)))


def _tostr(s):
    try:
        ss = str(s)
    except:
        ss = s
    return ss


class _PhonyVariable:
    # A phony variable to translate getitems:
    def __init__(self):
        pass

    def __getitem__(self, getitem_tuple):
        return getitem_tuple
