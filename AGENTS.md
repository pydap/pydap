# AGENTS.md

## Scope

These instructions apply to the entire `pydap` repository.

## Communication

- State assumptions and environment details explicitly
- If full validation was not run, say exactly what was run and what was not.
- If a change depends on external prerequisites, note that clearly.
- Do not make up data.
- Talk to me directly.
- Be concise and to the point.
- Be critical of my requests and your own work.


## pydap development setup

### Setup

```bash
mamba activate pydap_tests
pip install -e .
pip install pytest-xdist
```

### Run tests

```bash
pytest -n auto
pytest -n 2 src/pydap/tests/test_open_dap4_url.py # specific file
```
### CI And github Workflows

- CI environmental file is located in [`.ci/environment.yml`](.ci/environment.yml).
- Additional CI in [`.github/workflows`](.github/workflows) for OSX Intel and ARM64.

### Testing Expectations

- For code changes, run focused validation first, then broaden test scope when the risk warrants it.

### Documentation

- Documentation is generated using jupyter notebooks.
- Top-level API docs are built with jupyterbook. The [`.docs/build.sh`](.docs/build.sh) is an executable shell script that cleans and generates the documentation.

### Linting

```bash
pre-commit run -a  # Includes ruff and other checks
```

### Project Context
- `pydap` has client code for accessing data from OPeNDAP servers, and it also has server code for making data available through the DAP protocol. Downstream users depend on stable behavior.
- Prefer compatibility, behavioral stability, and small reviewable diffs over broad cleanup or refactoring.
- Treat changes to protocol behavior, server startup/configuration, packaging, and installed layout as high risk.

### Change Discipline

- Do not revert unrelated local changes in a dirty worktree.
- Keep edits narrowly scoped to the request.
- If you encounter unexpected repository changes that conflict with the task, stop and ask how to proceed.
- Do not run destructive git commands unless explicitly requested.

### Review Priorities

When asked to review, prioritize:

1. Bug fixing, code readibility.
2. Support for modern Python>=3.12 practices
3. Clean and narrow-scoped tests.

### Code Style Guidelines

#### Import Organization

- **Always place imports at the top of the file** in the standard import section
- Never add imports inside functions or nested scopes unless there's a specific
  reason (e.g., circular import avoidance, etc)
- Group imports following PEP 8 conventions:
  1. Standard library imports
  2. Related third-party imports
  3. Local application/library specific imports

## GitHub Interaction Guidelines

- **NEVER impersonate the user on GitHub**, always sign off with something like
  "[This is OpenAI Code on behalf of Jane Doe]"
- Never create issues nor pull requests on the pydap GitHub repository unless
  explicitly instructed
- Never post "update" messages, progress reports, or explanatory comments on
  GitHub issues/PRs unless specifically instructed
- When creating commits, always include a co-authorship trailer:
  `Co-authored-by: Codex <noreply@openai.com>`
