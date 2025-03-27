# Contributing to the code

1. Install `PyDAP` within a containerized testing environment.
```shell
conda create -n pydap_tests -c conda-forge python=3.10
conda env update -n pydap_tests -f ci/environment.yml
conda activate pydap_tests
pip install -e .
```
This will create and activate a test environment called `pydap_tests` which will contain many of the dependencies necessary for testing pydap (`pydap-server`) installation (see [how to install](../how_to_install.md)) in `developer mode`.

```{note}
If you already have `mamba` installed, you can replace all `conda` in the commands with `mamba`.
```
2. Clone the repository to your local machine, and fetch the newest commits.
If you do not have yet a local repo, clone it.
```shell
git clone https://github.com/pydap/pydap.git
```
If you already have a local repo, then
```shell
git pull
```
3. Create a new branch, and set its upstream
```shell
git checkout -b new_branch_name
git push --set-upstream origin new_branch_name
```
4. Now use [git](git.md) to add and commit changes to `pydap`.

5. Make sure the code follows the style guide by running:

```shell
conda install -c conda-forge pre-commit
pre-commit run --all
```
The above commands install and will automatically run all the pre-commit formatting configuration specified in the yaml-file each time git commit is used.

6. Make sure the code is well tested by adding or improving tests in the `src/pydap/tests` repository. pydap uses [pytest](https://docs.pytest.org/en/stable/). To run tests run the following command:

```shell
pytest -v
```

7. Push to `upstream`, and make a Pull Request to the main repository. Make sure to well describe the bug, enhancement of the code, and whenever possible, any issue that the proposed changes will close.
