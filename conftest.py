import os
import shutil
import textwrap

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


@pytest.fixture()
def dmrpp_xml_with_missing_attrib():
    """Return a DMR++ XML string with missing attributes for validation testing."""
    return textwrap.dedent("""\
        <?xml version="1.0" encoding="ISO-8859-1"?>
        <Dataset xmlns="http://xml.opendap.org/ns/DAP/4.0#"
        xmlns:dmrpp="http://xml.opendap.org/dap/dmrpp/1.0.0#"
        dapVersion="4.0" dmrVersion="1.0" name="validation_test.nc"
        dmrpp:href="OPeNDAP_DMRpp_DATA_ACCESS_URL" dmrpp:version="3.21.1-451">
            <Dimension size="10"/>
            <Float32 name="data">
                <Dim size="10"/>
                <Attribute name="long_name" type="String">
                    <Value>Test Data</Value>
                </Attribute>
                <dmrpp:chunks fillValue="0" byteOrder="LE">
                    <dmrpp:chunkDimensionSizes>10</dmrpp:chunkDimensionSizes>
                    <dmrpp:chunk offset="100" nBytes="400"/>
                </dmrpp:chunks>
            </Float32>
        </Dataset>
        """)
