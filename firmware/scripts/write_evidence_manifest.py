#!/usr/bin/env python3
"""Write a machine-readable inventory for one synchronized Stillair run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def artifact(path: Path) -> dict[str, object]:
    if path.is_dir():
        files = [item for item in sorted(path.rglob("*")) if item.is_file()]
        return {
            "path": str(path),
            "kind": "directory",
            "files": len(files),
            "bytes": sum(item.stat().st_size for item in files),
            "members": [
                {
                    "path": str(item.relative_to(path)),
                    "bytes": item.stat().st_size,
                    "sha256": digest(item),
                }
                for item in files
            ],
        }
    return {
        "path": str(path),
        "kind": "file",
        "bytes": path.stat().st_size,
        "sha256": digest(path),
    }


def pairs(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"expected NAME=VALUE, got {value!r}")
        name, item = value.split("=", 1)
        if not name or name in result:
            raise ValueError(f"invalid or duplicate name {name!r}")
        result[name] = item
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--field", action="append", default=[])
    parser.add_argument("--artifact", action="append", default=[])
    args = parser.parse_args()
    fields = pairs(args.field)
    paths = pairs(args.artifact)
    missing = [f"{name}={path}" for name, path in paths.items() if not Path(path).exists()]
    if missing:
        parser.error("missing artifacts: " + ", ".join(missing))
    payload = {
        "type": "stillair_evidence_manifest",
        "schema_version": 1,
        "fields": fields,
        "artifacts": {name: artifact(Path(path)) for name, path in paths.items()},
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
