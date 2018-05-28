DataLad extension for containerized environments
************************************************

This extension equips DataLad's `run/rerun
<http://datalad.org/for/reproducible-science>`_ functionality with the ability
to transparently execute commands in containerized computational environments.
On re-run, DataLad will automatically obtain any required container at the
correct version prior execution.

Documentation
=============

* :ref:`Documentation index <genindex>`
* `Getting started`_
* `API reference`_

.. toctree::
   :maxdepth: 1

   changelog
   acknowledgements


Getting started
---------------

.. toctree::
   :hidden:

   generated/examples/basic_demo

.. include:: generated/examples/basic_demo.rst
   :start-after: ***************


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

.. |---| unicode:: U+02014 .. em dash
