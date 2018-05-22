import os.path as op

from datalad.api import Dataset
from datalad.api import install
from datalad.api import containers_add
from datalad.api import containers_remove
from datalad.api import containers_list

from datalad.tests.utils import SkipTest
from datalad.tests.utils import ok_clean_git
from datalad.tests.utils import with_tree
from datalad.tests.utils import ok_
from datalad.tests.utils import assert_status
from datalad.tests.utils import assert_raises
from datalad.tests.utils import assert_result_count
from datalad.tests.utils import with_tempfile
from datalad.tests.utils import serve_path_via_http
from datalad.support.network import get_local_file_url


@with_tempfile
def test_add_noop(path):
    ds = Dataset(path).create()
    ok_clean_git(ds.path)
    assert_raises(TypeError, ds.containers_add)
    # fails when there is no image
    assert_status('error', ds.containers_add('name', on_failure='ignore'))
    # no config change
    ok_clean_git(ds.path)
    # place a dummy "image" file
    with open(op.join(ds.path, 'dummy'), 'w') as f:
        f.write('some')
    ds.add('dummy')
    ok_clean_git(ds.path)
    # config will be added, as long as there is a file, even when URL access
    # fails
    res = ds.containers_add('broken', url='bogus', image='dummy',
                            on_failure='ignore')
    assert_status('ok', res)
    assert_result_count(res, 1, action='save', status='ok')


@with_tempfile
@with_tree(tree={'some_container.img': "doesn't matter"})
@serve_path_via_http
def test_container_files(ds_path, local_file, url):
    # setup things to add
    #
    # Note: Since "adding" as a container doesn't actually call anything or use
    # the container in some way, but simply registers it, for testing any file
    # is sufficient.
    local_file = get_local_file_url(op.join(local_file, 'some_container.img'))

    # prepare dataset:
    ds = Dataset(ds_path).create()
    # non-default location:
    ds.config.add("datalad.containers.location",
                  value=op.join(".datalad", "test-environments"),
                  where='dataset')
    ds.save(message="Configure container mountpoint")

    # no containers yet:
    res = ds.containers_list()
    assert_result_count(res, 0)

    # add first "image": must end up at the configured default location
    target_path = op.join(
        ds.path, ".datalad", "test-environments", "first", "image")
    res = ds.containers_add(name="first", url=local_file)
    ok_clean_git(ds.repo)

    assert_result_count(res, 1, status="ok", type="file", path=target_path,
                        action="containers_add")
    ok_(op.lexists(target_path))

    res = ds.containers_list()
    assert_result_count(res, 1)
    assert_result_count(
        res, 1,
        name='first', type='file', action='containers', status='ok',
        path=target_path)

    # and kill it again
    # but needs name
    assert_raises(TypeError, ds.containers_remove)
    res = ds.containers_remove('first', remove_image=True)
    assert_status('ok', res)
    assert_result_count(ds.containers_list(), 0)
    # image removed
    assert(not op.lexists(target_path))


@with_tree(tree={'some_container.img': "doesn't matter",
                 'some_recipe.txt': "nobody cares"})
@with_tempfile(mkdir=True)
def test_container_dataset(container_ds, target_ds):

    raise SkipTest("TODO")

    # build a container dataset:
    # import pdb; pdb.set_trace()
    # c_ds = Dataset(container_ds).create(force=True)
    # c_ds.add(['some_container.img', 'some_recipe.txt'])
    # c_ds.config.add("datalad.containers."....)

    # save()

    # serve_via_http
    #


def test_container_from_subdataset():
    raise SkipTest("TODO")
