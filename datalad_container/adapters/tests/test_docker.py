from distutils.spawn import find_executable
import os.path as op
import sys

import datalad_container.adapters.docker as da
from datalad.cmd import Runner
from datalad.utils import swallow_outputs
from datalad.support.exceptions import CommandError
from datalad.tests.utils import (
    SkipTest,
    assert_in,
    assert_raises,
    eq_,
    ok_exists,
    with_tempfile,
    with_tree,
)

if not find_executable("docker"):
    raise SkipTest("'docker' not found on path")

RUNNER = Runner()


def call(args, **kwds):
    return RUNNER.run(
        [sys.executable, "-m", "datalad_container.adapters.docker"] + args,
        **kwds)


def list_images(args):
    cmd = ["docker", "images", "--quiet", "--no-trunc"] + args
    return RUNNER.run(cmd)[0].strip().split()


def images_exist(args):
    return bool(list_images(args))


@with_tempfile
def test_docker_save_doesnt_exist(path):
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
            RUNNER.run(["docker", "pull", cls.image_name])

    @classmethod
    def teardown_class(cls):
        if not cls.image_existed and images_exist([cls.image_name]):
            RUNNER.run(["docker", "rmi", cls.image_name])

    @with_tempfile(mkdir=True)
    def test_save_and_run(self, path):
        image_dir = op.join(path, "image")
        call(["save", self.image_name, image_dir])
        ok_exists(op.join(image_dir, "manifest.json"))
        img_ids = list_images([self.image_name])
        assert len(img_ids) == 1
        eq_("sha256:" + da.get_image(image_dir),
            img_ids[0])

        if not self.image_existed:
            RUNNER.run(["docker", "rmi", self.image_name])

        out, _ = call(["run", image_dir, "ls"], cwd=path)

        assert images_exist([self.image_name])
        assert_in("image", out)

    @with_tree({"foo": "content"})
    def test_containers_run(self, path):
        if self.image_existed:
            raise SkipTest(
                "Not pulling with containers-run due to existing image: {}"
                .format(self.image_name))

        from datalad.api import Dataset
        ds = Dataset(path).create(force=True)
        ds.save(path="foo")
        ds.containers_add("bb", url="dhub://" + self.image_name)
        with swallow_outputs() as out:
            ds.containers_run(["cat", "foo"], container_name="bb")
            assert_in("content", out.out)
