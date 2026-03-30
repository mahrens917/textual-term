# textual-term: Claude Guide

Terminal emulator widget for Textual with DSR support. Code in `src/textual_term/`, tests in `tests/`.

> **Shared rules** (CI pipeline, code hygiene, test isolation, path portability, do/don't): see `~/projects/ci_shared/CLAUDE.md`.

## Quick Commands
- `make check` — runs full CI pipeline (format, lint, type-check, test).

## Dependencies
This repo has no cross-repo Python dependencies.

## CI Limit Overrides
This repo uses tighter limits than the shared defaults: classes ≤100 lines; modules ≤400; ≤15 public / 25 total methods; ≤5 instantiations in `__init__`/`__post_init__`.
