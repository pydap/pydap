try:
    from .parser import DMRPPParser
except ImportError as exc:  # pragma: no cover - exercised only when extra missing
    raise ImportError(
        "pydap.virtualizarr requires the 'virtualizarr' extra. "
        "Install it with: pip install 'pydap[virtualizarr]'"
    ) from exc

__all__ = ["DMRPPParser"]
