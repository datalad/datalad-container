import os
import os.path as op

from six import text_type

from datalad.api import Dataset
from datalad.api import clone
from datalad.api import create
from datalad.api import containers_add
from datalad.api import containers_run
from datalad.api import containers_list

from datalad.utils import Path
from datalad.tests.utils import ok_
from datalad.tests.utils import ok_clean_git
from datalad.tests.utils import assert_false
from datalad.tests.utils import assert_not_in_results
from datalad.tests.utils import assert_in
from datalad.tests.utils import assert_result_count
from datalad.tests.utils import assert_raises
from datalad.tests.utils import ok_file_has_content
from datalad.tests.utils import with_tempfile
from datalad.tests.utils import with_tree
from datalad.tests.utils import skip_if_no_network
from datalad.tests.utils import SkipTest
from datalad.utils import (
    chpwd,
    on_windows,
)
from datalad.support.network import get_local_file_url
from datalad.cmd import (
    StdOutCapture,
    WitlessRunner,
)

from datalad_container.tests.utils import add_pyscript_image

testimg_url = 'shub://datalad/datalad-container:testhelper'


@with_tree(tree={"dummy0.img": "doesn't matter 0",
                 "dummy1.img": "doesn't matter 1"})
def test_run_mispecified(path):
    ds = Dataset(path).create(force=True)
    ds.save(path=["dummy0.img", "dummy1.img"])
    ok_clean_git(path)

    # Abort if no containers exist.
    with assert_raises(ValueError) as cm:
        ds.containers_run("doesn't matter")
    assert_in("No known containers", text_type(cm.exception))

    # Abort if more than one container exists but no container name is
    # specified.
    ds.containers_add("d0", image="dummy0.img")
    ds.containers_add("d1", image="dummy0.img")

    with assert_raises(ValueError) as cm:
        ds.containers_run("doesn't matter")
    assert_in("explicitly specify container", text_type(cm.exception))

    # Abort if unknown container is specified.
    with assert_raises(ValueError) as cm:
        ds.containers_run("doesn't matter", container_name="ghost")
    assert_in("Container selection impossible", text_type(cm.exception))


@with_tree(tree={"i.img": "doesn't matter"})
def test_run_unknown_cmdexec_placeholder(path):
    ds = Dataset(path).create(force=True)
    ds.containers_add("i", image="i.img", call_fmt="{youdontknowme}")
    assert_result_count(
        ds.containers_run("doesn't matter", on_failure="ignore"),
        1,
        path=ds.path,
        action="run",
        status="error")


@skip_if_no_network
@with_tempfile
@with_tempfile
def test_container_files(path, super_path):
    raise SkipTest('SingularityHub is gone for now')
    ds = Dataset(path).create()
    cmd = ['dir'] if on_windows else ['ls']

    # plug in a proper singularity image
    ds.containers_add(
        'mycontainer',
        url=testimg_url,
        image='righthere',
        # the next one is auto-guessed
        #call_fmt='singularity exec {img} {cmd}'
    )
    assert_result_count(
        ds.containers_list(), 1,
        path=op.join(ds.path, 'righthere'),
        name='mycontainer')
    ok_clean_git(path)

    def assert_no_change(res, path):
        # this command changed nothing
        #
        # Avoid specifying the action because it will change from "add" to
        # "save" in DataLad v0.12.
        assert_result_count(
            res, 1, status='notneeded',
            path=path, type='dataset')

    # now we can run stuff in the container
    # and because there is just one, we don't even have to name the container
    res = ds.containers_run(cmd)
    # container becomes an 'input' for `run` -> get request, but "notneeded"
    assert_result_count(
        res, 1, action='get', status='notneeded',
        path=op.join(ds.path, 'righthere'), type='file')
    assert_no_change(res, ds.path)

    # same thing as we specify the container by its name:
    res = ds.containers_run(cmd,
                            container_name='mycontainer')
    # container becomes an 'input' for `run` -> get request, but "notneeded"
    assert_result_count(
        res, 1, action='get', status='notneeded',
        path=op.join(ds.path, 'righthere'), type='file')
    assert_no_change(res, ds.path)

    # we can also specify the container by its path:
    res = ds.containers_run(cmd,
                            container_name=op.join(ds.path, 'righthere'))
    # container becomes an 'input' for `run` -> get request, but "notneeded"
    assert_result_count(
        res, 1, action='get', status='notneeded',
        path=op.join(ds.path, 'righthere'), type='file')
    assert_no_change(res, ds.path)

    # Now, test the same thing, but with this dataset being a subdataset of
    # another one:

    super_ds = Dataset(super_path).create()
    super_ds.install("sub", source=path)

    # When running, we don't discover containers in subdatasets
    with assert_raises(ValueError) as cm:
        super_ds.containers_run(cmd)
    assert_in("No known containers", text_type(cm.exception))
    # ... unless we need to specify the name
    res = super_ds.containers_run(cmd, container_name="sub/mycontainer")
    # container becomes an 'input' for `run` -> get request (needed this time)
    assert_result_count(
        res, 1, action='get', status='ok',
        path=op.join(super_ds.path, 'sub', 'righthere'), type='file')
    assert_no_change(res, super_ds.path)


@with_tempfile
@with_tree(tree={'some_container.img': "doesn't matter"})
def test_custom_call_fmt(path, local_file):
    ds = Dataset(path).create()
    subds = ds.create('sub')

    # plug in a proper singularity image
    subds.containers_add(
        'mycontainer',
        url=get_local_file_url(op.join(local_file, 'some_container.img')),
        image='righthere',
        call_fmt='echo image={img} cmd={cmd} img_dspath={img_dspath} '
                 # and environment variable being set/propagated by default
                 'name=$DATALAD_CONTAINER_NAME'
    )
    ds.save()  # record the effect in super-dataset

    # Running should work fine either withing sub or within super
    out = WitlessRunner(cwd=subds.path).run(
        ['datalad', 'containers-run', '-n', 'mycontainer', 'XXX'],
        protocol=StdOutCapture)
    assert_in('image=righthere cmd=XXX img_dspath=. name=mycontainer',
              out['stdout'])

    out = WitlessRunner(cwd=ds.path).run(
        ['datalad', 'containers-run', '-n', 'sub/mycontainer', 'XXX'],
        protocol=StdOutCapture)
    assert_in('image=sub/righthere cmd=XXX img_dspath=sub', out['stdout'])

    # Test within subdirectory of the super-dataset
    subdir = op.join(ds.path, 'subdir')
    os.mkdir(subdir)
    out = WitlessRunner(cwd=subdir).run(
        ['datalad', 'containers-run', '-n', 'sub/mycontainer', 'XXX'],
        protocol=StdOutCapture)
    assert_in('image=../sub/righthere cmd=XXX img_dspath=../sub', out['stdout'])


@skip_if_no_network
@with_tree(tree={"subdir": {"in": "innards"}})
def test_run_no_explicit_dataset(path):
    raise SkipTest('SingularityHub is gone for now')
    ds = Dataset(path).create(force=True)
    ds.save()
    ds.containers_add("deb", url=testimg_url,
                      call_fmt="singularity exec {img} {cmd}")

    # When no explicit dataset is given, paths are interpreted as relative to
    # the current working directory.

    # From top-level directory.
    with chpwd(path):
        containers_run("cat {inputs[0]} {inputs[0]} >doubled",
                       inputs=[op.join("subdir", "in")],
                       outputs=["doubled"])
        ok_file_has_content(op.join(path, "doubled"), "innardsinnards")

    # From under a subdirectory.
    subdir = op.join(ds.path, "subdir")
    with chpwd(subdir):
        containers_run("cat {inputs[0]} {inputs[0]} >doubled",
                       inputs=["in"], outputs=["doubled"])
    ok_file_has_content(op.join(subdir, "doubled"), "innardsinnards")


@with_tempfile
def test_run_subdataset_install(path):
    path = Path(path)
    ds_src = Dataset(path / "src").create()
    # Repository setup
    #
    # .
    # |-- a/
    # |   |-- a2/
    # |   |   `-- img
    # |   `-- img
    # |-- b/               / module name: b-name /
    # |   `-- b2/
    # |       `-- img
    # |-- c/
    # |   `-- c2/
    # |       `-- img
    # `-- d/               / module name: d-name /
    #     `-- d2/
    #         `-- img
    ds_src_a = ds_src.create("a")
    ds_src_a2 = ds_src_a.create("a2")
    ds_src_b = Dataset(ds_src.pathobj / "b").create()
    ds_src_b2 = ds_src_b.create("b2")
    ds_src_c = ds_src.create("c")
    ds_src_c2 = ds_src_c.create("c2")
    ds_src_d = Dataset(ds_src.pathobj / "d").create()
    ds_src_d2 = ds_src_d.create("d2")

    ds_src.repo.add_submodule("b", name="b-name")
    ds_src.repo.add_submodule("d", name="d-name")
    ds_src.save()

    add_pyscript_image(ds_src_a, "in-a", "img")
    add_pyscript_image(ds_src_a2, "in-a2", "img")
    add_pyscript_image(ds_src_b2, "in-b2", "img")
    add_pyscript_image(ds_src_c2, "in-c2", "img")
    add_pyscript_image(ds_src_d2, "in-d2", "img")

    ds_src.save(recursive=True)

    ds_dest = clone(ds_src.path, str(path / "dest"))
    ds_dest_a2 = Dataset(ds_dest.pathobj / "a" / "a2")
    ds_dest_b2 = Dataset(ds_dest.pathobj / "b" / "b2")
    ds_dest_c2 = Dataset(ds_dest.pathobj / "c" / "c2")
    ds_dest_d2 = Dataset(ds_dest.pathobj / "d" / "d2")
    assert_false(ds_dest_a2.is_installed())
    assert_false(ds_dest_b2.is_installed())
    assert_false(ds_dest_c2.is_installed())
    assert_false(ds_dest_d2.is_installed())

    # Needed subdatasets are installed if container name is given...
    res = ds_dest.containers_run(["arg"], container_name="a/a2/in-a2")
    assert_result_count(
        res, 1, action="install", status="ok", path=ds_dest_a2.path)
    assert_result_count(
        res, 1, action="get", status="ok",
        path=str(ds_dest_a2.pathobj / "img"))
    ok_(ds_dest_a2.is_installed())
    # ... even if the name and path do not match.
    res = ds_dest.containers_run(["arg"], container_name="b-name/b2/in-b2")
    assert_result_count(
        res, 1, action="install", status="ok", path=ds_dest_b2.path)
    assert_result_count(
        res, 1, action="get", status="ok",
        path=str(ds_dest_b2.pathobj / "img"))
    ok_(ds_dest_b2.is_installed())
    # Subdatasets will also be installed if given an image path...
    res = ds_dest.containers_run(["arg"], container_name=str(Path("c/c2/img")))
    assert_result_count(
        res, 1, action="install", status="ok", path=ds_dest_c2.path)
    assert_result_count(
        res, 1, action="get", status="ok",
        path=str(ds_dest_c2.pathobj / "img"))
    ok_(ds_dest_c2.is_installed())
    # ... unless the module name chain doesn't match the subdataset path. In
    # that case, the caller needs to install the subdatasets beforehand.
    with assert_raises(ValueError):
        ds_dest.containers_run(["arg"], container_name=str(Path("d/d2/img")))
    ds_dest.get(ds_dest_d2.path, recursive=True, get_data=False)
    ds_dest.containers_run(["arg"], container_name=str(Path("d/d2/img")))

    # There's no install record if subdataset is already present.
    res = ds_dest.containers_run(["arg"], container_name="a/a2/in-a2")
    assert_not_in_results(res, action="install")
