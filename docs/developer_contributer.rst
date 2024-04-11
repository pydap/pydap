Contributing to the code
------------------------

Report bugs and submit feedback at the `Issue Tracker <https://github.com/pydap/pydap/issues>`_.


**Using Git and GitHub**

Assuming familiarity with git and version control, and that you have an account in GITHUB,
the following is a step-by-step guide for contributing to pydap.

1. Create your own fork of the project on GITHUB if you don't have one already. If you already
have one, then make sure your fork's main branch is up-to-date.

**On your local computer terminal**:

2. If you don't have one already (otherwise skip to step 4.), clone your fork into your computer:

   .. code-block:: bash

    $ git clone https://github.com/your_username_here/pydap.git

3. Move into the local repository and set the remote that points to the original

   .. code-block:: bash

    $ cd pydap
    $ git remote add upstream https://github.com/pydap/pydap.git


4. Update your local repository's main branch to make sure you are completely synced

   .. code-block:: bash

    $ git checkout main
    $ git pull

5. Create a new branch from the up-to-date main branch

   .. code-block:: bash

    $ git checkout -b name_of_branch


6. Edit or add new files as needed. Stage and commit them

   .. code-block:: bash

    $ git add .
    $ git commit -m 'minimally describe changes'


7. Push your branch online

   .. code-block:: bash

    $ git push -u origin name_of_your_branch # `git push` if you have made previous contributions


8. Tests your new branch, making sure that the new changes do not brake any existing tests. If you have added new features make sure. To test your branch, create and activate the test environment ``pydap_tests`` as follows (with ``python=3.10``)

    .. code-block:: bash

     # if you have not created the environment do:
     $ mamba create -n pydap_tests -c conda-forge python=3.10
     $ mamba env update -n pydap_tests -f ci/environment.yml

     # if you already have created the environment simply activate it
     $ mamba activate pydap_tests

9. Install ``pydap`` in development mode

    .. code-block:: bash

     $ pip install -e .

10. Run the tests

    .. code-block:: bash

     $ pytest

11. Make edits/commits as necessary, and push. Once ready, go to your pydap fork repository and click on
``Compare and Pull``.

12. Make sure that the code follows the style guide using the following commands:

   .. code-block:: bash

    $ conda install -c conda-forge pre-commit
    $ pre-commit run --all

   .. note::

    Run the following command to automatically run `black` and `flake8` each time `git commit` is used:

      .. code-block:: bash

       $ pre-commit install


13. Finally, if your branch has no conclicts, click on ``Send Pull Request`` to finish sending the PR.
