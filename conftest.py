import os
import shutil

import pytest


@pytest.fixture(scope="session", autouse=True)
def set_local_env():
    os.environ["LOCAL_DEV"] = "1"


# Define which file to ignore in tests:
collect_ignore = ["setup.py", "bootstrap.py", "docs/conf.py"]

# This line should be deleted once the online documentation is
# fixed:
collect_ignore.append("docs/client.rst")

# These lines should be deleted when all examples use local files:
collect_ignore.append("docs/index.rst")
collect_ignore.append("src/pydap/client.py")


@pytest.fixture
def cache_tmp_dir(tmp_path):
    """
    Per-test temp directory for on-disk caches (sqlite/filesystem).
    Each test gets its own path; pytest cleans tmp_path automatically.
    """
    d = tmp_path / "requests-cache"
    d.mkdir(parents=True, exist_ok=True)
    yield d
    # Best-effort cleanup of WAL/SHM etc. (pytest will remove tmp_path anyway)
    shutil.rmtree(d, ignore_errors=True)
