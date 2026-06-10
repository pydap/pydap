"""A pandas-backed pydap handler for tabular sequence datasets."""

import copy
import json
import os
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from stat import ST_MTIME

import numpy as np

from pydap.exceptions import OpenFileError
from pydap.handlers.lib import BaseHandler, IterData
from pydap.model import BaseType, DatasetType, SequenceType

_METADATA_KEYS = frozenset(("dataset", "sequence", "columns"))
_COMPRESSION_EXTENSIONS = frozenset((".bz2", ".gz", ".xz", ".zip", ".zst"))
_PANDAS_READERS = {
    ".csv": ("read_csv", {}),
    ".tsv": ("read_csv", {"sep": "\t"}),
    ".txt": ("read_csv", {}),
    ".xls": ("read_excel", {}),
    ".xlsx": ("read_excel", {}),
    ".xlsm": ("read_excel", {}),
    ".json": ("read_json", {}),
    ".xml": ("read_xml", {}),
    ".parquet": ("read_parquet", {}),
    ".pq": ("read_parquet", {}),
}
_EXTENSION_PATTERN = "|".join(
    re.escape(extension.lstrip("."))
    for extension in sorted(_PANDAS_READERS, key=len, reverse=True)
)


class SequenceHandler(BaseHandler):
    """Expose a pandas-readable file as a single pydap sequence."""

    extensions = re.compile(
        r"^.*\.({extensions})(\.(gz|bz2|zip|xz|zst))?$".format(
            extensions=_EXTENSION_PATTERN
        ),
        re.IGNORECASE,
    )

    def __init__(
        self,
        filepath,
        sequence_name="sequence",
        reader=None,
        read_kwargs=None,
        metadata_path=None,
    ):
        BaseHandler.__init__(self)
        try:
            dataframe = read_dataframe(filepath, reader=reader, read_kwargs=read_kwargs)
        except Exception as exc:
            message = "Unable to open file {filepath}: {exc}".format(
                filepath=filepath, exc=exc
            )
            raise OpenFileError(message) from exc

        self.additional_headers.append(
            (
                "Last-modified",
                _last_modified_header(filepath),
            )
        )

        name = os.path.split(filepath)[1]
        metadata = _load_metadata(filepath, metadata_path)
        try:
            self.dataset = dataframe_to_dataset(
                dataframe,
                name=name,
                sequence_name=sequence_name,
                metadata=metadata,
            )
        except (TypeError, ValueError) as exc:
            message = "Unable to open file {filepath}: {exc}".format(
                filepath=filepath, exc=exc
            )
            raise OpenFileError(message) from exc


class SequenceData(IterData):
    """IterData adapter backed by a pandas DataFrame."""

    def __init__(
        self,
        dataframe,
        template,
        dtypes,
        ifilter=None,
        imap=None,
        islice=None,
        level=0,
    ):
        self.dataframe = dataframe
        self.template = template
        self.dtypes = dtypes
        self.level = level

        self.ifilter = ifilter or []
        self.imap = imap or []
        self.islice = islice or []
        self._isna = _load_pandas().isna

    @property
    def stream(self):
        """Yield normalized rows from the DataFrame."""
        for row in self.dataframe.itertuples(index=False, name=None):
            yield tuple(_normalize_value(value, self._isna) for value in row)

    @property
    def dtype(self):
        """Return the numpy dtype exposed to pydap."""
        if isinstance(self.template, SequenceType):
            return np.dtype(
                [(name, self.dtypes[name]) for name in self.template.keys()]
            )
        return self.dtypes[self.template.name]

    def __len__(self):
        return len(self.dataframe)

    def __copy__(self):
        """Return a lightweight copy."""
        return self.__class__(
            self.dataframe,
            copy.copy(self.template),
            self.dtypes,
            self.ifilter[:],
            self.imap[:],
            self.islice[:],
            self.level,
        )


def dataframe_to_dataset(
    dataframe,
    name="pandas",
    sequence_name="sequence",
    metadata=None,
):
    """Build a dataset containing one sequence from a pandas DataFrame."""
    dataframe = _normalize_dataframe(dataframe)
    dtypes = {
        column: pandas_dtype_to_numpy(dataframe[column].dtype, dataframe[column])
        for column in dataframe.columns
    }

    dataset = DatasetType(name)
    sequence = dataset[sequence_name] = SequenceType(sequence_name)
    for column in dataframe.columns:
        sequence[column] = BaseType(column, dtype=dtypes[column])

    sequence.data = SequenceData(dataframe, copy.copy(sequence), dtypes)
    if metadata:
        _apply_metadata(dataset, sequence, metadata)
    return dataset


def read_dataframe(filepath, reader=None, read_kwargs=None):
    """Read a tabular file into a pandas DataFrame."""
    pd = _load_pandas()
    reader_function, default_kwargs = _resolve_reader(pd, filepath, reader)
    kwargs = default_kwargs.copy()
    kwargs.update(read_kwargs or {})

    result = reader_function(filepath, **kwargs)
    return _coerce_dataframe(result, pd)


def pandas_dtype_to_numpy(dtype, series=None):
    """Map a pandas dtype to a numpy dtype compatible with DAP4 output."""
    pd = _load_pandas()
    pandas_types = pd.api.types

    if pandas_types.is_object_dtype(dtype):
        return _object_dtype_to_numpy(series)
    if pandas_types.is_string_dtype(dtype) or isinstance(dtype, pd.CategoricalDtype):
        return np.dtype("U")
    if pandas_types.is_bool_dtype(dtype):
        return _numpy_dtype(dtype, default="bool")
    if pandas_types.is_unsigned_integer_dtype(dtype):
        return _numpy_dtype(dtype, default="uint64")
    if pandas_types.is_integer_dtype(dtype):
        return _numpy_dtype(dtype, default="int64")
    if pandas_types.is_float_dtype(dtype):
        return _numpy_dtype(dtype, default="float64")

    raise TypeError("Unsupported pandas dtype: {dtype}".format(dtype=dtype))


def _load_pandas():
    try:
        import pandas as pd
    except ImportError as exc:
        message = (
            "SequenceHandler requires pandas. Install it with "
            '"pip install pydap[server]".'
        )
        raise OpenFileError(message) from exc
    return pd


def _last_modified_header(filepath):
    modified = datetime.fromtimestamp(os.stat(filepath)[ST_MTIME], tz=timezone.utc)
    return modified.strftime("%a, %d %b %Y %H:%M:%S GMT")


def _resolve_reader(pd, filepath, reader):
    if callable(reader):
        return reader, {}

    if reader is not None:
        reader_name = (
            reader if reader.startswith("read_") else "read_{0}".format(reader)
        )
    else:
        reader_name, default_kwargs = _reader_spec_for_path(filepath)
        return getattr(pd, reader_name), default_kwargs

    try:
        return getattr(pd, reader_name), {}
    except AttributeError as exc:
        message = "pandas does not provide reader {reader!r}".format(reader=reader_name)
        raise ValueError(message) from exc


def _reader_spec_for_path(filepath):
    extension = _data_extension(filepath)
    try:
        return _PANDAS_READERS[extension]
    except KeyError as exc:
        message = (
            "No pandas reader is configured for extension {extension!r}. "
            "Pass reader= to SequenceHandler for other pandas-compatible formats."
        ).format(extension=extension)
        raise ValueError(message) from exc


def _data_extension(filepath):
    suffixes = [suffix.lower() for suffix in Path(filepath).suffixes]
    while suffixes and suffixes[-1] in _COMPRESSION_EXTENSIONS:
        suffixes.pop()
    return suffixes[-1] if suffixes else ""


def _coerce_dataframe(result, pd):
    if isinstance(result, pd.DataFrame):
        return result

    if isinstance(result, Mapping):
        frames = list(result.values())
    elif isinstance(result, (list, tuple)):
        frames = list(result)
    else:
        raise TypeError(
            "pandas reader returned {type}, not a DataFrame".format(
                type=type(result).__name__
            )
        )

    if not frames:
        raise ValueError("pandas reader returned no tabular data")
    if len(frames) > 1:
        raise ValueError(
            "pandas reader returned multiple tables; pass reader= or read_kwargs "
            "that select one table"
        )
    if not isinstance(frames[0], pd.DataFrame):
        raise TypeError(
            "pandas reader returned {type}, not a DataFrame".format(
                type=type(frames[0]).__name__
            )
        )
    return frames[0]


def _load_metadata(filepath, metadata_path):
    metadata_path = metadata_path or "{0}.json".format(filepath)
    if not os.path.exists(metadata_path):
        return None

    try:
        with open(metadata_path) as fp:
            return json.load(fp)
    except Exception as exc:
        message = "Unable to open metadata file {filepath}: {exc}".format(
            filepath=metadata_path, exc=exc
        )
        raise OpenFileError(message) from exc


def _normalize_dataframe(dataframe):
    dataframe = dataframe.copy(deep=False)
    columns = [str(column) for column in dataframe.columns]
    if len(columns) != len(set(columns)):
        raise ValueError("DataFrame columns must be unique after string conversion")
    if any(not column for column in columns):
        raise ValueError("DataFrame columns must not be empty")
    dataframe.columns = columns
    return dataframe


def _numpy_dtype(dtype, default):
    numpy_dtype = getattr(dtype, "numpy_dtype", None)
    if numpy_dtype is not None:
        return np.dtype(numpy_dtype)
    try:
        return np.dtype(dtype)
    except TypeError:
        return np.dtype(default)


def _object_dtype_to_numpy(series):
    if series is None:
        return np.dtype("U")

    non_null = series.dropna()
    if non_null.empty:
        return np.dtype("U")
    if non_null.map(lambda value: isinstance(value, (str, bytes))).all():
        return np.dtype("U")

    raise TypeError(
        "Object columns must contain string values or use a concrete numeric dtype"
    )


def _normalize_value(value, isna):
    try:
        if isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, np.generic):
        return value.item()
    return value


def _apply_metadata(dataset, sequence, metadata):
    if not isinstance(metadata, Mapping):
        raise TypeError("Pandas sidecar metadata must be a JSON object")

    if not _METADATA_KEYS.intersection(metadata):
        dataset.attributes.update(metadata)
        return

    dataset_attrs = _metadata_mapping(metadata, "dataset")
    sequence_attrs = _metadata_mapping(metadata, "sequence")
    column_attrs = _metadata_mapping(metadata, "columns")

    dataset.attributes.update(dataset_attrs)
    sequence.attributes.update(sequence_attrs)
    for column, attributes in column_attrs.items():
        if column not in sequence:
            raise ValueError(
                "Metadata references unknown column: {column}".format(column=column)
            )
        if not isinstance(attributes, Mapping):
            raise TypeError(
                "Metadata for column {column} must be an object".format(column=column)
            )
        sequence[column].attributes.update(attributes)


def _metadata_mapping(metadata, key):
    value = metadata.get(key, {})
    if not isinstance(value, Mapping):
        raise TypeError("Metadata field {key} must be an object".format(key=key))
    return value
