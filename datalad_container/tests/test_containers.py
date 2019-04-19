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
from datalad.tests.utils import ok_file_has_content
from datalad.tests.utils import assert_equal
from datalad.tests.utils import assert_status
from datalad.tests.utils import assert_raises
from datalad.tests.utils import assert_result_count
from datalad.tests.utils import assert_in
from datalad.tests.utils import assert_not_in
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
@with_tree(tree={"foo.img": "doesn't matter 0",
                 "bar.img": "doesn't matter 1"})
def test_add_local_path(path, local_file):
    ds = Dataset(path).create()
    res = ds.containers_add(name="foobert",
                            url=op.join(local_file, "foo.img"))
    foo_target = op.join(path, ".datalad", "environments", "foobert", "image")
    assert_result_count(res, 1, status="ok", type="file", path=foo_target,
                        action="containers_add")
    # We've just copied and added the file.
    assert_not_in(ds.repo.WEB_UUID, ds.repo.whereis(foo_target))

    # We can force the URL to be added. (Note: This works because datalad
    # overrides 'annex.security.allowed-url-schemes' in its tests.)
    ds.containers_add(name="barry",
                      url=get_local_file_url(op.join(local_file, "bar.img")))
    bar_target = op.join(path, ".datalad", "environments", "barry", "image")
    assert_in(ds.repo.WEB_UUID, ds.repo.whereis(bar_target))


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


@with_tempfile
@with_tree(tree={'foo.img': "foo",
                 'bar.img': "bar"})
@serve_path_via_http
def test_container_update(ds_path, local_file, url):
    url_foo = get_local_file_url(op.join(local_file, 'foo.img'))
    url_bar = get_local_file_url(op.join(local_file, 'bar.img'))
    img = op.join(".datalad", "environments", "foo", "image")

    ds = Dataset(ds_path).create()

    ds.containers_add(name="foo", call_fmt="call-fmt1", url=url_foo)

    # Abort without --update flag.
    res = ds.containers_add(name="foo", on_failure="ignore")
    assert_result_count(res, 1, action="containers_add", status="impossible")

    # Abort if nothing to update is specified.
    res = ds.containers_add(name="foo", update=True, on_failure="ignore")
    assert_result_count(res, 1, action="containers_add", status="impossible",
                        message="No values to update specified")

    # Update call format.
    ds.containers_add(name="foo", update=True, call_fmt="call-fmt2")
    assert_equal(ds.config.get("datalad.containers.foo.cmdexec"),
                 "call-fmt2")
    ok_file_has_content(op.join(ds.path, img), "foo")

    # Update URL/image.
    ds.drop(img)  # Make sure it works even with absent content.
    res = ds.containers_add(name="foo", update=True, url=url_bar)
    assert_result_count(res, 1, action="remove", status="ok", path=img)
    assert_result_count(res, 1, action="save", status="ok")
    ok_file_has_content(op.join(ds.path, img), "bar")


@with_tempfile
@with_tempfile
@with_tree(tree={'some_container.img': "doesn't matter"})
def test_container_from_subdataset(ds_path, src_subds_path, local_file):

    # prepare a to-be subdataset with a registered container
    src_subds = Dataset(src_subds_path).create()
    src_subds.containers_add(name="first",
                         url=get_local_file_url(op.join(local_file,
                                                        'some_container.img'))
                         )
    # add it as subdataset to a super ds:
    ds = Dataset(ds_path).create()
    ds.install("sub", source=src_subds_path)
    # add it again one level down to see actual recursion:
    Dataset(op.join(ds.path, "sub")).install("subsub", source=src_subds_path)

    # We come up empty without recursive:
    res = ds.containers_list(recursive=False)
    assert_result_count(res, 0)

    # query available containers from within super:
    res = ds.containers_list(recursive=True)
    assert_result_count(res, 2)

    # default location within the subdataset:
    target_path = op.join(ds_path, 'sub',
                          '.datalad', 'environments', 'first', 'image')
    assert_result_count(
        res, 1,
        name='sub/first', type='file', action='containers', status='ok',
        path=target_path)

    # not installed subdataset doesn't pose an issue:
    sub2 = ds.create("sub2")
    assert_result_count(ds.subdatasets(), 2, type="dataset")
    ds.uninstall("sub2")
    from datalad.tests.utils import assert_false
    assert_false(sub2.is_installed())

    # same results as before, not crashing or somehow confused by a not present
    # subds:
    res = ds.containers_list(recursive=True)
    assert_result_count(res, 2)
    # default location within the subdataset:
    target_path = op.join(ds_path, 'sub',
                          '.datalad', 'environments', 'first', 'image')
    assert_result_count(
        res, 1,
        name='sub/first', type='file', action='containers', status='ok',
        path=target_path)
