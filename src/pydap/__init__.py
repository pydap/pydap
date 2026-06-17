import pyexpat

from ._version import __version__

if pyexpat.version_info < (2, 4, 0):
    import warnings

    warnings.warn(
        f"expat {pyexpat.EXPAT_VERSION} is vulnerable to DoS attacks (CVE-2022-23852). "
        "Upgrade your Python installation or system expat library to expat >= 2.4.0.",
        RuntimeWarning,
        stacklevel=2,
    )


__all__ = ["__version__"]
