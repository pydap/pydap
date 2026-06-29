# How to install

Recent releases of `pydap` may require upgrading Python versions. The latest version of `pydap` requires `Python=>3.12`. `Pydap` can be installed via PyPI as follows:

```shell
    $ pip install pydap
```

or in the case you are using Anaconda:
```shell
    $ conda install pydap
```

```{note}
If you already have `mamba` installed, you can replace all `conda` in the commands with `mamba`.
```

This installation of `pydap` will include the minimal dependencies to allow users to subset remote data on OPeNDAP servers.

```{note}
We recommend to use package installation managers like `conda`/`mamba`. This approach requires having an installation of [Miniconda](https://docs.anaconda.com/miniconda/) or [Anaconda](https://docs.anaconda.com/anaconda/install/).
```

## Reproducible (conda) environments

You can easily use conda to install `pydap` and any optional packages for sharing a reproducible workflow. For example:

```shell
    $ conda create -n pydap_env -c conda-forge python=3.12 pydap
    $ conda activate pydap_env
```

```{note}
If you already have `mamba` installed, you can replace all `conda` in the commands with `mamba`.
```

### Optional to run notebooks in this documentation
- `matplotlib`
- `jupyterlab`
- `cartopy`
- `xarray`

To install the latest `pydap` version (client-only), directly from the GitHub repository, run:

```shell
    $ pip install --upgrade git+https://github.com/pydap/pydap.git
```

This version is not stable as it is being actively developed and improved upon by contributors and maintainers of the `pydap` package.

If you are interested in installing `pydap` in `developer mode` to potentially contribute to the package, go to [Contributing to the code](contribute/contr_cod.md).
