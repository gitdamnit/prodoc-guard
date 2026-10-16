#!/usr/bin/env python3
"""check_skill.py -- validate a Skill directory against the Agent Skills spec.

Checks the rules documented at https://agentskills.io/specification:
frontmatter shape, `name` conventions, description and compatibility length
limits, progressive-disclosure budgets, and cross-references to bundled files.

Usage:
    python3 scripts/check_skill.py [SKILL_DIR] [--json]

Exit codes:
    0  no errors (warnings may still be reported)
    1  specification errors found
    3  SKILL.md not found or unusable

If an official Agent Skills validator is already installed on this machine it is
also run and its result is reported, but never required. Pass --official to fetch
one with uvx when it is missing; that is the only code path here that may use the
network, and it is never taken by default.
"""

from __future__ import annotations

import argparse
import importlib.machinery
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRODOC_PATH = HERE / "prodoc"


def load_prodoc():
    loader = importlib.machinery.SourceFileLoader("prodoc_cli", str(PRODOC_PATH))
    spec = importlib.util.spec_from_loader("prodoc_cli", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def local_official_command(skill_dir):
    """Return (label, argv) for an already-installed official validator, or None.

    Looks only at what is on this machine: the two executable names the reference
    library has shipped under, then the importable module. Nothing is downloaded,
    so this preserves the project's no-network guarantee.
    """
    for name in ("skills-ref", "agentskills"):
        executable = shutil.which(name)
        if executable:
            return name, [executable, "validate", str(skill_dir)]
    try:
        spec = importlib.util.find_spec("agentskills")
    except (ImportError, ValueError):  # pragma: no cover - environment dependent
        spec = None
    if spec is None:
        return None
    return "python -m agentskills", [sys.executable, "-m", "agentskills", "validate", str(skill_dir)]


def fetch_official_command(skill_dir):
    """Return (label, argv) that fetch the official validator with uvx, or None.

    This is the only code path in the project that may reach the network. It runs
    only when --official is passed, and only when the validator is not already
    installed.
    """
    executable = shutil.which("uvx")
    if not executable:
        return None
    return (
        "uvx --from skills-ref agentskills",
        [executable, "--from", "skills-ref", "agentskills", "validate", str(skill_dir)],
    )


def run_official(skill_dir, allow_download=False):
    """Run the official Agent Skills validator when one is obtainable."""
    candidate = local_official_command(skill_dir)
    if candidate is None:
        if not allow_download:
            return {
                "available": False,
                "reason": (
                    "official validator not installed locally; pass --official to fetch it "
                    "with uvx (needs network) or install it yourself"
                ),
            }
        candidate = fetch_official_command(skill_dir)
        if candidate is None:
            return {
                "available": False,
                "reason": "no local validator, and uvx is not installed to fetch one",
            }
    label, argv = candidate
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover
        return {"available": True, "command": label, "error": str(exc)}
    return {
        "available": True,
        "command": label,
        "returncode": proc.returncode,
        "passed": proc.returncode == 0,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="check_skill.py",
        description="Validate a Skill directory against the Agent Skills specification.",
    )
    parser.add_argument("skill_dir", nargs="?", default=".", help="skill directory (default: .)")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument(
        "--official",
        action="store_true",
        help=(
            "also run the official Agent Skills validator, fetching it with uvx if it is "
            "not already installed (this is the only option that may use the network)"
        ),
    )
    parser.add_argument(
        "--no-official",
        action="store_true",
        help="skip the official validator entirely",
    )
    args = parser.parse_args(argv)

    prodoc = load_prodoc()
    skill_dir = Path(args.skill_dir).expanduser().resolve()
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.is_file():
        sys.stderr.write("check_skill.py: SKILL.md not found in %s\n" % skill_dir)
        return 3

    text = skill_file.read_text(encoding="utf-8")
    findings, data = prodoc.validate_skill_frontmatter(text, skill_dir.name)

    # Cross-check references to bundled files. scripts/prodoc is executed from
    # the skill directory root, so relative paths must resolve there.
    missing = []
    for reference in prodoc.referenced_bundled_files(text):
        if not (skill_dir / reference).exists():
            missing.append(reference)
            findings.append(
                prodoc.Finding(
                    "skill.reference",
                    "referenced bundled file does not exist: %s" % reference,
                    "error",
                    "SKILL.md",
                )
            )

    errors = [f for f in findings if f["severity"] == "error"]
    payload = {
        "skill_dir": str(skill_dir),
        "skill_md": str(skill_file),
        "lines": len(text.splitlines()),
        "name": data.get("name") if isinstance(data, dict) else None,
        "description_length": (
            len(data.get("description", "")) if isinstance(data, dict) else None
        ),
        "findings": findings,
        "missing_references": missing,
        "errors": len(errors),
        "ok": not errors,
        "official_validator": (
            {"available": False, "reason": "skipped by --no-official"}
            if args.no_official
            else run_official(skill_dir, allow_download=args.official)
        ),
        "spec": "https://agentskills.io/specification",
    }

    if args.json:
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    else:
        print("skill: %s" % payload["name"])
        print("lines: %d   description: %d chars" % (payload["lines"], payload["description_length"] or 0))
        for finding in findings:
            print("  %-7s %s" % (finding["severity"].upper(), finding["message"]))
        if not findings:
            print("  OK      no specification issues found")
        ref = payload["official_validator"]
        if ref.get("available") and "returncode" in ref:
            print("  official: %s -> exit %d" % (ref.get("command", "?"), ref["returncode"]))
            if ref["returncode"] != 0:
                print(ref.get("stdout") or ref.get("stderr") or "")
        elif ref.get("available"):
            print("  official: %s -> %s" % (ref.get("command", "?"), ref.get("error", "no result")))
        else:
            print("  official: not run (%s)" % ref.get("reason", "unknown"))
        print("result: %s" % ("PASS" if payload["ok"] else "FAIL"))

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
