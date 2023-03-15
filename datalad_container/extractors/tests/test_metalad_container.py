import os.path as op
import pytest
import subprocess
import sys
from pathlib import Path
from shutil import which
from unittest.mock import patch

from datalad.api import (
    Dataset,
    clone,
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

# Must come after skiptest or imports will not work
from datalad_container.extractors.metalad_container import MetaladSingularityInspect


class TestMetaladSingularityInspect:

    @with_tempfile
    def test__singularity_inspect_nofile(self, path=None):
        """Singularity causes CalledProcessErorr if path DNE."""
        with pytest.raises(subprocess.CalledProcessError):
            result = MetaladSingularityInspect._singularity_inspect(path)

    def test__singularity_inspect_valid(self, pull_image):
        """Call inspect on a valid singularity container image."""
        result = MetaladSingularityInspect._singularity_inspect(pull_image)

        assert result['type'] == 'container'
        labels = result['data']['attributes']['labels']
        assert_in_labels = [
            'org.label-schema.usage.singularity.version',
            'org.label-schema.build-date',
            'org.label-schema.build-size',
            'org.label-schema.usage.singularity.deffile',
            'org.label-schema.usage.singularity.deffile.from',
            'org.label-schema.usage.singularity.deffile.bootstrap',
            'org.label-schema.usage.singularity.version',
        ]
        for label in assert_in_labels:
            assert label in assert_in_labels
        assert labels['org.label-schema.schema-version'] == '1.0'
        assert result['type'] == 'container'
