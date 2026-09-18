# Security policy

## Supported version

Security fixes are applied to the latest commit on `main`. This portfolio project is not an operated
production service and does not provide a production-security guarantee.

## Reporting

Do not open a public issue containing credentials, personal data, or an exploitable proof of concept.
Use GitHub's private vulnerability reporting feature for the repository. Include the affected component,
impact, reproduction conditions, and a minimally sensitive example.

## Data policy

Only deterministic synthetic data belongs in this repository. The ingestion layer screens common
personal/secret-bearing keys and values, but that control is defense in depth—not permission to submit
real data. Generated identifiers are keyed pseudonyms and are not encryption.

## Deployment boundary

The included local demo has no authentication and must not be exposed to an untrusted network. A real
deployment must add an identity provider, authorization, TLS termination, secret management, retention
controls, centralized audit logging, and infrastructure-specific hardening.
