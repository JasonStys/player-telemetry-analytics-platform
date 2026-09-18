"""File: __main__.py
Purpose: Route python -m telemetry_platform to the tested command-line entry point.
Symbols and line locations: see the generated docs/code-index.md catalog.
Important variables: none; execution delegates directly to cli.main.
"""

from telemetry_platform.cli import main

raise SystemExit(main())
