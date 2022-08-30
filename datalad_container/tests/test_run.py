import os
import os.path as op

from datalad.api import (
    Dataset,
    clone,
    containers_add,
    containers_list,
    containers_run,
    create,
)
from datalad.cmd import (
    StdOutCapture,
    WitlessRunner,
)
from datalad.support.network import get_local_file_url
from datalad.tests.utils_pytest import (
    assert_false,
    assert_in,
    assert_not_in_results,
    assert_raises,
    assert_result_count,
    ok_,
    ok_clean_git,
    ok_file_has_content,
    skip_if_no_network,
    with_tempfile,
    with_tree,
)
from datalad.utils import (
    Path,
    chpwd,
    on_windows,
)

from datalad_container.tests.utils import add_pyscript_image

testimg_url = 'shub://datalad/datalad-container:testhelper'


@with_tree(tree={"dummy0.img": "doesn't matter 0",
                 "dummy1.img": "doesn't matter 1"})
def test_run_mispecified(path=None):
    ds = Dataset(path).create(force=True)
    ds.save(path=["dummy0.img", "dummy1.img"])
    ok_clean_git(path)

    # Abort if no containers exist.
    with assert_raises(ValueError) as cm:
        ds.containers_run("doesn't matter")
    assert_in("No known containers", str(cm.value))

    # Abort if more than one container exists but no container name is
    # specified.
    ds.containers_add("d0", image="dummy0.img")
    ds.containers_add("d1", image="dummy0.img")

    with assert_raises(ValueError) as cm:
        ds.containers_run("doesn't matter")
    assert_in("explicitly specify container", str(cm.value))

    # Abort if unknown container is specified.
    with assert_raises(ValueError) as cm:
        ds.containers_run("doesn't matter", container_name="ghost")
    assert_in("Container selection impossible", str(cm.value))


@with_tree(tree={"i.img": "doesn't matter"})
def test_run_unknown_cmdexec_placeholder(path=None):
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
def test_container_files(path=None, super_path=None):
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
    assert_in("No known containers", str(cm.value))
    # ... unless we need to specify the name
    res = super_ds.containers_run(cmd, container_name="sub/mycontainer")
    # container becomes an 'input' for `run` -> get request (needed this time)
    assert_result_count(
        res, 1, action='get', status='ok',
        path=op.join(super_ds.path, 'sub', 'righthere'), type='file')
    assert_no_change(res, super_ds.path)


@with_tempfile
@with_tree(tree={'some_container.img': "doesn't matter"})
def test_custom_call_fmt(path=None, local_file=None):
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

    # Running should work fine either within sub or within super
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
def test_run_no_explicit_dataset(path=None):
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
def test_run_subdataset_install(path=None):
    path = Path(path)
    ds_src = Dataset(path / "src").create()
    # Repository setup
    #
    # .
    # |-- a/
    # |   |-- a2/
    # |   |   `-- img
    # |   `-- img
    # |-- b/
    # |   `-- b2/
    # |       `-- img
    # |-- c/
    # |   `-- c2/
    # |       `-- img
    # `-- d/
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
    res = ds_dest.containers_run(["arg"], container_name="b/b2/in-b2")
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
    ds_dest.containers_run(["arg"], container_name=str(Path("d/d2/img")))

    # There's no install record if subdataset is already present.
    res = ds_dest.containers_run(["arg"], container_name="a/a2/in-a2")
    assert_not_in_results(res, action="install")
