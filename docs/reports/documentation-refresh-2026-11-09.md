# Documentation refresh — 2026-11-09

By Jason Stys.

This documentation-only edition describes source `f83161e7ce500027fe5313bb08e36e9716a94be2`. It does not change application behavior, accounts, private data, installers or published releases.

## Published editions and completed review

| File                                     | Bytes | SHA-256                                                            | Reviewed scope                    |
| ---------------------------------------- | ----: | ------------------------------------------------------------------ | --------------------------------- |
| [project-guide.docx](project-guide.docx) | 47037 | `cef3f31c966914fd054e7b15acce1b11d504a98b116c2a9ae850e8f94d37f58c` | 7 pages, each viewed individually |

Word review checked plain black titles, readable pagination, whole table rows, source references, practical limits and absence of clipping or overflow. Render receipts were matched to the current DOCX digest before approval. Workbook review inspected both tab previews and actual exported Table/autoFilter elements; recalculated success/failure summaries were compared independently with workflow metadata. Static previews do not draw Excel dropdown arrows; the exported workbook contains the actual filters.

## Evidence and change boundary

- Functional baseline: `f83161e7ce500027fe5313bb08e36e9716a94be2`.
- Workflow observation: `2026-11-10T05:25:40.628667+00:00`; exact run URLs and source identities remain in [publications.json](publications.json).
- Local document-package validation verifies exact copied bytes, Office ZIP integrity, approved page/tab identities and internal documentation links. Repository-specific documentation and source-policy commands are run separately and recorded in the integration handoff.
- Source/index metadata is regenerated using the repository’s existing tools. Existing privacy, security, coverage and workflow gates are retained.
- PR and later main workflows must pass independently. This record does not claim future or unrun integration CI success.

## Interpretation

The Word files document the cited source; dated source reports retain their original execution scope. A passing workflow is distinct from completed analysis with zero findings, and neither establishes production suitability. The Excel source inventory is not a per-test execution report. Checksums identify exact bytes, not a signature or publisher attestation.

Use the [handbook](../handbook.md) to choose usage, design, security and test documentation. Keep editable Markdown and reviewed editions together; do not replace historical measurements with undated claims.

## Integration-local validation

Observed at 2026-11-10T08:06:47.464563+00:00. Exact Office bytes, package integrity, current rendered-page approvals, source/workflow identities and handbook links passed independent validation. The following repository-specific checks passed; later PR and main workflows remain separate requirements.

- `node scripts/generate-code-index.mjs --check` — exit 0.
- `node scripts/validate-repository.mjs` — exit 0.
- `node <repo>\web\node_modules\prettier\bin\prettier.cjs --write README.md docs/handbook.md docs/reports/publications.json docs/reports/documentation-refresh-2026-11-09.md` — exit 0.
- `node <repo>\web\node_modules\prettier\bin\prettier.cjs --check README.md docs/handbook.md docs/reports/publications.json docs/reports/documentation-refresh-2026-11-09.md` — exit 0.
- `C:\Users\jason\AppData\Local\Programs\Python\Python314\python.exe C:\Users\jason\Documents\Codex\2026-09-16\i\work\codeql-docs-20261109\validate_root_publications.py player-telemetry-analytics-platform` — exit 0.
