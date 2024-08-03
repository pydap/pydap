# Contributing to the documentation

Thank your for your interest of contributing to `PyDAP`'s documentation. We are interests in additions that

1. Identify and correct typos.
2. Improve the description of the pydap and overall DAP model.
3. Cookbooks! We want to know how `PyDAP` and broadly [OPeNDAP](https://www.opendap.org/) is being used, i.e. what kind of questions / problems is helping solve, domain of expertise, etc.
4. Demostrate an optimization to access patterns, i.e. a benchmark.
5. An OPeNDAP URL! We want to learn more about data available, and make it accessible for people. We are strong proponents of `data democratization` and `open science`, and these begin by making your data `Findable`.


The notebooks was build using [jupyter-book](https://jupyterbook.org/en/stable/intro.html), which supports different types of files. Here we use `rst` and `ipynb` (executable notebooks).


To add/edit the documentation, we recommend you follow the previous guides on version control, forking, and branching. That said, you can follow the steps:

1. Navitate to the cloned repository

2. Create/activate the conda environment and install the `PyDAP` in `dev` mode.
```shell
mamba env create -f docs/environment.yml
mamba activate pydap_docs
pip install -e ."[server,netcdf,client]"
```

3. At this point, you can use [git](git.md) for making commits to `PyDAP`'s documentation. Make sure the code follows the style guide by running:

```shell
mamba install -c conda-forge pre-commit
```

The above commands install and will automatically run all the pre-commit formatting configuration specified in the yaml-file each time git commit is used.


4. Clean any previous built html pages
```shell
jupyter-book clean docs --all
```

5. build the docs by running
```shell
jupyter-book build docs
```
Depending on how many changes you have done to the documentation, this last step may take a while. It also depends on the type of files added to the documentation (`ipynb` are much slower to build).

6. Once the build process is finished, you can inspect the locally built html files by running:
```shell
open docs/_build/html/index.html
```

7. Push all changes to your forked repository and create a PR.
