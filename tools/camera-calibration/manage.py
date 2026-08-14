#!/usr/bin/env python3
"""Restore and remove DiveTopo's local camera-calibration interface safely."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional

from pending_preview import PendingPreview


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
WEB_ROOT = REPOSITORY_ROOT / "apps" / "web"
CALIBRATION_REMOVAL_COMMIT = "76a561ae1629bfad3919cd7dd273d8c00aff6fc5"
PATCH_TARGETS = (
    "apps/web/app/TerrainViewer.tsx",
    "apps/web/app/globals.css",
)


class CalibrationToolError(RuntimeError):
    """A safe calibration-tool transition could not be completed."""


def git(
    *arguments: str, input_bytes: Optional[bytes] = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ("git", *arguments),
        cwd=REPOSITORY_ROOT,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def calibration_patch() -> bytes:
    commit_check = git("cat-file", "-e", f"{CALIBRATION_REMOVAL_COMMIT}^{{commit}}")
    if commit_check.returncode != 0:
        raise CalibrationToolError(
            f"Missing calibration history commit {CALIBRATION_REMOVAL_COMMIT}."
        )
    result = git(
        "show",
        "--format=",
        CALIBRATION_REMOVAL_COMMIT,
        "--",
        *PATCH_TARGETS,
    )
    if result.returncode != 0 or not result.stdout:
        raise CalibrationToolError(
            result.stderr.decode().strip() or "Could not read the calibration patch."
        )
    return result.stdout


def patch_applies(patch: bytes, *, reverse: bool) -> bool:
    arguments = ["apply", "--check", "--whitespace=nowarn"]
    if reverse:
        arguments.append("--reverse")
    return git(*arguments, input_bytes=patch).returncode == 0


def state(patch: bytes) -> str:
    can_enable = patch_applies(patch, reverse=True)
    can_disable = patch_applies(patch, reverse=False)
    if can_enable and not can_disable:
        return "disabled"
    if can_disable and not can_enable:
        return "enabled"
    return "modified"


def apply_patch(patch: bytes, *, reverse: bool) -> None:
    arguments = ["apply", "--whitespace=nowarn"]
    if reverse:
        arguments.append("--reverse")
    result = git(*arguments, input_bytes=patch)
    if result.returncode != 0:
        raise CalibrationToolError(
            result.stderr.decode().strip() or "The calibration patch could not be applied."
        )


def enable(patch: bytes) -> None:
    current = state(patch)
    if current == "enabled":
        return
    if current != "disabled":
        raise CalibrationToolError(
            "Calibration files contain other edits; refusing to overwrite them."
        )
    apply_patch(patch, reverse=True)


def disable(patch: bytes) -> None:
    current = state(patch)
    if current == "disabled":
        return
    if current != "enabled":
        raise CalibrationToolError(
            "Calibration files contain other edits; refusing to overwrite them."
        )
    apply_patch(patch, reverse=False)


def run_server(patch: bytes, arguments: list[str]) -> int:
    pending_preview = "--pending-sites" in arguments
    server_arguments = [
        argument for argument in arguments if argument != "--pending-sites"
    ]
    current = state(patch)
    if current != "disabled":
        raise CalibrationToolError(
            "The run command requires a disabled calibration tool so it can own "
            "the complete enable/disable lifecycle."
        )
    enable(patch)
    print("Camera calibration enabled for this development server.")
    preview = PendingPreview() if pending_preview else None
    command = ["npm", "run", "dev"]
    if server_arguments:
        command.extend(("--", *server_arguments))
    try:
        if preview is not None:
            preview.enable()
            print("Pending site preview enabled for this development server.")
        try:
            return subprocess.run(command, cwd=WEB_ROOT, check=False).returncode
        except KeyboardInterrupt:
            return 130
    finally:
        if preview is not None:
            preview.disable()
            print("Pending site preview removed from the working tree.")
        disable(patch)
        print("Camera calibration removed from the working tree.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("run", "enable", "disable", "status", "check-release"),
    )
    parser.add_argument("server_arguments", nargs=argparse.REMAINDER)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        patch = calibration_patch()
        if args.command == "run":
            return run_server(patch, args.server_arguments)
        if args.server_arguments:
            raise CalibrationToolError(
                "Server arguments are accepted only by the run command."
            )
        if args.command == "enable":
            enable(patch)
            print("Camera calibration enabled. Run the local Web application.")
        elif args.command == "disable":
            disable(patch)
            print("Camera calibration disabled.")
        elif args.command == "status":
            print(f"Camera calibration: {state(patch)}")
        elif args.command == "check-release":
            current = state(patch)
            if current != "disabled":
                raise CalibrationToolError(
                    f"Camera calibration must be disabled for release (current state: {current})."
                )
            print("Release check passed: camera calibration is disabled.")
        return 0
    except CalibrationToolError as error:
        print(f"camera-calibration: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
