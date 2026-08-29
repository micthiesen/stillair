#!/usr/bin/env python3
"""Audit KiCad window hygiene for a project managed by yabai."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


EDITOR_NAMES = {"PCB Editor", "Schematic Editor", "Footprint Editor", "Symbol Editor"}


def yabai_windows() -> list[dict[str, Any]]:
    try:
        result = subprocess.run(
            ["yabai", "-m", "query", "--windows"],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        raise SystemExit("error: yabai is not installed or not on PATH") from None
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or f"exit {exc.returncode}"
        raise SystemExit(f"error: yabai window query failed: {detail}") from None

    data = json.loads(result.stdout)
    if not isinstance(data, list):
        raise SystemExit("error: yabai returned an unexpected window payload")
    return data


def is_editor(window: dict[str, Any]) -> bool:
    app = str(window.get("app", ""))
    title = str(window.get("title", ""))
    return app in EDITOR_NAMES or any(name in title for name in EDITOR_NAMES)


def is_manager(window: dict[str, Any], stem: str) -> bool:
    app = str(window.get("app", ""))
    title = str(window.get("title", ""))
    return app == "KiCad" and stem in title and not is_editor(window)


def is_stray_editor(window: dict[str, Any], stem: str) -> bool:
    if not is_editor(window):
        return False
    title = str(window.get("title", ""))
    lowered = title.lower()
    return stem not in title or "untitled" in lowered


def describe(window: dict[str, Any]) -> str:
    state = "minimized" if window.get("is-minimized") else "visible"
    return f'{window.get("app", "?")}: {window.get("title", "")!r} ({state})'


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check that KiCad editors belong to one project and its manager is minimized."
    )
    parser.add_argument("project", type=Path, help="path to the target .kicad_pro file")
    parser.add_argument("--json", action="store_true", help="emit machine-readable results")
    args = parser.parse_args()

    if args.project.suffix != ".kicad_pro":
        parser.error("project must be a .kicad_pro path")
    if not args.project.is_file():
        parser.error(f"project does not exist: {args.project}")

    stem = args.project.stem
    windows = yabai_windows()
    kicad_windows = [
        window
        for window in windows
        if str(window.get("app", "")) == "KiCad" or is_editor(window)
    ]
    managers = [window for window in kicad_windows if is_manager(window, stem)]
    editors = [window for window in kicad_windows if is_editor(window)]
    stray = [window for window in editors if is_stray_editor(window, stem)]
    active_project_editors = [window for window in editors if window not in stray]

    problems: list[str] = []
    if active_project_editors and not managers:
        problems.append(f"no {stem!r} project-manager window is open")
    if active_project_editors and any(not window.get("is-minimized") for window in managers):
        problems.append("the project-manager window is not minimized")
    if stray:
        problems.append("stand-alone or untitled editor windows are open")

    payload = {
        "project": str(args.project),
        "ok": not problems,
        "problems": problems,
        "managers": managers,
        "project_editors": active_project_editors,
        "stray_editors": stray,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        if not kicad_windows:
            print(f"OK: no KiCad windows are open for {stem}")
        else:
            for window in kicad_windows:
                print(describe(window))
            if problems:
                for problem in problems:
                    print(f"PROBLEM: {problem}", file=sys.stderr)
            else:
                print(f"OK: {stem} window state is clean")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
