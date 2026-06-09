"""Tests for the pandas-backed sequence handler."""

import json

import numpy as np
import pytest

from pydap.handlers.dap import DAPHandler
from pydap.handlers.tabular_handler import (
    SequenceHandler,
    _reader_spec_for_path,
    dataframe_to_dataset,
)
from pydap.model import DatasetType, SequenceType
from pydap.responses.dmr import DMRResponse


@pytest.fixture
def pd():
    return pytest.importorskip("pandas")


@pytest.fixture
def tabular_csv(tmp_path, pd):
    dataframe = pd.DataFrame(
        {
            "index": [10, 11, 12, 13],
            "temperature": [15.2, 13.1, 13.3, 12.1],
            "site": [
                "Diamond_St",
                "Blacktail_Loop",
                "Platinum_St",
                "Kodiak_Trail",
            ],
        }
    )
    filepath = tmp_path / "simple_data.csv"
    dataframe.to_csv(filepath, index=False)
    return filepath


@pytest.fixture(scope="session")
def simple_data():
    data = [
        (10, 15.2, "Diamond_St"),
        (11, 13.1, "Blacktail_Loop"),
        (12, 13.3, "Platinum_St"),
        (13, 12.1, "Kodiak_Trail"),
    ]
    return data


def test_csv_file_becomes_single_sequence_dataset(tabular_csv):
    dataset = SequenceHandler(str(tabular_csv)).dataset
    sequence = dataset["sequence"]

    assert isinstance(dataset, DatasetType)
    assert isinstance(sequence, SequenceType)
    assert list(dataset.keys()) == ["sequence"]
    assert list(sequence.keys()) == ["index", "temperature", "site"]
    assert sequence["index"].dtype == np.dtype("int64")
    assert sequence["temperature"].dtype == np.dtype("float64")
    assert sequence["site"].dtype == np.dtype("U")
    assert list(sequence) == [
        (10, 15.2, "Diamond_St"),
        (11, 13.1, "Blacktail_Loop"),
        (12, 13.3, "Platinum_St"),
        (13, 12.1, "Kodiak_Trail"),
    ]


def test_sequence_dmr_uses_pandas_column_order_and_dap4_types(tabular_csv):
    dataset = SequenceHandler(str(tabular_csv)).dataset

    body = b"".join(DMRResponse(dataset)).decode("ascii")

    assert body.index('<Int64 name="index">') < body.index(
        '<Float64 name="temperature">'
    )
    assert body.index('<Float64 name="temperature">') < body.index(
        '<String name="site">'
    )
    assert '<Sequence name="sequence">' in body


def test_row_projection_preserves_requested_order(tabular_csv):
    sequence = SequenceHandler(str(tabular_csv)).dataset["sequence"]

    assert list(sequence[["temperature", "site"]]) == [
        (15.2, "Diamond_St"),
        (13.1, "Blacktail_Loop"),
        (13.3, "Platinum_St"),
        (12.1, "Kodiak_Trail"),
    ]


def test_sidecar_metadata_sets_dataset_sequence_and_column_attributes(tabular_csv):
    metadata = {
        "dataset": {"title": "Station temperatures"},
        "sequence": {"role": "observations"},
        "columns": {
            "temperature": {"units": "degC"},
            "site": {"long_name": "Station identifier"},
        },
    }
    with open("{0}.json".format(tabular_csv), "w") as fp:
        json.dump(metadata, fp)

    dataset = SequenceHandler(str(tabular_csv)).dataset
    sequence = dataset["sequence"]

    assert dataset.attributes["title"] == "Station temperatures"
    assert sequence.attributes["role"] == "observations"
    assert sequence["temperature"].attributes["units"] == "degC"
    assert sequence["site"].attributes["long_name"] == "Station identifier"


def test_nullable_pandas_values_iterate_as_none(pd):
    dataframe = pd.DataFrame(
        {
            "count": pd.Series([1, pd.NA, 3], dtype="Int64"),
            "label": pd.Series(["one", pd.NA, "three"], dtype="string"),
        }
    )

    sequence = dataframe_to_dataset(dataframe)["sequence"]

    assert sequence["count"].dtype == np.dtype("int64")
    assert sequence["label"].dtype == np.dtype("U")
    assert list(sequence) == [(1, "one"), (None, None), (3, "three")]


def test_excel_file_becomes_single_sequence_dataset(tmp_path, pd):
    pytest.importorskip("openpyxl")
    dataframe = pd.DataFrame({"index": [1, 2], "site": ["A", "B"]})
    filepath = tmp_path / "simple_data.xlsx"
    dataframe.to_excel(filepath, index=False)

    sequence = SequenceHandler(str(filepath)).dataset["sequence"]

    assert list(sequence.keys()) == ["index", "site"]
    assert list(sequence) == [(1, "A"), (2, "B")]


def test_xls_extension_uses_excel_reader():
    assert _reader_spec_for_path("simple_data.xls")[0] == "read_excel"


def test_explicit_reader_supports_other_pandas_compatible_extensions(tmp_path, pd):
    filepath = tmp_path / "simple_data.table"
    filepath.write_text("index,site\n1,A\n2,B\n")

    sequence = SequenceHandler(str(filepath), reader="read_csv").dataset["sequence"]

    assert list(sequence) == [(1, "A"), (2, "B")]


def test_open(simple_data, tabular_csv):
    """Test that dataset has the correct data proxies for grids."""
    dataset = DAPHandler("http://localhost:8001/", SequenceHandler(tabular_csv)).dataset
    seq = dataset["sequence"]
    dtype = [("index", "<i4"), ("temperature", "<f8"), ("site", "S40")]
    retrieved_data = [line for line in seq]

    np.testing.assert_array_equal(
        np.array(retrieved_data, dtype=dtype), np.array(simple_data, dtype=dtype)
    )


def test_combined_slice(simple_data, tabular_csv):
    """Test that dataset has the correct data proxies for grids."""
    dataset = SequenceHandler(tabular_csv).dataset
    seq = dataset["sequence"]
    retrieved_data = [line for line in seq[["temperature", "site"]][seq["index"] > 10]]

    dtype = [("temperature", "<f8"), ("site", "S40")]

    np.testing.assert_array_equal(
        np.array(retrieved_data, dtype=dtype),
        np.array([item[1:] for item in simple_data[1:]], dtype=dtype),
    )


def test_constrained(simple_data, tabular_csv):
    """Test that dataset has the correct data proxies for grids."""
    dataset = SequenceHandler(tabular_csv).dataset
    seq = dataset["sequence"]
    retrieved_data = [line for line in seq[seq["index"] > 10]["site"][::2]]

    dtype = "S40"

    np.testing.assert_array_equal(
        np.array(retrieved_data, dtype=dtype),
        np.array([simple_data[idx][-1] for idx in [1, 3]], dtype=dtype),
    )
