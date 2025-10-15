"""Tests of oci adapter that depend on skopeo or docker being installed.

See datalad_container.adapters.tests.test_oci for tests that do not depend on
this.
"""
from shutil import which

from datalad.api import (
    Dataset,
    # FIXME: This is needed to register the dataset method, at least when
    # running this single test module. Shouldn't that no longer be the case
    # after datalad's 4b056a251f (BF/RF: Automagically find and import a
    # datasetmethod if not yet bound, 2019-02-10)?
    containers_add,
)
from datalad.cmd import (
    StdOutErrCapture,
    WitlessRunner,
)
from datalad.consts import (
    DATALAD_SPECIAL_REMOTE,
    DATALAD_SPECIAL_REMOTES_UUIDS,
)
from datalad_container.adapters import oci
from datalad_container.adapters.utils import get_docker_image_ids
from datalad.tests.utils_pytest import (
    assert_in,
    integration,
    ok_,
    skip_if_no_network,
    SkipTest,
    slow,
    with_tempfile,
)
import pytest

for dep in ["skopeo", "docker"]:
    if not which(dep):
        raise SkipTest("'{}' not found on path".format(dep))


@skip_if_no_network
@integration
@slow  # ~13s
@with_tempfile
def test_oci_add_and_run(path=None):
    ds = Dataset(path).create(cfg_proc="text2git")
    ds.containers_add(url="oci:docker://busybox:1.30", name="bb")

    image_path = ds.repo.pathobj / ".datalad" / "environments" / "bb" / "image"
    image_id = oci.get_image_id(image_path)
    existed = image_id in get_docker_image_ids()

    try:
        out = WitlessRunner(cwd=ds.path).run(
            ["datalad", "containers-run", "-n", "bb",
             "sh -c 'busybox | head -1'"],
            protocol=StdOutErrCapture)
    finally:
        if not existed:
            WitlessRunner().run(["docker", "rmi", image_id])
    assert_in("BusyBox v1.30", out["stdout"])

    from datalad.downloaders.providers import Providers
    if not Providers.from_config_files().get_provider(
            "https://registry-1.docker.io/v2/library",
            only_nondefault=True):
        # The rest of the test is about Docker Hub registry links, which
        # require provider configuration for authentication.
        return

    layers = [r["path"]
              for r in ds.status(image_path / "blobs", annex="basic",
                                 result_renderer=None)
              if "key" in r]
    ok_(layers)

    dl_uuid = DATALAD_SPECIAL_REMOTES_UUIDS[DATALAD_SPECIAL_REMOTE]
    for where_res in ds.repo.whereis(list(map(str, layers))):
        assert_in(dl_uuid, where_res)


@pytest.mark.ai_generated
@skip_if_no_network
@integration
@slow
@with_tempfile
def test_oci_ghcr_registry(path=None):
    """Test adding and running a container from GitHub Container Registry (ghcr.io)."""
    ds = Dataset(path).create(cfg_proc="text2git")
    ds.containers_add(url="oci:docker://ghcr.io/astral-sh/uv:latest", name="uv")

    image_path = ds.repo.pathobj / ".datalad" / "environments" / "uv" / "image"
    image_id = oci.get_image_id(image_path)
    existed = image_id in get_docker_image_ids()

    try:
        out = WitlessRunner(cwd=ds.path).run(
            ["datalad", "containers-run", "-n", "uv", "--version"],
            protocol=StdOutErrCapture)
    finally:
        if not existed:
            WitlessRunner().run(["docker", "rmi", image_id])

    # uv --version should output something like "uv X.Y.Z"
    assert_in("uv", out["stdout"])


@pytest.mark.ai_generated
@skip_if_no_network
@integration
@slow
@with_tempfile
def test_oci_quay_registry(path=None):
    """Test adding and running a container from Quay.io registry."""
    ds = Dataset(path).create(cfg_proc="text2git")
    ds.containers_add(
        url="oci:docker://quay.io/linuxserver.io/baseimage-alpine:3.18",
        name="alpine"
    )

    image_path = ds.repo.pathobj / ".datalad" / "environments" / "alpine" / "image"
    image_id = oci.get_image_id(image_path)
    existed = image_id in get_docker_image_ids()

    try:
        out = WitlessRunner(cwd=ds.path).run(
            ["datalad", "containers-run", "-n", "alpine",
             "cat /etc/os-release"],
            protocol=StdOutErrCapture)
    finally:
        if not existed:
            WitlessRunner().run(["docker", "rmi", image_id])

    # Should contain Alpine Linux identifier
    assert_in("Alpine", out["stdout"])
