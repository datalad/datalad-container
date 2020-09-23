from datalad.api import Dataset
from datalad.api import clone
from datalad.consts import DATALAD_SPECIAL_REMOTE
from datalad.customremotes.base import init_datalad_remote
from datalad.tests.utils import assert_false
from datalad.tests.utils import assert_in
from datalad.tests.utils import assert_not_in
from datalad.tests.utils import with_tempfile
from datalad.utils import Path

from datalad_container.containers_add import _ensure_datalad_remote

# NOTE: At the moment, testing of the containers-add itself happens implicitly
# via use in other tests.


@with_tempfile
def test_ensure_datalad_remote_init_and_enable_needed(path):
    ds = Dataset(path).create(force=True)
    repo = ds.repo
    assert_false(repo.get_remotes())
    _ensure_datalad_remote(repo)
    assert_in("datalad", repo.get_remotes())


@with_tempfile
def check_ensure_datalad_remote_maybe_enable(autoenable, path):
    path = Path(path)
    ds_a = Dataset(path / "a").create(force=True)
    init_datalad_remote(ds_a.repo, DATALAD_SPECIAL_REMOTE,
                        autoenable=autoenable)

    ds_b = clone(source=ds_a.path, path=path / "b")
    repo = ds_b.repo
    if not autoenable:
        assert_not_in("datalad", repo.get_remotes())
    _ensure_datalad_remote(repo)
    assert_in("datalad", repo.get_remotes())


def test_ensure_datalad_remote_maybe_enable():
    yield check_ensure_datalad_remote_maybe_enable, False
    yield check_ensure_datalad_remote_maybe_enable, True
