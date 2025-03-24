# Contributing to the documentation

Your contributions are welcome! There are many ways to contribute to the documentation:

1. Identify and correct typos.
2. Improve the description of `PyDAP` and overall the DAP model.
3. Cookbooks! We want to know how `PyDAP` and [OPeNDAP](https://www.opendap.org/) are being used, i.e. what kind of questions / problems is helping solve? what is the domains of expertise?
4. Demostrate an optimization to access patterns, i.e. a benchmark.
5. An `OPeNDAP` URL! We want to learn more about available OPeNDAP data urls, and make them accessible to the broad community of PyDAP users. We are strong proponents of `data democratization` and `open science`, and these begin by making your data `Findable`.


The documentation was built using [jupyter-book](https://jupyterbook.org/en/stable/intro.html), which supports different types of files. Here we use `rst` and `ipynb` (executable notebooks).

## How to contribute to the documentation?
To add/edit the documentation, we recommend you follow the previous guides on version control, forking, and branching. That said, you can follow the steps:

1. Navitate to the cloned repository

2. Create/activate the conda environment.
```shell
conda env create -f docs/environment.yml
conda activate pydap_docs
```
```{note}
If you already have `mamba` installed, you can replace all `conda` in the commands with `mamba`.
```

The `docs/environment.yml` file provides a ready-to-use environment (it installs `pydap-server`). However, if you have made new changes to the code, we recommend installing pydap in `dev` mode and making sure that all notebooks properly build.

```shell
pip install -e .
```
or to install directly from the main branch:

```shell
pip install --upgrade git+https://github.com/pydap/pydap.git
```

3. Create a new branch, and set its upstream and use git (see [steps 3 and 4 from contributing to the code](contr_cod.md))

4. Clean any previous built html pages with
```shell
jupyter-book clean docs --all
```

5. Build the docs by running
```shell
jupyter-book build docs
```
Depending on how many changes you have done to the documentation, this last step may take a while. It also depends on the type of files added to the documentation (`ipynb` are slower to build).

6. Once the build process is finished, you can inspect the locally built html files by running:
```shell
open docs/_build/html/index.html
```

```{note}
Make sure to check that **ALL** notebooks were successfully built. This step is important because some of the notebooks require authentications. For testing the documentation it is OK to include passwords/tokens, but when you are getting ready to submit your PR for review, do not include these in the final version of your PR.
```

7. Push all changes and create a PR. `PyDAP` follows the recommendations of keeping the `source` files on `main`, and the `build` files on the `gh-pages` branch.
```{note}
Do not include passwords or tokens. You are only submitting `source` files.
```

8. Once a maintaner of `PyDAP` has approved your PR it will get merged into `main`. The maintainer of `PyDAP` can publish the documentation and update the `gh-pages` branch. Broadly, the steps to publish the documentation (i.e. rebuild the `gh-pages` branch) are detailed and described here: https://jupyterbook.org/en/stable/start/publish.html.
