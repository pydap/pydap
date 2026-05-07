# Pydap Server Plan for DAP4 Tabular Sequences

This document areas of work for improving the pydap server so it can describe, read,
and eventually serve DAP4 tabular sequence data.
Each section can be worked on separately, with clear goals and expected
outcomes.

## Overall Goal

Improve pydap's server-side DAP4 support for tabular data by building on the
existing data model, adding a pandas-backed tabular handler, completing DMR
generation for sequences, and using the DAP4 client/deserializer work to learn
and validate the binary sequence format before adding a `.dap` response.

The initial target should be modest:

- Non-nested DAP4 sequences.
- One top-level sequence per tabular dataset.
- Scalar sequence fields.
- Numeric and string columns.
- No constraint expressions at first.
- No nested structures or nested sequences at first.

## Guiding Principles

- Preserve the existing pydap server architecture if possible. If a major rewrite
  is necessary, stated all the necessary changes that are needed and why.
- Keep DAP2 behavior stable while adding DAP4-specific capabilities.
- Prefer small, verifiable steps over a broad rewrite.
- Use Hyrax responses as reference fixtures when possible.
- Keep pandas as the tabular data abstraction, not as a protocol layer.
- Conform to the (`dap4 xml schema`)[https://github.com/OPENDAP/xml/blob/master/dap4/dap4.xsd]
  when generating `dmr`.
- Build serializer and deserializer behavior from the DAP4 specification and
  validate with real `.dmr` and `.dap` examples.


## 1. Improve DMR Generation

### Goal

Make DMR generation more complete, deterministic, and easier to extend before
adding any sequence support. Focus on what is there already.

### Why This Matters

The DMR is the metadata foundation for DAP4. If the DMR is inconsistent or
incomplete, both the client deserializer and server response work become harder
to validate. Improving DMR generation first gives all later work a stable target.

### Action Items

- Review the current DMR response implementation, issue 634, and the dap4 specification
  to understand the expected (`dap4 dmr declaration`)[https://opendap.github.io/dap4-specification/DAP4.html#_dmr_declarations].
- Identify gaps between current pydap DMR output and expected DAP4 DMR output
  according to the (`dap4 xml schema`)[https://github.com/OPENDAP/xml/blob/master/dap4/dap4.xsd]
- Replace ad hoc dtype name generation with an explicit DAP4 type map.
- Give preference to pydap's existing data model types in
  (`.src/pydap/model.py`)[.src/pydap/model.py] over all the possibly missing
  existing dap4 types in the schema.
- Make XML output deterministic for attributes, dimensions, groups, and arrays.
- Ensure XML escaping is handled correctly for names and attribute values.
- Add small DMR fixtures for simple arrays and grouped datasets.
- Compare generated pydap DMR output with known Hyrax DMR examples.

### Expected Outcome

Pydap should generate cleaner DMR output for existing array and group datasets,
without changing DAP2 behavior.

### Independent Validation

- Existing DMR tests still pass. If not, identify why. Give preference to the
  conforming to DAP4 dmr schema and the dap4 specification over existing DMR
  files on pydap's testing suite.
- New DMR fixtures are stable.
- Generated XML can be parsed back into a pydap dataset correctly, following
  the expected order of declaration. For example, see (`dap4 spec`)[https://opendap.github.io/dap4-specification/DAP4.html#_groups]. This may fail at first Identify why, and,
  if necessary, specify dmrVersion=2 in pydap's dmr parser.

## 2. Add a Pandas-Based Tabular Handler

### Goal

Create a generic tabular handler that uses pandas to expose tabular files as
pydap sequences.

### Why This Matters

The current CSV handler already maps CSV data into a pydap `SequenceType`, but
it is specific to CSV. A pandas-backed handler can provide a broader, more
consistent tabular path for CSV and, later, other formats.

### Action Items

- Add a new pandas sequence handler rather than replacing the existing handlers
  immediately.
- Start with CSV input because it is easy to inspect and already has a pydap
  comparison point.
- Represent the tabular dataset as one `DatasetType` containing one
  `SequenceType`.
- Map DataFrame columns to sequence child variables.
- Define a clear pandas-to-DAP4 dtype mapping.
- Decide how to handle pandas nullable values.
- Support optional sidecar metadata for dataset, sequence, and column
  attributes.
- Keep row iteration independent of the DAP4 serializer so the handler remains
  useful for other responses.

### Expected Outcome

A tabular file can be loaded through pandas and represented inside pydap as a
sequence dataset.

### Independent Validation

- A CSV file becomes a pydap dataset with one sequence.
- The sequence has predictable column names, dtypes, and attributes.
- Row iteration returns values in the same order as the DMR will describe them.

## 3. Support DMR Output for Sequences

### Goal

Generate valid DAP4 DMR metadata for non-nested `SequenceType` objects.

### Why This Matters

Sequence DMR support is needed before a DAP4 `.dap` response can be produced or
read reliably. The DMR tells the deserializer how to interpret the binary data.

### Action Items

- Implement correct DMR generation for `SequenceType`.
- Keep the first version focused on non-nested sequences.
- Ensure child variables are emitted in the same order used by row serialization.
- Add tests using synthetic sequence datasets from pydap's own test fixtures.
- Add tests using the new pandas-backed handler.
- Make unsupported nested sequences explicit in tests and documentation.

### Expected Outcome

Pydap can describe tabular sequence data in a DAP4 DMR.

### Independent Validation

- A synthetic `SequenceType` produces stable DMR XML.
- A pandas-backed dataset produces stable sequence DMR XML.
- The DMR parser can read the generated sequence DMR back into the expected
  pydap model.

## 4. Work on the DAP4 Sequence Deserializer

### Goal

Teach the pydap client to deserialize non-nested DAP4 sequence data.

### Why This Matters

Deserializer work builds familiarity with the DAP4 binary sequence format before
pydap attempts to serve that format. This also allows pydap to compare sequence
data received from Hyrax with sequence data eventually served by pydap itself.

### Action Items

- Collect small Hyrax `.dmr` and `.dap` fixtures containing non-nested
  sequences.
- Start with numeric-only sequence fields.
- Add string fields once numeric rows work.
- Decode the DAP4 sequence row count.
- Decode each row as a structure whose fields follow DMR order.
- Represent decoded data in a way that works naturally with pydap
  `SequenceType`.
- Add clear errors for nested sequences or unsupported field shapes.

### Expected Outcome

Pydap can read a simple DAP4 sequence response from Hyrax.

### Independent Validation

- A known Hyrax sequence fixture deserializes into the expected rows.
- Numeric and string fields round trip into predictable Python or numpy values.
- Unsupported nested data fails with a clear error instead of silent corruption.

## 5. Add a DAP4 `.dap` Response for Sequences

### Goal

Create the first pydap server response that serves a non-nested sequence using
the DAP4 binary response format.

### Why This Matters

Once pydap can deserialize DAP4 sequences, it can use its own client to validate
its own server output. This creates a tight feedback loop for server
development.

### Action Items

- Add a `.dap` response class for DAP4 data.
- Register the response without disturbing existing `.dods` DAP2 behavior.
- Start with full dataset responses only.
- Do not implement constraint expressions in the first version.
- Emit a DMR chunk followed by binary data chunks.
- Serialize one top-level, non-nested sequence.
- Keep row field order identical to the DMR field order.
- Add checksum handling only after the basic response is stable.

### Expected Outcome

Pydap can serve a simple pandas-backed sequence as a DAP4 `.dap` response.

### Independent Validation

- The pydap client can open the pydap-served `.dap` response.
- The rows match the original pandas-backed data.
- The same logical sequence can be compared between Hyrax and pydap responses.

## 6. Compare Hyrax and Pydap Sequence Behavior

### Goal

Use Hyrax as an external reference to validate pydap's DAP4 sequence behavior.

### Why This Matters

DAP4 sequence support should not only work internally. It should match the
behavior of established DAP4 servers closely enough that pydap clients and
other clients can rely on it.

### Action Items

- Keep a small set of reference Hyrax sequence fixtures.
- Compare DMR structure, field order, dtypes, and attributes.
- Compare deserialized row values.
- Compare string encoding behavior.
- Compare chunking assumptions.
- Document any intentional differences.

### Expected Outcome

Pydap has a practical compatibility baseline for DAP4 sequences.

### Independent Validation

- Fixture-based tests explain what is being compared.
- Differences from Hyrax are visible and documented.
- The pydap client can deserialize both Hyrax and pydap sequence responses.

## 7. Add Constraint Expression Support Later

### Goal

Add projection, slicing, and filtering only after full sequence responses work.

### Why This Matters

Constraint expressions add complexity to parsing, pandas filtering, DMR
subsetting, and binary serialization. They should be layered on after the
unconstrained path is correct.

### Action Items

- Start with column projection.
- Add row slicing.
- Add simple comparisons for filters.
- Avoid passing raw user expressions into pandas query APIs.
- Make filtered row counts correct before serializing binary data.
- Add tests for empty results, one-row results, and string filters.

### Expected Outcome

Pydap can serve constrained DAP4 sequence responses for common tabular access
patterns.

### Independent Validation

- Projection changes both DMR and binary payload consistently.
- Filters produce correct row counts and row values.
- Invalid expressions return useful errors.

## 8. Keep Initial Scope Explicit

### In Scope First

- CSV-backed pandas handler.
- Non-nested sequences.
- Scalar sequence fields.
- Numeric and string fields.
- DMR generation for sequences.
- DAP4 sequence deserialization.
- Full `.dap` sequence response without constraint expressions.

### Out of Scope First

- Nested sequences.
- Nested structures inside sequences.
- Arrays as sequence fields.
- Server-side DAP4 constraint expressions.
- Advanced streaming optimizations.
- Full FastAPI migration.
- Replacing the existing NetCDF array handler.

## Suggested Work Order

These items are intentionally separable, but the smoothest path is:

1. Improve general DMR generation.
2. Add pandas-backed sequence datasets.
3. Add DMR output for sequences.
4. Add DAP4 sequence deserialization from Hyrax fixtures.
5. Add the first pydap DAP4 `.dap` sequence response.
6. Compare Hyrax and pydap behavior.
7. Add constraint expression support.

## Practical Notes

- The pandas handler can be developed and tested without DAP4 serialization.
- Sequence DMR support can be developed with synthetic datasets before the
  pandas handler is complete.
- The DAP4 sequence deserializer can be developed entirely from Hyrax fixtures.
- The `.dap` sequence response should wait until the deserializer is good enough
  to validate pydap's own server output.
- Constraint expressions should wait until the unconstrained response is stable.
