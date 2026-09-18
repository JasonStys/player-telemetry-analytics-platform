# Contributing

Contributions should preserve the repository's central promise: a metric is publishable only when its
input contract, transformation, test evidence, and limitations are reviewable.

## Development workflow

1. Create a focused branch and describe the user or analyst outcome.
2. Update the event contract or metric catalog before changing semantics.
3. Add a failing test at the lowest useful layer.
4. Implement the smallest cohesive change.
5. Run `./scripts/verify.sh` and any affected PostgreSQL/browser checks.
6. Update the code index and measured reports when declarations or evidence change.

## Required quality

- No real identifiers, credentials, private data, or copied production payloads.
- Python is formatted and linted with Ruff and checked with strict mypy.
- TypeScript is formatted with Prettier, linted with ESLint, and compiled in strict mode.
- Business paths, edge cases, failures, data integrity, and security boundaries have tests.
- SQL changes include reconciliation or golden assertions and an updated metric definition.
- Source files contain `File:` and `Purpose:` headers; exact symbols and line locations are generated in
  `docs/code-index.md`.
- New dependencies require a documented reason and a clean production dependency audit.

## Commit guidance

Use imperative, outcome-oriented messages such as `Add idempotent batch conflict detection`. Keep
format-only changes separate from semantic changes when practical.
