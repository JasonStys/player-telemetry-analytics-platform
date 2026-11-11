# Player Telemetry Analytics Platform handbook

By Jason Stys.

Review acquisition cohorts with receipt-time cutoffs, cross-platform later activity and mature versus censored D0/D1/D7 denominators.

Prevents late-arrival hindsight and immature cohorts from producing misleading retention comparisons.

## Read the documentation

| Edition                                          | Audience and contents                                                                       |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| [project-guide.docx](reports/project-guide.docx) | User and developer guide: purpose, current usage, design, boundaries and source references. |

The editable Markdown remains the maintenance source. The Word files are readable editions, and the workbook is an evidence index rather than a test runner. See [publication identities and review](reports/publications.json) and the [documentation refresh record](reports/documentation-refresh-2026-11-09.md).

## Current usage and help

[README quick start](../README.md) is the entry point. Use the project-specific guides below before changing inputs, operating modes or deployment assumptions.

### Usage and operations

- [native analyst application](native-application.md)
- [native application validation](reports/native-application-2026-11-10.md)

- [cohort review](cohort-review.md)
- [operations](operations.md)

### Design and contracts

- [adr/0001 sql first modular analytics](adr/0001-sql-first-modular-analytics.md)
- [api](api.md)
- [architecture](architecture.md)
- [complexity](complexity.md)
- [data contract](data-contract.md)
- [research](research.md)

### Security and validation

- [security privacy](security-privacy.md)
- [testing](testing.md)

## Historical results and reproduction

The reviewed source is [`f83161e7ce500027fe5313bb08e36e9716a94be2`](https://github.com/JasonStys/player-telemetry-analytics-platform/tree/f83161e7ce500027fe5313bb08e36e9716a94be2). The observed functional workflow baseline is `f83161e7ce500027fe5313bb08e36e9716a94be2`; those observations are recorded at `2026-11-10T05:25:40.628667+00:00`. They do not certify an unrun later revision.

- [Detailed recorded validation](reports/practical-workflows-20261109.md)
- [Current Actions](https://github.com/JasonStys/player-telemetry-analytics-platform/actions) records later integration checks separately.
- Preserve dated measurements and follow the existing testing guide to reproduce them; a test-source inventory alone does not establish execution.

## Practical boundaries

- Synthetic local controlled lab without authentication or support for real private player data.
- Cohort filters apply to the dedicated review; other existing warehouse panels remain global.
- A receipt watermark does not prove data completeness, statistical certainty or a historical database revision archive.

## Maintaining these editions

Update the editable usage/design/test documents first. Rebuild and visually review every Word page and workbook tab before replacing an edition; verify the exact binary digests and evidence source in publications.json. Keep account data, logs with secrets, installed-app state and private test stores out of documentation. Source and release assets retain their existing security and licensing boundaries.
