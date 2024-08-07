# How to install

This package is available for installation from pypi or conda for the stable version, and directly from source (GitHub's repository) for the most recent version under development.

pydap can be installed with minimal required dependencies from [PyPI](https://pypi.org/) via pip as follows:

```shell
pip install pydap
```

### Reproducible environments

We highly recommend using a package installation manager like conda/mamba to install pydap, and any other dependency, in a reproducible and containerized environment. This approach requires having an installation of [Miniconda](https://docs.anaconda.com/miniconda/) or [Anaconda](https://docs.anaconda.com/anaconda/install/).

The easiest way to install `pydap` is to use the conda-forge channel. Open a terminal, then run the following commands:

```shell
mamba create -n pydap -c conda-forge python=3.10 pydap numpy jupyterlab ipython netCDF4 scipy matplotlib cartopy xarray
```

The code above will create a conda environment named "pydap" with many of the commonly used packages for processing and visualizing gridded data, using the latest stable versions (conda release).

To start using `pydap`, you need to activate the environment with the same name, by running:

```shell
mamba activate pydap
```

At this stage, you can install additional packages or remove them if not needed.


[PyPI](https://pypi.org/) provides additional flexibility for installing python packages that otherwise is hard to achieve with other package installation managers. For example, you can install the latest `pydap` version directly from the github repository run within the freshly activated `pydap` environment by running:


```shell
pip install --upgrade git+https://github.com/pydap/pydap.git
```
This version is often not the stable in the sense that it is being actively developed and improved upon by contributors and maintainers of the `pydap` package.

You can install `pydap` in `developer mode`. The `developer` installation of `pydap` comes in handy when actively making local changes to `pydap` (i.e. in your local clone directory), that you are interesting in incorporating into as a new feature, or fixing a bug. This is, the `pydap` installation gets updated realtime after every change to the code.navigate to a local, cloned pydap repository and run:

```shell
pip install -e .
```

This will install `pydap` along with the minimal dependencies defined on the `pyproject.toml` specification. For more on the `developer` approach of installing `pydap`, see [Contributing to the code](contribute/contr_cod.md).


### Lightweight server

`pydap` also implements a lightweight [WSGI](http://wsgi.org/) framework that it can easily be run behind [Apache](https://www.apache.org/). You can install `pydap` in server mode by running

```shell
pip install pydap"[server]"
```

This installation of pydap comes with handlers for NetCDF and csv files. Other handlers can have been developed and can be found in the [Pydap Github Project](https://github.com/pydap).
