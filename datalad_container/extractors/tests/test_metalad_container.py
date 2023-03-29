import os.path as op
import pytest
import subprocess
import sys
from pathlib import Path
from shutil import which
from unittest.mock import patch

from datalad.api import (
    clone,
    Dataset,
    meta_extract,
)
from datalad.cmd import (
    StdOutCapture,
    WitlessRunner,
)
from datalad.support.exceptions import CommandError
from datalad.support.external_versions import external_versions, UnknownVersion
from datalad.tests.utils_pytest import (
    SkipTest,
    assert_in,
    assert_raises,
    eq_,
    ok_exists,
    with_tempfile,
    with_tree,
)

if not external_versions["datalad_metalad"]:
    raise SkipTest("skipping metalad tests")

from datalad_container.utils import get_container_command

try:
    container_command = get_container_command()
except RuntimeError:
    raise SkipTest("skipping singularity/apptainer tests")

# Must come after skiptest or imports will not work
from datalad_container.extractors.metalad_container import MetaladContainerInspect


@with_tempfile
def test__container_inspect_nofile(path=None):
    """Singularity causes CalledProcessErorr if path DNE."""
    with pytest.raises(subprocess.CalledProcessError):
        result = MetaladContainerInspect._container_inspect(container_command, path)

def test__container_inspect_valid(singularity_test_image):
    """Call inspect on a valid singularity container image."""
    result = MetaladContainerInspect._container_inspect(
        container_command,
        singularity_test_image["img_path"],
    )
    expected_result = {
        'data': {
            'attributes': {
                'labels':{
                    'org.label-schema.build-date': 'Sat,_19_May_2018_07:06:48_+0000',
                    'org.label-schema.build-size': '62MB',
                    'org.label-schema.schema-version': '1.0',
                    'org.label-schema.usage.singularity.deffile': 'Singularity.testhelper',
                    'org.label-schema.usage.singularity.deffile.bootstrap': 'docker',
                    'org.label-schema.usage.singularity.deffile.from': 'debian:stable-slim', 'org.label-schema.usage.singularity.version':
                    '2.5.0-feature-squashbuild-secbuild-2.5.0.gddf62fb5'
                }
            }
        },
        'type': 'container'
    }
    assert result == expected_result

def test_extract(singularity_test_image):
    ds = singularity_test_image["ds"]
    path = singularity_test_image["img_path"]
    result = meta_extract(dataset=ds, extractorname="container_inspect", path=path)
    assert len(result) == 1

    assert "extracted_metadata" in result[0]["metadata_record"]
    assert result[0]["metadata_record"]["extractor_name"] == 'container_inspect'
    assert result[0]["metadata_record"]["extractor_version"] == MetaladContainerInspect.get_version()
