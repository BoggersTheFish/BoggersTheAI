# TS-Core consolidation record

## Source

- Repository: `BoggersTheFish/TS-Core`
- Source branch: `master`
- Source commit: `3ef48ad00efef8659ad0981d71de509a9827f584`
- Licence: MIT

## Imported surface

The domain-neutral typed tension kernel from the satellite's `ts_core/`
package was imported into:

`src/thinking_system/core/typed_tension/`

The corresponding focused test and generic demonstration were imported into:

- `tests/test_ts_core_typed_tension.py`
- `examples/typed_tension_kernel_demo.py`

## Adaptation

Internal package source was copied without architectural rewriting.

Test and demonstration imports were changed from:

`ts_core`

to:

`thinking_system.core.typed_tension`

## Deliberately not imported

The following TS-Core surfaces remain outside the monorepo pending separate
classification:

- legacy `src/python/` application and narrative layers
- TUI and Streamlit interfaces
- Grok/xAI integration
- Z3 toy alignment tooling
- training-data utilities
- Docker and Ollama configuration
- Rust/PyO3 acceleration
- Kernel Wave 12 and Daily Spin application modes
- legacy `tscore` and `tscore-daily` commands

These are not represented as consolidated by this import.

## Current status

**PARTIALLY_IMPORTED**

TS-Core must not be archived solely because of this import. Remaining unique
surfaces must be classified as importable, obsolete, historical, or independent
before an archival decision.
