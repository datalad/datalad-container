import os.path as op
from datalad.api import Dataset
from datalad.tests.utils import (
    ok_clean_git,
    assert_in,
    assert_is_instance,
    assert_in_results,
    assert_result_count,
    assert_raises
)
from datalad.tests.utils import with_tree
from datalad_container.find_container import find_container


@with_tree(tree={"sub": {"i.img": "doesn't matter"}})
def test_find_containers(path):
    ds = Dataset(path).create(force=True)
    ds.save(path=[op.join('sub', 'i.img')], message="dummy container")
    ds.containers_add("i", image=op.join('sub', 'i.img'))
    ok_clean_git(path)

    # find the only one
    res = find_container(ds)
    assert_is_instance(res, dict)
    assert_result_count([res], 1, status="ok", path=op.join(ds.path, "sub", "i.img"))

    # find by name
    res = find_container(ds, "i")
    assert_is_instance(res, dict)
    assert_result_count([res], 1, status="ok", path=op.join(ds.path, "sub", "i.img"))

    # find by path
    res = find_container(ds, op.join("sub", "i.img"))
    assert_is_instance(res, dict)
    assert_result_count([res], 1, status="ok", path=op.join(ds.path, "sub", "i.img"))

    # don't find another thing
    assert_raises(ValueError, find_container, ds, "nothere")
