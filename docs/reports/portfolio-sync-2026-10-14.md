# Portfolio synchronization — 2026-10-14

Created by Jason Stys.

This candidate combines the reviewed proposals below while preserving their
commit ancestry and the existing main-branch security fixes. Conflicting
version declarations are combined explicitly; affected locks are regenerated
from the reviewed manifests. No audit or coverage budget is lowered.

- [Original proposal #13](https://github.com/JasonStys/player-telemetry-analytics-platform/pull/13).
- [Original proposal #16](https://github.com/JasonStys/player-telemetry-analytics-platform/pull/16).
- [Original proposal #17](https://github.com/JasonStys/player-telemetry-analytics-platform/pull/17).
- [Original proposal #21](https://github.com/JasonStys/player-telemetry-analytics-platform/pull/21).
- [Original proposal #22](https://github.com/JasonStys/player-telemetry-analytics-platform/pull/22).
- [Original proposal #23](https://github.com/JasonStys/player-telemetry-analytics-platform/pull/23).
- [Original proposal #24](https://github.com/JasonStys/player-telemetry-analytics-platform/pull/24).
- [Original proposal #26](https://github.com/JasonStys/player-telemetry-analytics-platform/pull/26).
- [Original proposal #27](https://github.com/JasonStys/player-telemetry-analytics-platform/pull/27).
- [Original proposal #28](https://github.com/JasonStys/player-telemetry-analytics-platform/pull/28).
- [Original proposal #29](https://github.com/JasonStys/player-telemetry-analytics-platform/pull/29).
- [Original proposal #30](https://github.com/JasonStys/player-telemetry-analytics-platform/pull/30).
- [Original proposal #31](https://github.com/JasonStys/player-telemetry-analytics-platform/pull/31).

Coordinated CodeQL steps use the same reviewed immutable release where present.
Source and generated-symbol contracts remain enforced by the existing workflows.
The complete candidate must pass its applicable native CI before promotion.
[Inspect candidate checks](https://github.com/JasonStys/player-telemetry-analytics-platform/actions?query=branch%3Amaintenance%2Fportfolio-sync-20261014).

This maintenance does not add production deployments, user-data access, automatic
source promotion or new guarantees of security. Existing release tags and assets
are retained. Platform and model-quality limitations remain in the project README.

Python image proposal #20 is not included: its 3.15 release-candidate
runtime fails this package's declared `>=3.12,<3.15` support contract. Supporting
that runtime requires a separate dependency-wheel and runtime-port validation.
