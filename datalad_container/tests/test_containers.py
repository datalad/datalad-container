import os.path as op
from os import listdir
from os.path import join as opj

from datalad.api import Dataset
from datalad.api import install
from datalad.api import containers_add
from datalad.utils import chpwd

from datalad.tests.utils import ok_clean_git
from datalad.tests.utils import with_tree
from datalad.tests.utils import ok_
from datalad.tests.utils import eq_
from datalad.tests.utils import assert_true, assert_not_equal, assert_raises, \
    assert_false, assert_equal
from datalad.tests.utils import assert_status
from datalad.tests.utils import assert_result_count
from datalad.tests.utils import assert_in
from datalad.tests.utils import with_tempfile
from datalad.tests.utils import serve_path_via_http
from datalad.support.network import get_local_file_url
from datalad.support.exceptions import IncompleteResultsError
from six.moves.urllib.parse import urljoin


@with_tempfile
@with_tree(tree={'some_container.img': "doesn't matter"})
@serve_path_via_http
def test_containers(ds_path, local_file, url):

    # setup things to add
    #
    # Note: Since "adding" as a container doesn't actually call anything or use
    # the container in some way, but simply registers it, for testing any file
    # is sufficient.
    local_file = get_local_file_url(op.join(local_file, 'some_container.img'))
    remote_file = urljoin(url, 'some_container.img')

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

    # add first "image":
    ds.containers_add(name="first", url=local_file)

    ok_clean_git(ds.repo)
    ok_(op.lexists(op.join(ds.path, ".datalad", "test-environments", "first")))
    eq_(local_file, ds.config.get("datalad.containers.first.url"))

    # add a "remote" one:
    # don't provide url in the call, but in a config:
    ds.config.add("datalad.containers.second.url",
                  value=remote_file,
                  where='dataset')
    ds.save(message="Configure URL for container 'second'")
    ds.containers_add(name="second")

    ok_clean_git(ds.repo)
    ok_(op.lexists(op.join(ds.path, ".datalad", "test-environments", "second")))
    # config wasn't changed:
    eq_(remote_file, ds.config.get("datalad.containers.second.url"))

    res = ds.containers_list()
    assert_result_count(res, 2,
                        status='ok', type='file', action='containers_list')
