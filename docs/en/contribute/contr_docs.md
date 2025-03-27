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

1. Navigate to the cloned repository on your local machine.

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
or to install `pydap` directly from the main branch:

```shell
pip install --upgrade git+https://github.com/pydap/pydap.git
```

3. Create a new branch, and set its upstream and use git (see [steps 3 and 4 from contributing to the code](contr_cod.md))

4. The documentation is now split into two source files, one in English (you can find it in: `docs/en`), and one in Spanish (los puedes encontrar aqui `docs/es`). Depending on which version of the documentation you are contributing, you can modify the source files.

5. Once you have made changes to the source files of the documentation (either in `docs/en` or `docs/es`), use the `build.sh` to clean and build `html` documentation files (you may need to make `build.sh`1= executable with `chmod +x `)
```shell
cd docs
chmod +x build.sh
./build.sh
```

```{warning}
Many of the tutorial examples in the documentation require EDL Authentication via a local `.netrc` file. Make sure you have one with valid credentials. See [Authentication](../notebooks/Authentication)
```
Depending on how many changes you have done to the documentation, this last step may take a while. It also depends on the type of files added to the documentation (`ipynb` are slower to build).

6. Once the build process is finished, you can inspect the locally built html files. The `build.sh` creates a redirect at the base of the built html files. Thus, to open the English documentation execute
```shell
open _build/html/index.html
```
The redirect means that the English language version of the documentation is the default. To open the Spanish version, execute
```shell
open _build/html/es/intro.html
```

```{warning}
Make sure to check that **ALL** notebooks were successfully built.
```

```{note}
The documentation will have a toggle to manually switch between the English and Spanish versions.
```

7. Push all changes and create a PR. `PyDAP` follows the recommendations of keeping the `source` files on `main`, and the `build` files on the `gh-pages` branch.
```{note}
Do not include passwords or tokens. You are only submitting `source` files.
```

8. Once a maintaner of `PyDAP` has approved your PR it will get merged into `main`. The maintainer of `PyDAP` can publish the documentation and update the `gh-pages` branch. Broadly, the steps to publish the documentation (i.e. rebuild the `gh-pages` branch) are detailed and described here: https://jupyterbook.org/en/stable/start/publish.html.
