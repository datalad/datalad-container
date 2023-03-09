import pytest
from pathlib import Path

from datalad.api import Dataset
from datalad.tests.utils_pytest import with_tempfile

from datalad_container.tests.utils import add_pyscript_image

TEST_IMG_URL = 'shub://datalad/datalad-container:testhelper'

@pytest.fixture(scope="session")
def pull_image(tmp_path_factory: pytest.TempPathFactory) -> str:
    fixture_file_name = "fixture.sing"
    ds = Dataset(tmp_path_factory.mktemp("singularity_image"))
    ds.create(force=True)
    ds.containers_add(
        'mycontainer',
        url=TEST_IMG_URL,
        image=fixture_file_name,
    )
    img_path = ds.pathobj / fixture_file_name
    ds.get(img_path)
    return img_path