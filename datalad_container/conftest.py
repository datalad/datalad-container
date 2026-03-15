import os
import sys

import pytest

from datalad.conftest import setup_package

from .tests.fixtures import *  # noqa: F401, F403  # lgtm [py/polluting-import]


@pytest.fixture(scope="session", autouse=True)
def ensure_sys_executable_in_path():
    """Ensure sys.executable's directory is first in PATH for test duration.

    This is needed when tests spawn subprocesses that need to import modules
    from the same Python environment that's running pytest.
    """
    python_dir = os.path.dirname(sys.executable)
    original_path = os.environ.get("PATH", "")
    path_dirs = original_path.split(os.pathsep)

    # Check if python_dir is already first in PATH
    if path_dirs and path_dirs[0] != python_dir:
        # Put python_dir first, removing it from elsewhere if present
        filtered_dirs = [d for d in path_dirs if d != python_dir]
        new_path = os.pathsep.join([python_dir] + filtered_dirs)
        os.environ["PATH"] = new_path
        yield
        # Restore original PATH
        os.environ["PATH"] = original_path
    else:
        # PATH is already correct
        yield
