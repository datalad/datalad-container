import pytest
from datalad.api import (
    Dataset,
    clone,
)
from datalad.consts import DATALAD_SPECIAL_REMOTE
from datalad.customremotes.base import init_datalad_remote
from datalad.tests.utils_pytest import (
    assert_false,
    assert_in,
    assert_not_in,
    with_tempfile,
)
from datalad.utils import Path

from datalad_container.containers_add import _ensure_datalad_remote

# NOTE: At the moment, testing of the containers-add itself happens implicitly
# via use in other tests.


@with_tempfile
def test_ensure_datalad_remote_init_and_enable_needed(path=None):
    ds = Dataset(path).create(force=True)
    repo = ds.repo
    assert_false(repo.get_remotes())
    _ensure_datalad_remote(repo)
    assert_in("datalad", repo.get_remotes())


@pytest.mark.parametrize("autoenable", [False, True])
@with_tempfile
def test_ensure_datalad_remote_maybe_enable(path=None, *, autoenable):
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