from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("pydap")
except PackageNotFoundError:
    # package is not installed
    pass
