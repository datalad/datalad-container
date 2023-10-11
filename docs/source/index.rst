DataLad extension for containerized environments
************************************************

This extension equips DataLad's `run/rerun
<http://datalad.org/for/reproducible-science>`_ functionality with the ability
to transparently execute commands in containerized computational environments.
On re-run, DataLad will automatically obtain any required container at the
correct version prior execution.

Documentation
=============

This is the technical documentation of the functionality and commands provided by this DataLad extension package.
For an introduction to the general topic and a tutorial, please see the DataLad Handbook at https://handbook.datalad.org/r?containers.

* :ref:`Documentation index <genindex>`
* `API reference`_

.. toctree::
   :maxdepth: 1

   changelog
   acknowledgements
   metadata-extraction


API Reference
=============

Command manuals
---------------

.. toctree::
   :maxdepth: 1

   generated/man/datalad-containers-add
   generated/man/datalad-containers-remove
   generated/man/datalad-containers-list
   generated/man/datalad-containers-run


Python API
----------

.. currentmodule:: datalad_container
.. autosummary::
   :toctree: generated

   containers_add
   containers_remove
   containers_list
   containers_run

   utils

.. |---| unicode:: U+02014 .. em dash
