.. This file is auto-converted from CHANGELOG.md (make update-changelog) -- do not edit

Change log
**********
::

    ____          _           _                 _ 
   |  _ \   __ _ | |_   __ _ | |      __ _   __| |
   | | | | / _` || __| / _` || |     / _` | / _` |
   | |_| || (_| || |_ | (_| || |___ | (_| || (_| |
   |____/  \__,_| \__| \__,_||_____| \__,_| \__,_|
                                         Container

This is a high level and scarce summary of the changes between releases.
We would recommend to consult log of the `DataLad git
repository <http://github.com/datalad/datalad-container>`__ for more
details.

1.1.2 (January 16, 2021) –
--------------------------

-  Replace use of ``mock`` with ``unittest.mock`` as we do no longer
   support Python 2

1.1.1 (January 03, 2021) –
--------------------------

-  Drop use of ``Runner`` (to be removed in datalad 0.14.0) in favor of
   ``WitlessRunner``

1.1.0 (October 30, 2020) –
--------------------------

-  Datalad version 0.13.0 or later is now required.

-  In the upcoming 0.14.0 release of DataLad, the datalad special remote
   will have built-in support for “shub://” URLs. If ``containers-add``
   detects support for this feature, it will now add the “shub://” URL
   as is rather than resolving the URL itself. This avoids registering
   short-lived URLs, allowing the image to be retrieved later with
   ``datalad get``.

-  ``containers-run`` learned to install necessary subdatasets when
   asked to execute a container from underneath an uninstalled
   subdataset.

1.0.1 (June 23, 2020) –
-----------------------

-  Prefer ``datalad.core.local.run`` to ``datalad.interface.run``. The
   latter has been marked as obsolete since DataLad v0.12 (our minimum
   requirement) and will be removed in DataLad’s next feature release.

1.0.0 (Feb 23, 2020) – not-as-a-shy-one
---------------------------------------

Extension is pretty stable so releasing as 1. MAJOR release, so we could
start tracking API breakages and enhancements properly.

-  Drops support for Python 2 and DataLad prior 0.12

0.5.2 (Nov 12, 2019) –
----------------------

Fixes
~~~~~

-  The Docker adapter unconditionally called ``docker run`` with
   ``--interactive`` and ``--tty`` even when stdin was not attached to a
   TTY, leading to an error.

0.5.1 (Nov 08, 2019) –
----------------------

.. _fixes-1:

Fixes
~~~~~

-  The Docker adapter, which is used for the “dhub://” URL scheme,
   assumed the Python executable was spelled “python”.

-  A call to DataLad’s ``resolve_path`` helper assumed a string return
   value, which isn’t true as of the latest DataLad release candidate,
   0.12.0rc6.

0.5.0 (Jul 12, 2019) – damn-you-malicious-users
-----------------------------------------------

New features
~~~~~~~~~~~~

-  The default result renderer for ``containers-list`` is now a custom
   renderer that includes the container name in the output.

.. _fixes-2:

Fixes
~~~~~

-  Temporarily skip two tests relying on SingularityHub – it is down.

0.4.0 (May 29, 2019) – run-baby-run
-----------------------------------

The minimum required DataLad version is now 0.11.5.

.. _new-features-1:

New features
~~~~~~~~~~~~

-  The call format gained the “{img_dspath}” placeholder, which expands
   to the relative path of the dataset that contains the image. This is
   useful for pointing to a wrapper script that is bundled in the same
   subdataset as a container.

-  ``containers-run`` now passes the container image to ``run`` via its
   ``extra_inputs`` argument so that a run command’s “{inputs}” field is
   restricted to inputs that the caller explicitly specified.

-  During execution, ``containers-run`` now sets the environment
   variable ``DATALAD_CONTAINER_NAME`` to the name of the container.

.. _fixes-3:

Fixes
~~~~~

-  ``containers-run`` mishandled paths when called from a subdirectory.

-  ``containers-run`` didn’t provide an informative error message when
   ``cmdexec`` contained an unknown placeholder.

-  ``containers-add`` ignores the ``--update`` flag when the container
   doesn’t yet exist, but it confusingly still used the word “update” in
   the commit message.

0.3.1 (Mar 05, 2019) – Upgrayeddd
---------------------------------

.. _fixes-4:

Fixes
~~~~~

-  ``containers-list`` recursion actually does recursion.

0.3.0 (Mar 05, 2019) – Upgrayedd
--------------------------------

API changes
~~~~~~~~~~~

-  ``containers-list`` no longer lists containers from subdatasets by
   default. Specify ``--recursive`` to do so.

-  ``containers-run`` no longer considers subdataset containers in its
   automatic selection of a container name when no name is specified. If
   the current dataset has one container, that container is selected.
   Subdataset containers must always be explicitly specified.

.. _new-features-2:

New features
~~~~~~~~~~~~

-  ``containers-add`` learned to update a previous container when passed
   ``--update``.

-  ``containers-add`` now supports Singularity’s “docker://” scheme in
   the URL.

-  To avoid unnecessary recursion into subdatasets, ``containers-run``
   now decides to look for containers in subdatasets based on whether
   the name has a slash (which is true of all subdataset containers).

0.2.2 (Dec 19, 2018) – The more the merrier
-------------------------------------------

-  list/use containers recursively from installed subdatasets
-  Allow to specify container by path rather than just by name
-  Adding a container from local filesystem will copy it now

0.2.1 (Jul 14, 2018) – Explicit lyrics
--------------------------------------

-  Add support ``datalad run --explicit``.

0.2 (Jun 08, 2018) – Docker
---------------------------

-  Initial support for adding and running Docker containers.
-  Add support ``datalad run --sidecar``.
-  Simplify storage of ``call_fmt`` arguments in the Git config, by
   benefiting from ``datalad run`` being able to work with single-string
   compound commands.

0.1.2 (May 28, 2018) – The docs
-------------------------------

-  Basic beginner documentation

0.1.1 (May 22, 2018) – The fixes
--------------------------------

.. _new-features-3:

New features
~~~~~~~~~~~~

-  Add container images straight from singularity-hub, no need to
   manually specify ``--call-fmt`` arguments.

.. _api-changes-1:

API changes
~~~~~~~~~~~

-  Use “name” instead of “label” for referring to a container (e.g.
   ``containers-run -n ...`` instead of ``containers-run -l``.

.. _fixes-5:

Fixes
~~~~~

-  Pass relative container path to ``datalad run``.
-  ``containers-run`` no longer hides ``datalad run`` failures.

0.1 (May 19, 2018) – The Release
--------------------------------

-  Initial release with basic functionality to add, remove, and list
   containers in a dataset, plus a ``run`` command wrapper that injects
   the container image as an input dependency of a command call.
