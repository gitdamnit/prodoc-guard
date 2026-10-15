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

If the official `skills-ref` validator is installed it is also run and its
result is reported, but never required: this script is fully offline and uses
the Python standard library only.
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


def run_skills_ref(skill_dir):
    """Run the official validator when present. Optional, never required."""
    executable = shutil.which("skills-ref")
    if not executable:
        return {"available": False, "reason": "skills-ref not installed"}
    try:
        proc = subprocess.run(
            [executable, "validate", str(skill_dir)],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover
        return {"available": True, "error": str(exc)}
    return {
        "available": True,
        "returncode": proc.returncode,
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
        "skills_ref": run_skills_ref(skill_dir),
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
        ref = payload["skills_ref"]
        if ref.get("available") and "returncode" in ref:
            print("  skills-ref: exit %d" % ref["returncode"])
        else:
            print("  skills-ref: %s (optional)" % ref.get("reason", "not run"))
        print("result: %s" % ("PASS" if payload["ok"] else "FAIL"))

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
