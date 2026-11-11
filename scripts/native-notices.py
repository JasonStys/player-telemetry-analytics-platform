"""File: native-notices.py
Purpose: Preserve bundled Python, Tcl/Tk and installed dependency license notices at build time.
Symbols and important variables are indexed in docs/code-index.md.
Only public toolchain/package metadata is read, never application user profiles.
"""

import importlib.metadata
import shutil
import sys
import tkinter
from pathlib import Path


def copy_notices(destination: Path) -> None:
    """Retain the actual runtime's licensing material beside its frozen executable."""
    if sys.version_info[:3] != (3, 14, 10):
        raise ValueError("The reviewed Python3.14.10 runtime is required")
    destination.mkdir()
    shutil.copyfile(Path(sys.base_prefix) / "LICENSE.txt", destination / "PYTHON-LICENSE.txt")
    interpreter = tkinter.Tk()
    interpreter.withdraw()
    try:
        for component in ("tcl", "tk"):
            location = interpreter.eval(f"set {component}_library")
            content = interpreter.eval(
                f"set notice [open {{{location}/license.terms}} rb]; "
                "set licenseText [read $notice]; close $notice; set licenseText"
            )
            (destination / f"{component.upper()}-LICENSE.txt").write_bytes(
                content.encode("latin-1")
            )
    finally:
        interpreter.destroy()
    for distribution in importlib.metadata.distributions():
        for item in distribution.files or ():
            # Dist-info legal files are public distribution metadata, including transitive notices.
            parts = item.parts
            if not parts or not parts[0].endswith(".dist-info"):
                continue
            if "licenses" not in parts and item.name.lower() not in {
                "license",
                "license.txt",
                "license.md",
                "copying",
                "notice",
                "notice.txt",
            }:
                continue
            source = Path(distribution.locate_file(item))
            if source.is_file():
                target = destination.joinpath(*parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)


if __name__ == "__main__":
    copy_notices(Path(sys.argv[1]))
