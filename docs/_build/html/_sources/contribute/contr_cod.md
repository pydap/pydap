# Contributing to the code

To contribute to the code, we recommend to install `PyDAP` within a containerized testing environment. The simplest way is to navigate to the local pydap clone repository and run:

```shell
mamba create -n pydap_tests -c conda-forge python=3.10
mamba env update -n pydap_tests -f ci/environment.yml
mamba activate pydap_tests
```

This will create and activate a test environment called `pydap_tests` which will contain many of the dependencies necessary for appropriately testing pydap.

Then install pydap in development mode:

```shell
pip install -e".[tests,client,netcdf]"
```


At this point, you can use [git](git.md) for making commits to pydap. Make sure the code follows the style guide by running:

```shell
mamba install -c conda-forge pre-commit
```

The above commands install and will automatically run all the pre-commit formatting configuration specified in the yaml-file each time git commit is used.

Lastly, make sure the code is well tested by adding or improving tests in the `src/pydap/tests` repository. pydap uses [pytest](https://docs.pytest.org/en/stable/). To run tests run the following command:

```shell
pytest -v
```
