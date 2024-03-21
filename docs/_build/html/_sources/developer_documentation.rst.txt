Contributing to the documentation
---------------------------------

The documentation is built with `sphinx <https://www.sphinx-doc.org/en/master/>`_ and hosted by
`Read the Docs <https://about.readthedocs.com/>`_. To contribute to the documentation follow the 
next steps.

1. Within your development branch, move into the documentation directory of the project.

   .. code-block:: bash

     $ cd pydap/docs

2. Create the mamba environment ``pydap_docs`` to build the documentation defined within the yml-file.

   .. code-block:: bash

     $ mamba env create -f environment.yml
     $ mamba deactivate
     $ mamba activate pydap_docs

3. Edit/commit files and stage them.

4. Build the html files.

   .. code-block:: bash

     $ make clean
     $ make html

5. You can inspect the files. For example to see a new build from `client.rst`. 

   .. code-block:: bash

     $ open _build/html/client.html


6. When satisfied, send a pull request.

