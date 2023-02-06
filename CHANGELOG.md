
<a id='changelog-1.1.9'></a>
# 1.1.9 (2023-02-06)

## 🏠 Internal

- Fix the "bump" level for breaking changes in .datalad-release-action.yaml.  [PR #186](https://github.com/datalad/datalad-container/pull/186) (by [@jwodder](https://github.com/jwodder))

- Account for move of @eval_results in datalad core.  [PR #192](https://github.com/datalad/datalad-container/pull/192) (by [@yarikoptic](https://github.com/yarikoptic))

- scriv.ini: Provide full relative path to the templates.  [PR #193](https://github.com/datalad/datalad-container/pull/193) (by [@yarikoptic](https://github.com/yarikoptic))

## 🧪 Tests

- Install Singularity 3 from an official .deb, use newer ubuntu (jammy) on travis.  [PR #188](https://github.com/datalad/datalad-container/pull/188) (by [@bpoldrack](https://github.com/bpoldrack))
# 1.1.8 (Mon Oct 10 2022)

#### 🐛 Bug Fix

- Replace `simplejson` with `json` [#182](https://github.com/datalad/datalad-container/pull/182) ([@christian-monch](https://github.com/christian-monch))

#### 📝 Documentation

- codespell fix some typos [#184](https://github.com/datalad/datalad-container/pull/184) ([@yarikoptic](https://github.com/yarikoptic))

#### 🧪 Tests

- Reenabling tests using SingularityHub [#180](https://github.com/datalad/datalad-container/pull/180) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 2

- Christian Mönch ([@christian-monch](https://github.com/christian-monch))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# 1.1.7 (Tue Aug 30 2022)

#### 🐛 Bug Fix

- DOC: Set language in Sphinx config to en [#178](https://github.com/datalad/datalad-container/pull/178) ([@adswa](https://github.com/adswa))

#### 🧪 Tests

- nose -> pytest, isort imports in tests, unify requirements-devel to correspond to the form as in core [#179](https://github.com/datalad/datalad-container/pull/179) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 2

- Adina Wagner ([@adswa](https://github.com/adswa))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# 1.1.6 (Mon Apr 11 2022)

#### 🐛 Bug Fix

- BF: Disable subdataset result rendering [#175](https://github.com/datalad/datalad-container/pull/175) ([@adswa](https://github.com/adswa))
- DOC: A few typos in comments/docstrings [#173](https://github.com/datalad/datalad-container/pull/173) ([@yarikoptic](https://github.com/yarikoptic))
- Update badges [#172](https://github.com/datalad/datalad-container/pull/172) ([@mih](https://github.com/mih))
- Build docs in standard workflow, not with travis [#171](https://github.com/datalad/datalad-container/pull/171) ([@mih](https://github.com/mih))
- Make six obsolete [#170](https://github.com/datalad/datalad-container/pull/170) ([@mih](https://github.com/mih))
- Adopt standard extension setup [#169](https://github.com/datalad/datalad-container/pull/169) ([@mih](https://github.com/mih) [@jwodder](https://github.com/jwodder) [@yarikoptic](https://github.com/yarikoptic))
- Adopt standard appveyor config [#167](https://github.com/datalad/datalad-container/pull/167) ([@mih](https://github.com/mih))
- Clarify documentation for docker usage [#164](https://github.com/datalad/datalad-container/pull/164) ([@mih](https://github.com/mih))
- Strip unsupported scenarios from travis [#166](https://github.com/datalad/datalad-container/pull/166) ([@mih](https://github.com/mih))
- WIP: Implement the actual command "containers" [#2](https://github.com/datalad/datalad-container/pull/2) ([@mih](https://github.com/mih) [@bpoldrack](https://github.com/bpoldrack))
- Stop using deprecated Repo.add_submodule() [#161](https://github.com/datalad/datalad-container/pull/161) ([@mih](https://github.com/mih))
- BF:Docs: replace incorrect dashes with spaces in command names [#154](https://github.com/datalad/datalad-container/pull/154) ([@loj](https://github.com/loj))

#### ⚠️ Pushed to `master`

- Adjust test to acknowledge reckless behavior ([@mih](https://github.com/mih))
- Slightly relax tests to account for upcoming remove() change ([@mih](https://github.com/mih))

#### 📝 Documentation

- Mention that could be installed from conda-forge [#177](https://github.com/datalad/datalad-container/pull/177) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 6

- Adina Wagner ([@adswa](https://github.com/adswa))
- Benjamin Poldrack ([@bpoldrack](https://github.com/bpoldrack))
- John T. Wodder II ([@jwodder](https://github.com/jwodder))
- Laura Waite ([@loj](https://github.com/loj))
- Michael Hanke ([@mih](https://github.com/mih))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# 1.1.5 (Mon Jun 07 2021)

#### 🐛 Bug Fix

- BF: fix special remotes without "externaltype" [#156](https://github.com/datalad/datalad-container/pull/156) ([@loj](https://github.com/loj))

#### Authors: 1

- Laura Waite ([@loj](https://github.com/loj))

---

# 1.1.4 (Mon Apr 19 2021)

#### 🐛 Bug Fix

- BF+RF: no need to pandoc long description for pypi + correctly boost MODULE/version.py for the release [#152](https://github.com/datalad/datalad-container/pull/152) ([@yarikoptic](https://github.com/yarikoptic))

#### Authors: 1

- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# 1.1.3 (Thu Apr 15 2021)

#### 🐛 Bug Fix

- Set up workflow with auto for releasing & PyPI uploads [#151](https://github.com/datalad/datalad-container/pull/151) ([@yarikoptic](https://github.com/yarikoptic))
- TST: docker_adapter: Skip tests if 'docker pull' in setup fails [#148](https://github.com/datalad/datalad-container/pull/148) ([@kyleam](https://github.com/kyleam))

#### 🏠 Internal

- ENH: containers-add-dhub - add multiple images/tags/repositories from docker hub [#135](https://github.com/datalad/datalad-container/pull/135) ([@kyleam](https://github.com/kyleam) [@yarikoptic](https://github.com/yarikoptic))

#### Authors: 2

- Kyle Meyer ([@kyleam](https://github.com/kyleam))
- Yaroslav Halchenko ([@yarikoptic](https://github.com/yarikoptic))

---

# 1.1.2 (January 16, 2021) --

- Replace use of `mock` with `unittest.mock` as we do no longer support
  Python 2

# 1.1.1 (January 03, 2021) --

- Drop use of `Runner` (to be removed in datalad 0.14.0) in favor of
  `WitlessRunner`

# 1.1.0 (October 30, 2020) -- 

- Datalad version 0.13.0 or later is now required.

- In the upcoming 0.14.0 release of DataLad, the datalad special
  remote will have built-in support for "shub://" URLs.  If
  `containers-add` detects support for this feature, it will now add
  the "shub://" URL as is rather than resolving the URL itself.  This
  avoids registering short-lived URLs, allowing the image to be
  retrieved later with `datalad get`.

- `containers-run` learned to install necessary subdatasets when asked
  to execute a container from underneath an uninstalled subdataset.


# 1.0.1 (June 23, 2020) -- 

- Prefer `datalad.core.local.run` to `datalad.interface.run`.  The
  latter has been marked as obsolete since DataLad v0.12 (our minimum
  requirement) and will be removed in DataLad's next feature release.

# 1.0.0 (Feb 23, 2020) -- not-as-a-shy-one

Extension is pretty stable so releasing as 1. MAJOR release, so we could
start tracking API breakages and enhancements properly.

- Drops support for Python 2 and DataLad prior 0.12

# 0.5.2 (Nov 12, 2019) --

### Fixes

- The Docker adapter unconditionally called `docker run` with
  `--interactive` and `--tty` even when stdin was not attached to a
  TTY, leading to an error.

# 0.5.1 (Nov 08, 2019) --

### Fixes

- The Docker adapter, which is used for the "dhub://" URL scheme,
  assumed the Python executable was spelled "python".

- A call to DataLad's `resolve_path` helper assumed a string return
  value, which isn't true as of the latest DataLad release candidate,
  0.12.0rc6.

# 0.5.0 (Jul 12, 2019) -- damn-you-malicious-users

### New features

- The default result renderer for `containers-list` is now a custom
  renderer that includes the container name in the output.

### Fixes

- Temporarily skip two tests relying on SingularityHub -- it is down.

# 0.4.0 (May 29, 2019) -- run-baby-run

The minimum required DataLad version is now 0.11.5.

### New features

- The call format gained the "{img_dspath}" placeholder, which expands
  to the relative path of the dataset that contains the image.  This
  is useful for pointing to a wrapper script that is bundled in the
  same subdataset as a container.

- `containers-run` now passes the container image to `run` via its
  `extra_inputs` argument so that a run command's "{inputs}" field is
  restricted to inputs that the caller explicitly specified.

- During execution, `containers-run` now sets the environment variable
  `DATALAD_CONTAINER_NAME` to the name of the container.

### Fixes

- `containers-run` mishandled paths when called from a subdirectory.

- `containers-run` didn't provide an informative error message when
  `cmdexec` contained an unknown placeholder.

- `containers-add` ignores the `--update` flag when the container
  doesn't yet exist, but it confusingly still used the word "update"
  in the commit message.

# 0.3.1 (Mar 05, 2019) -- Upgrayeddd

### Fixes

- `containers-list` recursion actually does recursion.


# 0.3.0 (Mar 05, 2019) -- Upgrayedd

### API changes

- `containers-list` no longer lists containers from subdatasets by
  default.  Specify `--recursive` to do so.

- `containers-run` no longer considers subdataset containers in its
   automatic selection of a container name when no name is specified.
   If the current dataset has one container, that container is
   selected.  Subdataset containers must always be explicitly
   specified.

### New features

- `containers-add` learned to update a previous container when passed
  `--update`.

- `containers-add` now supports Singularity's "docker://" scheme in
  the URL.

- To avoid unnecessary recursion into subdatasets, `containers-run`
  now decides to look for containers in subdatasets based on whether
  the name has a slash (which is true of all subdataset containers).

# 0.2.2 (Dec 19, 2018) -- The more the merrier

- list/use containers recursively from installed subdatasets
- Allow to specify container by path rather than just by name
- Adding a container from local filesystem will copy it now

# 0.2.1 (Jul 14, 2018) -- Explicit lyrics

- Add support `datalad run --explicit`.

# 0.2 (Jun 08, 2018) -- Docker

- Initial support for adding and running Docker containers.
- Add support `datalad run --sidecar`.
- Simplify storage of `call_fmt` arguments in the Git config, by benefiting
  from `datalad run` being able to work with single-string compound commands.

# 0.1.2 (May 28, 2018) -- The docs

- Basic beginner documentation

# 0.1.1 (May 22, 2018) -- The fixes

### New features

- Add container images straight from singularity-hub, no need to manually
  specify `--call-fmt` arguments.

### API changes

- Use "name" instead of "label" for referring to a container (e.g.
  `containers-run -n ...` instead of `containers-run -l`.

### Fixes

- Pass relative container path to `datalad run`.
- `containers-run` no longer hides `datalad run` failures.

# 0.1 (May 19, 2018) -- The Release

- Initial release with basic functionality to add, remove, and list
  containers in a dataset, plus a `run` command wrapper that injects
  the container image as an input dependency of a command call.
