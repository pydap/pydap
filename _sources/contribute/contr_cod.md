# Contributing to the code

To contribute to the code, we recommend to install `PyDAP` within a containerized testing environment, and to follow the approach used worflows in out CI/CD:

```shell
conda create -n pydap_tests -c conda-forge python=3.10
conda env update -n pydap_tests -f ci/environment.yml
conda activate pydap_tests
```

This will create and activate a test environment called `pydap_tests` which will contain many of the dependencies necessary for appropriately testing pydap.

```{note}
If you already have `mamba` installed, you can replace all `conda` in the commands with `mamba`.
```

Then install pydap in development mode:

```shell
pip install -e ".[tests]"
```

At this point, you can use [git](git.md) for making commits to pydap. Make sure the code follows the style guide by running:

```shell
conda install -c conda-forge pre-commit
pre-commit run --all
```

The above commands install and will automatically run all the pre-commit formatting configuration specified in the yaml-file each time git commit is used.

Lastly, make sure the code is well tested by adding or improving tests in the `src/pydap/tests` repository. pydap uses [pytest](https://docs.pytest.org/en/stable/). To run tests run the following command:

```shell
pytest -v
```
