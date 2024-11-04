pydap
=====
[![Ubuntu CI](https://github.com/pydap/pydap/actions/workflows/run_tests_ubuntu.yml/badge.svg
)](https://github.com/pydap/pydap/actions/workflows/run_tests_ubuntu.yml)
[![MacOS CI](https://github.com/pydap/pydap/actions/workflows/run_tests_macos.yml/badge.svg
)](https://github.com/pydap/pydap/actions/workflows/run_tests_macos.yml)
[![Python](https://img.shields.io/pypi/pyversions/pydap.svg)](https://pypi.python.org/pypi/pydap/)
[![PyPI](https://img.shields.io/pypi/v/pydap.svg?maxAge=2592000?style=plastic)](https://pypi.python.org/pypi/pydap/)
[![conda forge](https://anaconda.org/conda-forge/pydap/badges/version.svg)](https://anaconda.org/conda-forge/pydap)
[![black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![license](https://img.shields.io/github/license/mashape/apistatus.svg)](https://github.com/pydap/pydap)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/pydap/pydap/main.svg)](https://results.pre-commit.ci/latest/github/pydap/pydap/main)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.14010567.svg)](https://doi.org/10.5281/zenodo.14010567)


What is pydap?
----------
[pydap](https://pydap.github.io/pydap/) is an open-source implementation of the OPeNDAP protocol, written from scratch in pure python. You can use pydap to access scientific data available on the many OPeNDAP servers publically available through the internet. Because pydap supports remote and lazy evaluation, you can access the data without having to download it; instead, you work with special array and iterable objects that download data on-the-fly as necessary, saving bandwidth and time. The module also comes with a robust-but-lightweight OPeNDAP server, implemented as a WSGI application.

Why pydap?
----------
Originally developed in the 2000s, pydap is one of the oldest open-source python projects available and it gets rutinely developed and maintained by the OPeNDAP community at large. In addition, pydap is a long-recognized backend engine (and dependency) for [xarray](https://github.com/pydata/xarray) and chances are you have used pydap in past without knowing.


Quickstart
----------
pydap is a lighweight python package that you can use in either
of the two modalities: a client and as a server.
You can install the latest version using
[pip](http://pypi.python.org/pypi/pip). After [installing
pip](http://www.pip-installer.org/en/latest/installing.html) you can
install pydap with this command:

```bash
    $ pip install pydap
```
This will install pydap together with all the required
dependencies.

pydap is also available through [Anaconda](https://www.anaconda.com/).
Below we install pydap and its required dependencies, along with common
additional packages in a fresh conda environment named pydap:

```bash
$ conda create -n pydap -c conda-forge python=3.10 pydap numpy">=2.0" jupyterlab ipython netCDF4 scipy matplotlib
```
Now you simply activate the pydap environment:
```bash
conda activate pydap
```
(NOTE: if you have `mamba` install, you can replace `conda` in the commands with `mamba`). You can now use pydap as a client and open any remotely served
dataset, and pydap will download the accessed data on-the-fly as needed. For example consider [this](http://test.opendap.org:8080/opendap/catalog/ghrsst/20210102090000-JPL-L4_GHRSST-SSTfnd-MUR-GLOB-v02.0-fv04.1.nc.dmr.html) dataset currently hosted on OPeNDAP's Hyrax data server

```python
    from pydap.client import open_url
    pyds = open_url('http://test.opendap.org:8080/opendap/catalog/ghrsst/20210102090000-JPL-L4_GHRSST-SSTfnd-MUR-GLOB-v02.0-fv04.1.nc', protocol='dap4')
    pyds.tree()
```
```python
    .20210102090000-JPL-L4_GHRSST-SSTfnd-MUR-GLOB-v02.0-fv04.1.nc
    ├──time
    ├──lat
    ├──lon
    ├──analysed_sst
    ├──analysis_error
    ├──mask
    ├──sea_ice_fraction
    ├──dt_1km_data
    └──sst_anomaly
```
```python
    pyds['sst_anomaly'].shape
```
```python
    (1, 17999, 36000)
```
**NOTE** In the example above, no data was downloaded, it was all lazily evaluated using OPeNDAP's DMR (DAP4) metadata representation. For more information, please check the documentation on [using pydap
as a client](https://pydap.github.io/pydap/client.html).

pydap also comes with a simple server, implemented as a [WSGI]( http://wsgi.org/)
application. To use it, you first need to install the server and
optionally a data handler:

## Running pydap as a Server

```bash
    $ pip install "pydap[server,netcdf]"
```

This will install the necessary dependencies for running pydap as a server, along with extra dependencies for handling [netCDF4](https://www.unidata.ucar.edu/software/netcdf/) dataset. Now create a directory
for your server data.

To run the server just issue the command:

```bash

    $ pydap --data ./myserver/data/ --port 8001 --workers 4 --threads 4
```

This will start a standalone server running on the default http://localhost:8001/,
serving netCDF files from ``./myserver/data/`` Since the server uses the
[WSGI](http://wsgi.org/) standard, pydap uses by default 1 worker and 1
thread, but these can be defined by the user like in the case above (4 workers
and 4 threads). Pydap can also easily be run behind Apache. The [server
documentation](https://pydap.github.io/pydap/server.html) has
more information on how to better deploy pydap.

## Documentation

For more information, see [the pydap documentation](https://pydap.github.io/pydap/).

## Help and Community

If you need any help with pydap, open an issue in this repository. You can also send an email to
the [mailing list](http://groups.google.com/group/pydap/). Finally, ff you have a broader OPeNDAP access question, you can reach the OPeNDAP team on the [OPeNDAP Discourse](https://opendap.discourse.group/)!
