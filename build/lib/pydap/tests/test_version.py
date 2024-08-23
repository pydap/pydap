import pydap


def test_version() -> None:
    assert pydap.__version__ != "999"
