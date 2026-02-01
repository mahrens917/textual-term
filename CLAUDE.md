# textual-term: Claude Guide

Terminal emulator widget for Textual with DSR support. Code in `src/textual_term/`, tests in `tests/`, CI config in `ci_shared.mk` + `shared-tool-config.toml`.

## Quick Commands
- `make check` — runs full CI pipeline (format, lint, type-check, test).

## Code Hygiene
- Avoid adding fallbacks, duplicate code, or backward-compatibility shims; call out and fix fail-fast gaps or dead code when encountered.
- Prefer config JSON files over new environment variables; only introduce ENV when necessary and document it.

## CI Pipeline (exact order)
- `codespell` -> `vulture` -> `deptry` -> `gitleaks` -> `bandit_wrapper` -> `safety scan` (skipped with `CI_AUTOMATION`) -> `ruff --fix` -> `pyright --warnings` -> `pylint` -> `pytest` -> `coverage_guard` -> `compileall`.
- Limits: classes <= 100 lines; functions <= 80; modules <= 400; cyclomatic <= 10 / cognitive <= 15; inheritance depth <= 2; <= 15 public / 25 total methods; <= 5 instantiations in `__init__`/`__post_init__`; `unused_module_guard --strict`; documentation guard requires README/CLAUDE/docs hierarchy.

## Do/Don't
- Do fix the code, never bypass checks (`# noqa`, `# pylint: disable`, `# type: ignore`, `policy_guard: allow-*`, threshold changes are off-limits).
- Do keep secrets and generated artifacts out of git.
- Do keep required docs current (`README.md`, `CLAUDE.md`, `docs/README.md`).
