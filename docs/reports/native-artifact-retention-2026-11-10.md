# Native CI artifact retention — 10 November 2026

By Jason Stys. The native job still builds and exercises the complete Windows
application, including its independently reconciled Parquet export and durable
restart. Successful pushes and pull requests retain only bounded synthetic
acceptance receipts/screenshots for one day. They no longer automatically upload
the full Windows package to Actions artifact storage.

A maintainer may explicitly request the tested unsigned package through the
trusted-main manual workflow's `retain-package` input. That separate download is
also retained for one day. Public end-user distributions belong in reviewed
Releases. This change deletes no existing run, artifact or cache and does not
change application behavior, source-test requirements or native acceptance.
