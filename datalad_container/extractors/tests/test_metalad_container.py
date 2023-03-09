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
from datalad.tests.utils_pytest import (
    SkipTest,
    assert_in,
    assert_raises,
    eq_,
    ok_exists,
    with_tempfile,
    with_tree,
)

from datalad_container.extractors.metalad_container import MetaladSingularityInspect

test_img_url = 'shub://datalad/datalad-container:testhelper'


class TestMetaladSingularityInspect:

    @with_tempfile
    def test__singularity_inspect_nofile(self, path=None):
        """Singularity causes CalledProcessErorr if path DNE."""
        with pytest.raises(subprocess.CalledProcessError):
            result = MetaladSingularityInspect._singularity_inspect(path)

    # TODO this fixture is 2Gb, lets find a smaller one.
    def test__singularity_inspect_valid(self, pull_image):
        """Call inspect on a valid singularity container image."""
        # TODO using test_img_url, create a session fixture
    #     path = op.join(Path(__file__).resolve().parent, "fixtures", "singularity.img")
        result = MetaladSingularityInspect._singularity_inspect(pull_image)

        assert result['type'] == 'container'
        # Do I need to catch this?
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
