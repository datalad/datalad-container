import gzip
import json
import logging
import os
import os.path as op
import shutil
import sys
from shutil import (
    unpack_archive,
    which,
)

import pytest
from datalad.cmd import (
    StdOutCapture,
    WitlessRunner,
)
from datalad.support.exceptions import CommandError
from datalad.tests.utils_pytest import (
    SkipTest,
    assert_in,
    assert_raises,
    ok_exists,
    with_tempfile,
    with_tree,
)
from datalad.utils import swallow_logs

import datalad_container.adapters.docker as da

if not which("docker"):
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


def get_ref(path, **kwds):
    """Return the reference `load()` loads the image in `path` as"""
    return "datalad-container:" + da.get_image(path, **kwds)


def remove_images(*refs):
    for ref in refs:
        if images_exist([ref]):
            WitlessRunner().run(["docker", "rmi", ref])


def make_legacy_layout(src, dst, repo_tags=None):
    """Convert an image saved by `docker save` of Docker >= 25 (OCI layout)
    into the layout `docker save` produced before"""
    with open(op.join(src, "manifest.json")) as fp:
        entry, = json.load(fp)
    os.makedirs(dst)
    config = op.basename(entry["Config"]) + ".json"
    shutil.copy(op.join(src, entry["Config"]), op.join(dst, config))
    layers = []
    for i, layer in enumerate(entry["Layers"]):
        os.mkdir(op.join(dst, str(i)))
        with open(op.join(src, layer), "rb") as ifh:
            data = ifh.read()
        if data[:2] == b"\x1f\x8b":
            # the containerd image store saves layers as pulled, compressed
            data = gzip.decompress(data)
        with open(op.join(dst, str(i), "layer.tar"), "wb") as ofh:
            ofh.write(data)
        layers.append("{}/layer.tar".format(i))
    with open(op.join(dst, "manifest.json"), "w") as fp:
        json.dump(
            [{"Config": config, "RepoTags": repo_tags, "Layers": layers}], fp)


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
        ref = get_ref(image_dir)
        remove_images(ref)

        if not self.image_existed:
            WitlessRunner().run(["docker", "rmi", self.image_name])

        out = call(["run", image_dir, "ls"], cwd=path,
                   protocol=StdOutCapture)

        # loaded as `ref`, and not tagged with the name it was saved with
        assert images_exist([ref])
        assert images_exist([self.image_name]) == self.image_existed
        assert_in("image", out["stdout"])
        if not self.image_existed:
            # the other tests of this class expect the image under its name,
            # which it was not loaded with
            WitlessRunner().run(["docker", "tag", ref, self.image_name])
        remove_images(ref)

    @with_tempfile(mkdir=True)
    def test_run_legacy_layout(self, path=None):
        # an image saved by Docker < 25, with no index.json, which Docker's
        # containerd image store identifies by a digest it generates on load
        image_dir = op.join(path, "image")
        call(["save", self.image_name, image_dir])
        ref = get_ref(image_dir)
        tag = "datalad-container-tests/legacy:latest"
        try:
            for repo_tags in (None, [tag]):
                legacy_dir = op.join(
                    path, "legacy-{}".format("tagged" if repo_tags else "untagged"))
                make_legacy_layout(image_dir, legacy_dir, repo_tags)
                remove_images(ref)
                with swallow_logs(new_level=logging.DEBUG) as cml:
                    assert da.load(legacy_dir, None, None) == ref
                    # found by `ref`, so not loaded again
                    assert da.load(legacy_dir, None, None) == ref
                    assert cml.out.count("Loading ") == 1
                assert not images_exist([tag])
                out = call(["run", legacy_dir, "ls"], cwd=path,
                           protocol=StdOutCapture)
                assert_in("image", out["stdout"])
        finally:
            remove_images(ref, tag)

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

        try:
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
        finally:
            remove_images(get_ref(op.join(ds.path, ".datalad", "environments",
                                          "bb", "image")))


def test_load_multi_image(tmp_path):
    for v in ["3.15", "3.16", "3.17"]:
        WitlessRunner().run(["docker", "pull", f"alpine:{v}"])
    WitlessRunner().run(["docker", "save", "alpine", "-o", str(tmp_path / "alpine.tar")])
    unpack_archive(tmp_path / "alpine.tar", tmp_path / "alpine")
    with pytest.raises(CommandError):
        call(["run", str(tmp_path / "alpine"), "ls"])
    call(["run", "--repo-tag", "alpine:3.16", str(tmp_path / "alpine"), "ls"])
    remove_images(get_ref(str(tmp_path / "alpine"), repo_tag="alpine:3.16"))


def test_save_multi_image(tmp_path):
    for v in ["3.15", "3.16", "latest"]:
        WitlessRunner().run(["docker", "pull", f"alpine:{v}"])
    call(["save", "alpine", str(tmp_path)])
    with (tmp_path / "manifest.json").open() as fp:
        manifest = json.load(fp)
    assert len(manifest) == 1
    assert manifest[0]["RepoTags"] == ["alpine:latest"]
