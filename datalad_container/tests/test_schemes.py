import os.path as op

from datalad.api import Dataset
from datalad.api import create
from datalad.api import containers_add
from datalad.api import containers_list
from datalad.api import containers_run

from datalad.utils import swallow_outputs
from datalad.tests.utils import ok_clean_git
from datalad.tests.utils import ok_file_has_content
from datalad.tests.utils import assert_result_count
from datalad.tests.utils import with_tempfile
from datalad.tests.utils import skip_if_no_network


@skip_if_no_network
@with_tempfile
def test_docker(path):  # Singularity's "docker://" scheme.
    ds = Dataset(path).create()
    ds.containers_add(
        "bb",
        url=("docker://busybox@sha256:"
             "7964ad52e396a6e045c39b5a44438424ac52e12e4d5a25d94895f2058cb863a0"))

    img = op.join(ds.path, ".datalad", "environments", "bb", "image")
    assert_result_count(ds.containers_list(), 1, path=img, name="bb")
    ok_clean_git(path)

    with swallow_outputs():
        ds.containers_run(["ls", "/singularity"])
