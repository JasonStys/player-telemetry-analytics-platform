# Security and privacy

## Assets and trust boundaries

Protected assets are metric integrity, source lineage, local database contents, and operator confidence.
Untrusted boundaries are NDJSON input, HTTP path/query values, dependency supply chain, browser content,
and container configuration.

## Threats and controls

| Threat | Control | Residual risk |
|---|---|---|
| Personal data enters analytics | Synthetic-only policy; recursive key/value screen; strict extra-field rejection | Pattern matching cannot identify every sensitive value |
| Identifier reversal | Keyed HMAC pseudonymization | Public demo key offers no secrecy; real deployments need managed secrets |
| Duplicate/replayed delivery | Event primary key; batch ID plus SHA-256 checksum; atomic transaction | Semantically duplicated events with new IDs require domain rules |
| SQL injection | Bound values; fixed SQL files; allowlisted export table names | `explain` accepts internal statements and must not be user exposed |
| Oversized output | Hard limits of 100/500 rows | No per-client rate limit in local demo |
| Browser injection | React escaping; no raw HTML; static CSP and framing/type headers | CSP allows inline styles for computed bar widths |
| Dependency compromise | Lockfiles, audits, Dependabot, CodeQL, SHA-pinned Actions | Registry and upstream trust remain |
| Privileged container escape | Non-root application processes; minimal images | Container runtime and base image still require patching |
| Unauthorized access | Local-only deployment guidance | Authentication is intentionally absent in version one |

## Privacy behavior

`find_privacy_violations` walks nested mappings and sequences. It flags sensitive names such as email,
phone, name, token, password, and API key, plus email-like, phone-like, and bearer-like string values.
Violation diagnostics record the field path, not the matched secret. The quarantined raw payload is still
sensitive by definition and would need restricted access and a retention limit in a real system.

## Safe deployment checklist

Before any non-local use:

1. Disable demo bootstrap.
2. Add authenticated identity and role-based authorization.
3. Put TLS and request-size/rate controls at the edge.
4. Replace the demo HMAC key with a rotated secret from a secret manager.
5. Encrypt storage, define retention/deletion, and restrict quarantine access.
6. Add centralized audit logs and alerts without raw payload leakage.
7. Pin container images by digest and scan the produced images.
8. Perform an environment-specific threat model and privacy review.

## Honest claims

Passing the included checks means the tested controls behaved as documented on the tested revision. It
does not establish compliance, anonymity, fraud detection, fairness, or production readiness.
