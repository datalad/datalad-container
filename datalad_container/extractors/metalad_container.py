# emacs: -*- mode: python; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4:
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
#
#   See COPYING file distributed along with the datalad package for the
#   copyright and license terms.
#
# ## ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ### ##
"""Metadata extractors for Container Images stored in Datalad's own core storage"""
import json
import logging
import subprocess
import time
from uuid import UUID

from datalad.support.external_versions import external_versions, UnknownVersion
from datalad_metalad.extractors.base import DataOutputCategory, ExtractorResult, FileMetadataExtractor
from datalad_metalad import get_file_id

from datalad_container.utils import get_container_command


CURRENT_VERSION = "0.0.1"

lgr = logging.getLogger('datalad.metadata.extractors.metalad_container')


class MetaladContainerInspect(FileMetadataExtractor):
    """
    Populates metadata singularity/apptainer version and `inspect` output.
    """

    def get_data_output_category(self) -> DataOutputCategory:
        return DataOutputCategory.IMMEDIATE

    def is_content_required(self) -> bool:
        return True

    def get_id(self) -> UUID:
        # Nothing special, made this up - asmacdo
        return UUID('3a28cca6-b7a1-11ed-b106-fc3497650c92')

    @staticmethod
    def get_version() -> str:
        return CURRENT_VERSION

    def extract(self, _=None) -> ExtractorResult:
        container_command = get_container_command()
        return ExtractorResult(
            extractor_version=self.get_version(),
            extraction_parameter=self.parameter or {},
            extraction_success=True,
            datalad_result_dict={
                "type": "container",
                "status": "ok"
            },
            immediate_data={
                "@id": get_file_id(dict(
                    path=self.file_info.path,
                    type=self.file_info.type)),
                "type": self.file_info.type,
                "path": self.file_info.intra_dataset_path,
                "content_byte_size": self.file_info.byte_size,
                "comment": f"SingularityInspect extractor executed at {time.time()}",
                "container_system": container_command,
                "container_system_version": str(external_versions[container_command]),
                "container_inspect": self._container_inspect(container_command, self.file_info.path),
            })

    @staticmethod
    def _container_inspect(command, path) -> str:
        data = subprocess.run(
            [command, "inspect", "--json", path],
            check=True,
            stdout=subprocess.PIPE).stdout.decode()
        return json.loads(data)
