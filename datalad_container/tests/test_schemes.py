import os.path as op

from datalad.api import (
    Dataset,
    containers_add,
    containers_list,
    containers_run,
    create,
)
from datalad.cmd import (
    StdOutCapture,
    WitlessRunner,
)
from datalad.tests.utils_pytest import (
    assert_result_count,
    ok_clean_git,
    ok_file_has_content,
    skip_if_no_network,
    with_tempfile,
)


@skip_if_no_network
@with_tempfile
def test_docker(path=None):  # Singularity's "docker://" scheme.
    ds = Dataset(path).create()
    ds.containers_add(
        "bb",
        url=("docker://busybox@sha256:"
             "7964ad52e396a6e045c39b5a44438424ac52e12e4d5a25d94895f2058cb863a0"))

    img = op.join(ds.path, ".datalad", "environments", "bb", "image")
    assert_result_count(ds.containers_list(), 1, path=img, name="bb")
    ok_clean_git(path)

    WitlessRunner(cwd=ds.path).run(
        ["datalad", "containers-run", "ls", "/singularity"],
        protocol=StdOutCapture)
