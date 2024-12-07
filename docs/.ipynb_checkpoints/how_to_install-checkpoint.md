# How to install

Starting with the latest release `3.5.1`, the installation of `pydap` is now split into two possible options:

## 1. Client-only
To install pydap to use only as a client API, you can do:


```shell
pip install pydap
```
or

```shell
conda install pydap
```

This installation of `pydap` will include the minimal dependencies to allow users to subset remote data on OPeNDAP servers.

## 2. Complete installation
To recover the full installation of pydap, which includes the packages for using pydap as a client and as a server, run:

```shell
conda install pydap-server
```

This installation of `pydap` will include the dependencies to allow users to a) subset remote data on OPeNDAP servers, and b) use pydap's server to make data available.



## Dependencies
### Minimal Required
The following are required to run pydap as a client.

- `python>=3.10`
- `numpy`
- `scipy`
- `requests`
- `beautifulsoup4`
- `lxml`
- `Webob`


### Optional dependencies
- matplotlib
- jupyter-lab
- cartopy
- xarray

These last are only necessary to run some of the tutorial notebooks.

### extra-dependencies
With [PyPI](https://pypi.org/) you can install extra-dependencies. For example:
```shell
pip install pydap"[server,netcdf]"
```

This will install `netCDF4`-python library as well as all other dependencies to use/run `pydap` as a **lightweight server**. With this, `pydap` implements a lightweight [WSGI](http://wsgi.org/) framework that it can easily be run behind [Apache](https://www.apache.org/).


While these are useful, we recommend to use package installation managers like `conda`/`mamba`, as described below. This approach requires having an installation of [Miniconda](https://docs.anaconda.com/miniconda/) or [Anaconda](https://docs.anaconda.com/anaconda/install/).


## Reproducible (conda) environments

You can easily use conda to install `pydap` or `pydap-server`, along with any optional packages for sharing a reproducible workflow. For example:

```shell
conda create -n pydap_env -c conda-forge python=3.10 pydap-server jupyterlab ipython netCDF4 matplotlib
conda activate pydap
```

```{note}
If you already have `mamba` installed, you can replace all `conda` in the commands with `mamba`.
```

To install the latest `pydap` version (client-only), directly from the github repository, run:

```shell
pip install --upgrade git+https://github.com/pydap/pydap.git
```

This version is not stable as it is being actively developed and improved upon by contributors and maintainers of the `pydap` package.

If you are interested in installing `pydap` in `developer mode`, to potentially contribute to the package, got o [Contributing to the code](contribute/contr_cod.md).
