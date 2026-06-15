# Plan: DAP4 Sequence Deserialization (`SequenceProxyDap4`)

**Created:** 2026-06-15  
**Author:** Miguel Jimenez-Urias  
**Branch:** `seq_decoder`  
**Target file:** `src/pydap/handlers/dap.py`  
**Reference data:** `src/pydap/tests/data/daps/gsodock.dat.dap`

---

## Part A: How `SequenceProxy` (DAP2) Works

`SequenceProxy` lives at [src/pydap/handlers/dap.py:617](../src/pydap/handlers/dap.py#L617) and acts as a lazy proxy for tabular (Sequence) data from a DAP2 `.dods` endpoint. It mimics a NumPy structured array but fetches data on demand.

### Construction

```python
SequenceProxy(baseurl, template, selection=None, slice_=None, ...)
```

- `baseurl`: base URL of the remote dataset (without `.dods` suffix)
- `template`: a `SequenceType` object describing the columns (names, dtypes, shapes)
- `selection`: list of constraint strings (`["var>1.0", "var<5.0"]`)
- `slice_`: row slicing tuple, e.g. `(slice(0, 10),)`

### URL Assembly (`url` property)

Appends `.dods` to the path and encodes the constraint expression:

```
http://server/path/to/data.nc.dods?sequence[0:10]&field>1.0
```

### Subsetting (`__getitem__`)

Returns a lightweight `copy.copy()` of self with modified state:

| Key type             | Effect                                          |
|----------------------|-------------------------------------------------|
| `str`                | Selects a child variable (single column)        |
| `list[str]`          | Selects multiple columns; sets `sub_children=True` |
| `ConstraintExpression` | Appends a filter string to `selection`        |
| `int` or `slice`     | Combines with existing `self.slice` via `combine_slices` |

### Data Fetching (`__iter__`)

Called when Python iterates over the proxy:

1. **HTTP GET** to `self.url` via `pydap.net.GET`
2. **Skip DDS header**: scans the byte stream for the `b"Data:\n"` pattern using `find_pattern_in_string_iter`; everything before is the ASCII Data Descriptor Structure (DDS)
3. **Wrap the remainder** in a `StreamReader` (reads from byte chunks lazily)
4. **Delegate to `unpack_sequence(stream, self.template)`**, which yields one row at a time

### `unpack_sequence` (DAP2 binary format)

Located at [src/pydap/handlers/dap.py:780](../src/pydap/handlers/dap.py#L780).

The DAP2 binary layout for Sequences is:

```
[START_OF_SEQUENCE 4 bytes] [row data] [START_OF_SEQUENCE] [row data] ... [END_OF_SEQUENCE 4 bytes]
```

- `START_OF_SEQUENCE = b"\x5a\x00\x00\x00"` — 4-byte marker before every row
- All scalar/array data in **big-endian XDR** format (converted via `DAP2_response_dtypemap`)
- Strings: 4-byte length prefix (big-endian uint32) + data + padding to 4-byte boundary
- Arrays: 4-byte count + 4-byte count (repeated) + data + padding
- Unsigned bytes: padded to 4-byte boundary

**Simple path** (all columns are fixed-size non-string scalars): reads one `numpy.dtype` record per row atomically.

**Complex path**: calls `unpack_children` recursively for nested `SequenceType` or `StructureType` children.

### Wiring into the client (`add_dap2_proxies`)

At [src/pydap/handlers/dap.py:351](../src/pydap/handlers/dap.py#L351):

```python
for var in walk(self.dataset, SequenceType):
    var.data = SequenceProxy(self.base_url, template, ...)
```

---

## Part B: DAP4 Sequence Binary Format

Empirically verified from `gsodock.dat.dap` (URI GSO-Dock dataset; 1 Float64 + 11 Float32 columns, 144 rows).

### The `.dap` Chunked Response

A DAP4 `.dap` response uses a **chunked binary encoding**. Every chunk is prefixed by a 4-byte big-endian header:

```
bits [31:24]  — chunk type flags (1 byte)
bits [23:0]   — chunk byte length (3 bytes)
```

Chunk type flags (3 bits, LSB-first on little-endian machines after bit reversal):

| Bit | Meaning              |
|-----|----------------------|
| 0   | `last_chunk` — no more data follows |
| 1   | `error` — this chunk carries an error message |
| 2   | `little_endian` — data is little-endian |

In `gsodock.dat.dap`, all chunks have type `0x04` → binary `00000100` → reversed `00100000` → `last=False, error=False, endian='<'` (little-endian). The final terminator chunk has type `0x05` (last=True, little-endian), length=0.

### Chunk layout of `gsodock.dat.dap`

| Offset | Type   | Length | Contents                     |
|--------|--------|--------|------------------------------|
| 0      | `0x04` | 3412   | DMR XML (metadata)           |
| 3416   | `0x04` | 4096   | Sequence binary data (part 1)|
| 7516   | `0x04` | 3400   | Sequence binary data (part 2)|
| 10920  | `0x05` | 0      | End-of-data terminator       |

Total file: 10924 bytes. Total data payload: 7496 bytes.

### Sequence Binary Layout (within concatenated data chunks)

```
[8 bytes: uint64 LE — number of rows N]
[N × row_bytes: row-major interleaved data, little-endian]
```

For `gsodock.dat.dap`:

- N = 144 rows
- Row = Float64 (8 bytes) + 11 × Float32 (4 bytes each) = **52 bytes/row**
- Total: 8 + 144 × 52 = **7496 bytes** ✓

Each field is encoded directly in its native numpy dtype in the machine's endianness (as declared by the chunk type flags) — **no XDR, no padding, no per-row markers**.

**No per-Sequence CRC32 checksum** is appended (confirmed: 0 extra bytes after the last row). This contrasts with normal DAP4 array variables which each have a 4-byte CRC32 appended after their data.

### Comparison: DAP2 vs DAP4 Sequence Encoding

| Property              | DAP2 (`.dods`)                     | DAP4 (`.dap`)                         |
|-----------------------|------------------------------------|---------------------------------------|
| Framing               | DDS text header + `Data:\n`        | Chunked binary (4-byte chunk headers) |
| Row marker            | `\x5a\x00\x00\x00` before each row | None                                   |
| Row count             | Implicit (iterate until END marker)| Explicit 8-byte uint64 LE prefix      |
| Byte order            | Big-endian XDR always              | Declared per-response (usually LE)    |
| String encoding       | 4-byte len + data + 4-byte padding | 8-byte LE uint64 len + UTF-8 data     |
| Unsigned byte padding | Padded to 4-byte boundary          | No padding                             |
| Checksum              | None                               | None for Sequences (CRC32 for arrays) |
| Constraint expression | `?sequence[0:10]&field>val`        | `?dap4.ce=/Sequence[0:10]`            |

---

## Part C: Implementation Plan for `SequenceProxyDap4`

### Goal

Create a `SequenceProxyDap4` class that:
- Mirrors the interface of `SequenceProxy` (lazy, iterable, supports column/row/filter subsetting)
- Fetches data from a `.dap` endpoint
- Deserializes the DAP4 chunked binary format for Sequences
- Is wired into `add_dap4_proxies` (replacing the current warning stub)

### Step 1: Add `unpack_sequence_dap4` helper function

**2026-06-15** — Design  
**Location:** near `unpack_sequence` (~line 780 in `dap.py`)

```python
def unpack_sequence_dap4(buffer, template, endian='<'):
    """Unpack a DAP4 sequence from a flat bytearray into rows."""
```

Logic:
1. Read first 8 bytes as `uint64` (little-endian) → `n_rows`
2. Build a list of `(name, numpy_dtype)` for each child of `template`
3. For each of the `n_rows` rows:
   - For each column, read `dtype.itemsize` bytes at current position
   - Interpret as `dtype.newbyteorder(endian)`
   - Handle strings: read 8-byte LE uint64 length, then UTF-8 bytes
4. Yield each row as a tuple (matching `unpack_sequence` output contract)

### Step 2: Add `stream2bytearray_for_sequence` or reuse `stream2bytearray`

**2026-06-15** — Design  
`stream2bytearray` already concatenates all non-DMR data chunks. However, for `SequenceProxyDap4` we need to stream the response from a remote server, not from a `BytesReader` wrapping a local file. Reuse `stream2bytearray` logic but applied to a `StreamReader`.

### Step 3: Create `SequenceProxyDap4` class

**2026-06-15** — Design  
**Location:** immediately after `SequenceProxy` (~line 778 in `dap.py`)

```python
class SequenceProxyDap4(object):
    """Lazy proxy for DAP4 Sequence variables.

    Mirrors SequenceProxy but fetches from .dap endpoints using
    the DAP4 chunked binary format.
    """
    shape = ()

    def __init__(self, baseurl, template, selection=None, slice_=None,
                 application=None, session=None, timeout=DEFAULT_TIMEOUT,
                 verify=True, checksums=True, get_kwargs=None):
        ...
```

Key attributes same as `SequenceProxy` plus `checksums` and `endian` (determined at fetch time from first chunk header).

#### `url` property

```
http://server/path/to/data.dap?dap4.ce=/SequenceName[0:N]
```

Differences from DAP2:
- Path suffix: `.dap` not `.dods`
- CE format: `dap4.ce=/SequenceName` (slash-prefixed absolute path)
- Filters use DAP4 CE syntax (TBD; currently not implemented in pydap)

#### `__iter__`

1. GET `self.url` with streaming
2. Read first 4 bytes → DMR chunk header → read and discard DMR (length bytes)
3. Call `stream2bytearray`-style logic to assemble subsequent data chunks
4. Parse endianness from first data-chunk header
5. Call `unpack_sequence_dap4(buffer, self.template, endian)`
6. Apply `self.slice` (row slicing) as a post-filter over the yielded iterator

#### `__getitem__` (same interface as `SequenceProxy`)

| Key type               | Effect                        |
|------------------------|-------------------------------|
| `str`                  | Select child column           |
| `list[str]`            | Select multiple columns       |
| `ConstraintExpression` | Append to `self.selection`    |
| `int` / `slice`        | Combine with `self.slice`     |

### Step 4: Wire into `add_dap4_proxies`

**2026-06-15** — Design  
Replace the current warning at [src/pydap/handlers/dap.py:316](../src/pydap/handlers/dap.py#L316):

```python
# Before (current):
for var in walk(self.dataset, SequenceType):
    warnings.warn(f"... Sequences in DAP4 are not fully supported ...")

# After:
for var in walk(self.dataset, SequenceType):
    template = copy.copy(var)
    var.data = SequenceProxyDap4(
        self.base_url,
        template,
        application=self.application,
        session=self.session,
        timeout=self.timeout,
        verify=self.verify,
        checksums=self.checksums,
        get_kwargs={**self.get_kwargs, "stream": True},
    )
```

### Step 5: Add `unpack_sequence_dap4` to handle the binary buffer

Full design for `unpack_sequence_dap4`:

```python
def unpack_sequence_dap4(buffer, template, endian='<'):
    cols = list(template.children()) or [template]
    offset = 8  # skip the 8-byte row count (already read by caller)
    n_rows = int.from_bytes(buffer[:8], 'little')

    for _ in range(n_rows):
        row = []
        for col in cols:
            dt = numpy.dtype(col.dtype).newbyteorder(endian)
            if dt.kind == 'S' or dt.kind == 'U':
                # 8-byte LE uint64 length prefix + UTF-8 bytes
                strlen = int.from_bytes(buffer[offset:offset+8], 'little')
                offset += 8
                val = buffer[offset:offset+strlen].decode('utf-8')
                offset += strlen
                row.append(val)
            else:
                val = numpy.frombuffer(buffer[offset:offset+dt.itemsize], dt)[0]
                offset += dt.itemsize
                row.append(val)
        yield tuple(row)
```

### Step 6: Tests

**2026-06-15** — Design  
Add to `src/pydap/tests/test_handlers_dap.py`:

1. **Unit test for `unpack_sequence_dap4`**: parse `gsodock.dat.dap` locally (from file), assert:
   - 144 rows returned
   - First row: `time≈35234.0`, `depth≈1.95`, `sea_temp≈17.62`
   - Last row values match expected

2. **Integration test for `SequenceProxyDap4.__iter__`**: mock or use a local WSGI app with DAP4 response

3. **Test `add_dap4_proxies` no longer warns** for Sequence variables once wired up

### Step 7: Edge cases to handle

- **String columns**: 8-byte LE uint64 length prefix (not 4-byte as in DAP2)
- **Nested sequences**: not yet supported in DAP4 per spec; raise `NotImplementedError`
- **Empty sequences**: N=0 → yield nothing
- **Multiple data chunks**: `stream2bytearray` already concatenates correctly
- **Big-endian servers**: use the endianness flag from the chunk type byte
- **Slicing**: apply `self.slice` as `itertools.islice` after row generation (or encode in the CE)

---

## Open Questions

1. **DAP4 CE for Sequences**: Does Hyrax support `dap4.ce=/Sequence[0:10]` for row slicing? The current DAP2 approach encodes slice in the hyperslab notation. Needs testing against a live server.
2. **Filter expressions**: DAP4 CE filters for sequences (e.g., `field>value`) use a different syntax than DAP2. Not yet implemented in pydap's CE parser.
3. **Checksum for Sequences**: The spec (Section 1.6.2) mentions CRC32 per top-level variable; the test file has none. Need to clarify whether servers include a checksum after the Sequence data blob.
4. **Column projection via CE**: Can Hyrax return a subset of columns when `dap4.ce=/Sequence.Time,/Sequence.Depth` is requested?

---

## Files to Change

| File | Change |
|------|--------|
| `src/pydap/handlers/dap.py` | Add `unpack_sequence_dap4()`, add `SequenceProxyDap4` class, update `add_dap4_proxies` |
| `src/pydap/tests/test_handlers_dap.py` | Add `TestSequenceProxyDap4` test class |

No new files needed; the test data file `gsodock.dat.dap` already exists.
