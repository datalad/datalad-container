import os.path as op
import sys
from distutils.spawn import find_executable

from datalad.cmd import (
    StdOutCapture,
    WitlessRunner,
)
from datalad.support.exceptions import CommandError
from datalad.tests.utils_pytest import (
    SkipTest,
    assert_in,
    assert_raises,
    eq_,
    ok_exists,
    with_tempfile,
    with_tree,
)

import datalad_container.adapters.docker as da

if not find_executable("docker"):
    raise SkipTest("'docker' not found on path")


def call(args, **kwds):
    return WitlessRunner().run(
        [sys.executable, "-m", "datalad_container.adapters.docker"] + args,
        **kwds)


def list_images(args):
    cmd = ["docker", "images", "--quiet", "--no-trunc"] + args
    res = WitlessRunner().run(cmd, protocol=StdOutCapture)
    return res["stdout"].strip().split()


def images_exist(args):
    return bool(list_images(args))


@with_tempfile
def test_docker_save_doesnt_exist(path=None):
    image_name = "idonotexistsurely"
    if images_exist([image_name]):
        raise SkipTest("Image wasn't supposed to exist, but does: {}"
                       .format(image_name))
    with assert_raises(CommandError):
        call(["save", image_name, path])


class TestAdapterBusyBox(object):

    @classmethod
    def setup_class(cls):
        cls.image_name = "busybox:latest"
        if images_exist([cls.image_name]):
            cls.image_existed = True
        else:
            cls.image_existed = False
            try:
                WitlessRunner().run(["docker", "pull", cls.image_name])
            except CommandError:
                # This is probably due to rate limiting.
                raise SkipTest("Plain `docker pull` failed; skipping")

    @classmethod
    def teardown_class(cls):
        if not cls.image_existed and images_exist([cls.image_name]):
            WitlessRunner().run(["docker", "rmi", cls.image_name])

    @with_tempfile(mkdir=True)
    def test_save_and_run(self, path=None):
        image_dir = op.join(path, "image")
        call(["save", self.image_name, image_dir])
        ok_exists(op.join(image_dir, "manifest.json"))
        img_ids = list_images([self.image_name])
        assert len(img_ids) == 1
        eq_("sha256:" + da.get_image(image_dir),
            img_ids[0])

        if not self.image_existed:
            WitlessRunner().run(["docker", "rmi", self.image_name])

        out = call(["run", image_dir, "ls"], cwd=path,
                   protocol=StdOutCapture)

        assert images_exist([self.image_name])
        assert_in("image", out["stdout"])

    @with_tree({"foo": "content"})
    def test_containers_run(self, path=None):
        if self.image_existed:
            raise SkipTest(
                "Not pulling with containers-run due to existing image: {}"
                .format(self.image_name))

        from datalad.api import Dataset
        ds = Dataset(path).create(force=True)
        ds.save(path="foo")
        ds.containers_add("bb", url="dhub://" + self.image_name)

        out = WitlessRunner(cwd=ds.path).run(
            ["datalad", "containers-run", "-n", "bb", "cat foo"],
            protocol=StdOutCapture)
        assert_in("content", out["stdout"])

        # Data can be received on stdin.
        with (ds.pathobj / "foo").open() as ifh:
            out = WitlessRunner(cwd=ds.path).run(
                ["datalad", "containers-run", "-n", "bb", "cat"],
                protocol=StdOutCapture,
                stdin=ifh)
        assert_in("content", out["stdout"])
