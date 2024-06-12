Installation
============

Python editing
--------------

You can run Project Hadron in your favorite code editor, Jupyter notebook, Google Colab,
or anywhere else you write Python.

Python version
--------------

We recommend using the latest version of Python. Project Hadron supports Python 3.8 and
newer.

Package installation
--------------------
he best way to install this package is directly from the Python Package Index repository
using pip

.. code-block:: bash

    $ pip install discovery-core

if you want to upgrade your current version then using pip

.. code-block:: bash

    $ pip install --upgrade discovery-core

This will also install or update dependent third party packages. The dependencies are
limited to Python and `PyArrow`_, and thus have a limited footprint and non-disruptive
installation in a data processing environment.

Virtual environments
--------------------

Use a virtual environment to manage the dependencies for your project, both in
development and in production.

What problem does a virtual environment solve? The more Python projects you
have, the more likely it is that you need to work with different versions of
Python libraries, or even Python itself. Newer versions of libraries for one
project can break compatibility in another project.

Virtual environments are independent groups of Python libraries, one for each
project. Packages installed for one project will not affect other projects or
the operating system's packages.

Python comes bundled with the :mod:`venv` module to create virtual
environments.

create an environment
~~~~~~~~~~~~~~~~~~~~~

Create a project folder and a :file:`.venv` folder within:

macOS/Linux

.. code-block:: text

    $ mkdir myproject
    $ cd myproject
    $ python3 -m venv .venv

Windows

.. code-block:: text

    > mkdir myproject
    > cd myproject
    > py -3 -m venv .venv

activate the environment
~~~~~~~~~~~~~~~~~~~~~~~~

Before you work on your project, activate the corresponding environment:

macOS/Linux

.. code-block:: text

    $ . .venv/bin/activate

Windows

.. code-block:: text

    > .venv\Scripts\activate

Your shell prompt will change to show the name of the activated
environment.

Viewing examples
----------------

As said before, you can run Project Hadron in your favorite code editor, but to help any
tutorial documentation, you can find examples of the code on GitHub as Jupyter notebooks.

Jupyter Notebooks and Jupyter Labs are available for installation via the `Python Package Index`_
using pip.

We recommend installing JupyterLab with pip:

.. code-block:: text

    $ pip install jupyterlab

Once installed, launch JupyterLab with:

.. code-block:: text

    $ jupyter lab

For more information on JupyterLab go to the `Jupyter documentation`_


Release process
---------------

Versions to be released will govern and describe how the `discovery-core` produces a new
release.

To find the current version of `discovery-core`, from your terminal run:

.. code-block:: text

    $ python -c "import ds-core; print(ds_core.__version__)"

major releases
~~~~~~~~~~~~~~

A major release will include breaking changes. When it is versioned, it will
be versioned as ``vX.0.0``. For example, if the previous release was
``v10.2.7`` the next version will be ``v11.0.0``.

Breaking changes are changes that break backwards compatibility with prior
versions. The majority of changes to the dependant core abstraction will result in a
major release.

Project Hadron is committed to providing a good user experience
and as such, committed to preserving backwards compatibility as much as possible.
Major releases will be infrequent and will need strong justifications before they
are considered.

minor releases
~~~~~~~~~~~~~~

A minor release will include additional methods, classes, or noticeable modifications
to code in a backward-compatable manner which may include miscellaneous bug fixes.
If the previous version released was ``v10.2.7`` a minor release would be versioned
as ``v10.3.0``.

Minor releases will be backwards compatible with releases that have the same
major version number. In other words, all versions that would start with
``v10.`` should be compatible with each other.

patch releases
~~~~~~~~~~~~~~

A patch release include small and encapsulated code changes that do
not directly effect a major or minor release, for example changing
``round(...`` to ``np.around(...``, and patch bug fixes that can't
wait to be released before a major or minor release. If the previous
version released ``v10.2.7`` the patch release would be versioned
as ``v10.2.8``.

.. _Python Package Index: https://pypi.org/
.. _Jupyter documentation: https://jupyter.org/
.. _PyArrow: https://arrow.apache.org/
