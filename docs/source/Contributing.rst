Contributor Guidelines
======================

This document will go through best practices for contributing to this
project. We welcome and appreciate contributions or ideas for
improvement.

-  `Bug Reports and Feature
   Requests <#bug-reports-and-feature-requests>`__
-  `Local Installation for
   Development <#local-installation-for-development>`__
-  `Branches and Pull Requests <#branches-and-pull-requests>`__
-  `Release Cycles <#release-cycles>`__

Bug Reports and Feature Requests
--------------------------------

Before creating a pull request, we ask contributors to please open a bug
report or feature request first:
`issues <https://github.com/AllenNeuralDynamics/aind-data-transfer-service/issues/new/choose>`__

We will do our best to monitor and maintain the backlog of issues.

Local Installation for Development
----------------------------------

For development,

-  For new features or non-urgent bug fixes, create a branch off of
   ``dev``
-  For an urgent hotfix to our production environment, create a branch
   off of ``main``

Consult the `Branches and Pull Requests <#branches-and-pull-requests>`__
and `Release Cycles <#release-cycles>`__ for more details.

Running a local server
~~~~~~~~~~~~~~~~~~~~~~

From the root directory, run:

.. code:: bash

   pip install -e .[dev]

to install the relevant code for development.

We are working on setting up a local dev server to mock airflow responses.
In the meantime, it’s assumed that you are able to connect to our
development backend. Please reach out to us if you need an airflow
account.

To mock airflow responses for job status list:

.. code:: bash

   cd tests/test_server
   docker build -t json_server .
   docker run -p 8080:3000 json_server

To run uvicorn locally:

.. code:: bash

   export AIND_METADATA_SERVICE_PROJECT_NAMES_URL='http://aind-metadata-service-dev/project_names'
   export AIND_AIRFLOW_SERVICE_URL='http://aind-airflow-service-dev:8080/api/v1/dags/run_list_of_jobs/dagRuns'
   # export AIND_AIRFLOW_SERVICE_JOBS_URL='http://aind-airflow-service-dev:8080/api/v1/dags'
   export AIND_AIRFLOW_SERVICE_JOBS_URL='http://localhost:8080/transform_and_upload'
   export AIND_AIRFLOW_SERVICE_PASSWORD='*****'
   export AIND_AIRFLOW_SERVICE_USER='user'
   export ENV_NAME='local'
   export AWS_DEFAULT_REGION='us-west-2'
   export AIND_AIRFLOW_PARAM_PREFIX='/aind/dev/airflow/variables/job_types'
   export AIND_SSO_SECRET_NAME='/aind/dev/data_transfer_service/sso/secrets'
   uvicorn aind_data_transfer_service.server:app --host 0.0.0.0 --port 5000 --reload

You can now access aind-data-transfer-service at
``http://localhost:5000``.

Branches and Pull Requests
--------------------------

Branch naming conventions
~~~~~~~~~~~~~~~~~~~~~~~~~

Name your branch using the following format:
``<type>-<issue_number>-<short_summary>``

where:

``<type>`` is one of: - **build**: Changes that affect the build system
or external dependencies (e.g., pyproject.toml, setup.py) - **ci**:
Changes to our CI configuration files and scripts (examples:
.github/workflows/ci.yml) - **docs**: Changes to our documentation -
**feat**: A new feature - **fix**: A bug fix - **perf**: A code change
that improves performance - **refactor**: A code change that neither
fixes a bug nor adds a feature, but will make the codebase easier to
maintain - **test**: Adding missing tests or correcting existing tests -
**hotfix**: An urgent bug fix to our production code

``<issue_number>`` references the GitHub issue this branch will close

``<short_summary>`` is a brief description that shouldn’t be more than 3
words.

Some examples:

-  ``feat-12-adds-email-field``
-  ``fix-27-corrects-endpoint``
-  ``test-43-updates-server-test``

We ask that a separate issue and branch are created if code is added
outside the scope of the reference issue.

Commit Messages
~~~~~~~~~~~~~~~

Please format your commit messages as ``<type>: <short summary>`` where
``<type>`` is from the list above and the short summary is one or two
sentences.

Testing and Docstrings
~~~~~~~~~~~~~~~~~~~~~~

We strive for complete code coverage and docstrings, and we also run
code format checks.

-  To run the code format check:

.. code:: bash

   flake8 .

-  There are some helpful libraries that will automatically format the
   code and import statements:

.. code:: bash

   black .

and

.. code:: bash

   isort .

Strings that exceed the maximum line length may still need to be
formatted manually.

-  To run the docstring coverage check and report:

.. code:: bash

   interrogate -v .

This project uses NumPy’s docstring format: `Numpy docstring
standards <https://numpydoc.readthedocs.io/en/latest/format.html>`__

Many IDEs can be configured to automatically format docstrings in the
NumPy convention.

-  To run the unit test coverage check and report:

.. code:: bash

   coverage run -m unittest discover && coverage report

-  To view a more detailed html version of the report, run:

.. code:: bash

   coverage run -m unittest discover && coverage report
   coverage html

and then open ``htmlcov/index.html`` in a browser.

Pull Requests
~~~~~~~~~~~~~

Pull requests and reviews are required before merging code into this
project. You may open a ``Draft`` pull request and ask for a preliminary
review on code that is currently a work-in-progress.

Before requesting a review on a finalized pull request, please verify
that the automated checks have passed first.

Release Cycles
--------------------------

For this project, we have adopted the `Git
Flow <https://www.gitkraken.com/learn/git/git-flow>`__ system. We will
strive to release new features and bug fixes on a two week cycle. The
rough workflow is:

Hotfixes
~~~~~~~~

-  A ``hotfix`` branch is created off of ``main``
-  A Pull Request into is ``main`` is opened, reviewed, and merged into
   ``main``
-  A new ``tag`` with a patch bump is created, and a new ``release`` is
   deployed
-  The ``main`` branch is merged into all other branches

Feature branches and bug fixes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

-  A new branch is created off of ``dev``
-  A Pull Request into ``dev`` is opened, reviewed, and merged

Release branch
~~~~~~~~~~~~~~

-  A new branch ``release-v{new_tag}`` is created
-  Documentation updates and bug fixes are created off of the
   ``release-v{new_tag}`` branch.
-  Commits added to the ``release-v{new_tag}`` are also merged into
   ``dev``
-  Once ready for release, a Pull Request from ``release-v{new_tag}``
   into ``main`` is opened for final review
-  A new tag will automatically be generated
-  Once merged, a new GitHub Release is created manually

Pre-release checklist
~~~~~~~~~~~~~~~~~~~~~

-  ☐ Increment ``__version__`` in
   ``aind_data_transfer_service/__init__.py`` file
-  ☐ Run linters, unit tests, and integration tests
-  ☐ Verify code is deployed and tested in test environment
-  ☐ Update examples
-  ☐ Update documentation

   -  Run:

   .. code:: bash

      sphinx-apidoc -o docs/source/ src
      sphinx-build -b html docs/source/ docs/build/html

-  ☐ Update and build UML diagrams

   -  To build UML diagrams locally using a docker container:

   .. code:: bash

      docker pull plantuml/plantuml-server
      docker run -d -p 8080:8080 plantuml/plantuml-server:jetty

Post-release checklist
~~~~~~~~~~~~~~~~~~~~~~

-  ☐ Merge ``main`` into ``dev`` and feature branches
-  ☐ Edit release notes if needed
-  ☐ Post announcement
