#!/usr/bin/env python3
"""Run the ProDoc Guard test suite and emit machine-readable evidence.

Usage:
    python3 tests/run_tests.py [options]

By default results are written to a scratch directory (`test-output/`, ignored by
Git), so running the suite never dirties a tracked file. Writing the committed
evidence in `docs/` is a separate, explicit act:

    python3 tests/run_tests.py --update-evidence --force

Options:
    --output DIR        write results to DIR instead of test-output/
    --update-evidence   write the committed evidence in docs/ (refuses to
                        overwrite unless --force is also given)
    --force             allow --update-evidence to replace existing evidence
    --pattern GLOB      only run matching test modules (default: test_*.py)
    --quiet             suppress the per-test stream
    --no-gates          skip the post-suite document gates

Exit codes:
    0  every test passed and every gate passed
    1  at least one test or gate failed
    2  usage error (including a refused evidence overwrite)
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import platform
import subprocess
import sys
import time
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
EVIDENCE_DIR = REPO_ROOT / "docs"
DEFAULT_OUTPUT_DIRNAME = "test-output"
JSON_NAME = "test-results.json"
REPORT_NAME = "TEST_REPORT.md"
SCHEMA = "prodoc-guard/test-results@1"

# Post-suite gates. These run after the report exists, because the canonical
# documents cite the report itself as evidence.
GATES = (
    ("skill-spec", [sys.executable, "scripts/check_skill.py", "."]),
    ("documents-validate", [sys.executable, "scripts/prodoc", "validate"]),
    ("documents-check", [sys.executable, "scripts/prodoc", "check"]),
)


def output_paths(repo_root, output_dir=None, update_evidence=False):
    """Return (results_path, report_path, mode) for this run.

    mode is "scratch" for the default untracked directory, "custom" for an
    explicit --output, and "evidence" for docs/, which is tracked.
    """
    if update_evidence:
        base = Path(repo_root) / "docs"
        mode = "evidence"
    elif output_dir:
        base = Path(output_dir).expanduser()
        if not base.is_absolute():
            base = Path.cwd() / base
        mode = "custom"
    else:
        base = Path(repo_root) / DEFAULT_OUTPUT_DIRNAME
        mode = "scratch"
    return base / JSON_NAME, base / REPORT_NAME, mode


def evidence_overwrite_guard(paths, update_evidence, force):
    """Return a refusal message when a run would clobber committed evidence.

    Test evidence is tracked and cited from PROJECT_STATUS.md, so replacing it is
    a deliberate act with an explicit flag, never a side effect of running tests.
    """
    if not update_evidence or force:
        return None
    existing = [str(path) for path in paths if Path(path).exists()]
    if not existing:
        return None
    return (
        "refusing to overwrite existing test evidence: %s\n"
        "Those files are tracked and cited from PROJECT_STATUS.md. Pass --force to replace "
        "them, or drop --update-evidence to write to %s/ instead."
        % (", ".join(existing), DEFAULT_OUTPUT_DIRNAME)
    )


# Required test areas, mapped to the topic they prove.
COVERAGE = (
    ("Skill metadata and specification", ("frontmatter", "skill", "template", "progressive")),
    ("Skill discovery paths and installation docs", ("documentation", "compatibility", "readme")),
    ("New repository initialization", ("init",)),
    ("Missing document recovery", ("missing_document", "missing_section")),
    ("Existing document preservation", ("never_overwrites", "refreshes_only")),
    ("Clean and dirty working trees", ("tree", "dirty")),
    ("Multiple branches", ("branches",)),
    ("Detached HEAD", ("detached",)),
    ("Unborn repository (no commits)", ("unborn", "without_commits", "no_commits")),
    ("Concurrent modification", ("concurrent",)),
    ("Read-only repositories", ("read_only",)),
    ("Invalid and missing Git remotes", ("remote",)),
    ("Idempotency", ("idempotent",)),
    ("Append-only decision history", ("append_only", "fenced_decision", "duplicate", "out_of_order")),
    ("False completion prevention", ("claim_without_evidence", "work_state", "claim_with_evidence")),
    ("Fabricated test result prevention", ("fabricated", "evidence_must_exist", "not_run")),
    ("Secret detection and redaction", ("secret", "credentials_redacted")),
    ("Git operations and exit codes", ("exit", "usage", "environment_error", "never_mutates", "quiet", "json_schema")),
    ("CLI behaviour (JSON, help, repo flag)", ("json", "help", "repo_flag", "dry_run", "phase", "status", "validate")),
)


class Collector(unittest.TextTestResult):
    """Records one entry per test so results can be serialised."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []
        self._started = {}

    def startTest(self, test):
        self._started[test.id()] = time.time()
        super().startTest(test)

    def _record(self, test, status, message=None):
        started = self._started.pop(test.id(), time.time())
        self.records.append(
            {
                "id": test.id(),
                "suite": test.id().split(".")[0],
                "status": status,
                "duration_seconds": round(time.time() - started, 4),
                "message": message,
            }
        )

    def addSuccess(self, test):
        super().addSuccess(test)
        self._record(test, "passed")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._record(test, "failed", self._exc_info_to_string(err, test).strip().splitlines()[-1])

    def addError(self, test, err):
        super().addError(test, err)
        self._record(test, "errored", self._exc_info_to_string(err, test).strip().splitlines()[-1])

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._record(test, "skipped", reason)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._record(test, "expected-failure")

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._record(test, "unexpected-success")


def git(*args):
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout.strip() if proc.returncode == 0 else None


def environment():
    return {
        "python": sys.version.split()[0],
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "git": (subprocess.run(["git", "--version"], capture_output=True, text=True).stdout.strip()
                if _which("git") else None),
        "run_as_root": hasattr(os, "geteuid") and os.geteuid() == 0,
    }


def _which(name):
    from shutil import which

    return which(name)


def repository_state():
    return {
        "root": str(REPO_ROOT),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "commit": git("rev-parse", "HEAD"),
        "working_tree": "dirty" if (git("status", "--porcelain") or "") else "clean",
    }


def run_gates():
    results = []
    for name, command in GATES:
        started = time.time()
        proc = subprocess.run(command, cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=300)
        results.append(
            {
                "name": name,
                "command": " ".join(command),
                "returncode": proc.returncode,
                "passed": proc.returncode == 0,
                "duration_seconds": round(time.time() - started, 4),
                "stdout": proc.stdout.strip()[:4000],
                "stderr": proc.stderr.strip()[:2000],
            }
        )
    return results


def summarise(records, gates, duration):
    counts = {"passed": 0, "failed": 0, "errored": 0, "skipped": 0}
    for record in records:
        counts[record["status"]] = counts.get(record["status"], 0) + 1
    suites = {}
    for record in records:
        entry = suites.setdefault(
            record["suite"], {"suite": record["suite"], "tests": 0, "passed": 0, "failed": 0, "errored": 0, "skipped": 0}
        )
        entry["tests"] += 1
        entry[record["status"]] += 1
    gates_ok = all(gate["passed"] for gate in gates)
    return {
        "tests": len(records),
        "passed": counts.get("passed", 0),
        "failed": counts.get("failed", 0),
        "errored": counts.get("errored", 0),
        "skipped": counts.get("skipped", 0),
        "duration_seconds": round(duration, 3),
        "suites": sorted(suites.values(), key=lambda s: s["suite"]),
        "gates_passed": gates_ok,
        "ok": counts.get("failed", 0) == 0 and counts.get("errored", 0) == 0 and gates_ok,
    }


def coverage(records):
    rows = []
    for topic, needles in COVERAGE:
        matched = [
            record["id"] for record in records if any(needle in record["id"].lower() for needle in needles)
        ]
        rows.append(
            {
                "topic": topic,
                "tests": len(matched),
                "matched": sorted({n for n in needles if n in " ".join(matched).lower()}),
            }
        )
    return rows


def write_json(payload, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_report(payload, path):
    totals = payload["totals"]
    lines = [
        "# Test Report",
        "",
        "Generated by `%s`. This file is evidence: it is cited from" % payload["command"],
        "`PROJECT_STATUS.md` when written with `--update-evidence`.",
        "",
        "| Field | Value |",
        "| --- | --- |",
        "| Generated at | %s |" % payload["generated_at"],
        "| Command | `%s` |" % payload["command"],
        "| Output mode | %s |" % payload["output_mode"],
        "| Pattern | `%s` |" % payload["pattern"],
        "| Result | %s |" % ("PASS" if totals["ok"] else "FAIL"),
        "| Tests | %d total, %d passed, %d failed, %d errored, %d skipped |"
        % (totals["tests"], totals["passed"], totals["failed"], totals["errored"], totals["skipped"]),
        "| Duration | %ss |" % totals["duration_seconds"],
        "| Branch | `%s` |" % (payload["repository"]["branch"] or "(detached)"),
        "| Commit under test | `%s` |" % (payload["repository"]["commit"] or "(none)"),
        "| Working tree | %s |" % payload["repository"]["working_tree"],
        "",
        "## Environment",
        "",
        "| Key | Value |",
        "| --- | --- |",
        "| Python | %s (%s) |" % (payload["environment"]["python"], payload["environment"]["implementation"]),
        "| Platform | %s |" % payload["environment"]["platform"],
        "| Git | %s |" % (payload["environment"]["git"] or "not found"),
        "| Root user | %s |" % payload["environment"]["run_as_root"],
        "| Isolation | one disposable Git repository and one temporary HOME per test; no network use |",
        "",
        "## Suites",
        "",
        "| Suite | Tests | Passed | Failed | Errored | Skipped |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for suite in totals["suites"]:
        lines.append(
            "| `%s` | %d | %d | %d | %d | %d |"
            % (suite["suite"], suite["tests"], suite["passed"], suite["failed"], suite["errored"], suite["skipped"])
        )
    lines += ["", "## Gates", "", "| Gate | Command | Result |", "| --- | --- | --- |"]
    for gate in payload["gates"]:
        lines.append(
            "| %s | `%s` | %s (exit %d) |"
            % (gate["name"], gate["command"], "PASS" if gate["passed"] else "FAIL", gate["returncode"])
        )
    lines += [
        "",
        "The gates run after this report is written, because the canonical documents",
        "cite it as evidence.",
        "",
    ]

    failures = [r for r in payload["tests"] if r["status"] in ("failed", "errored")]
    lines += ["## Failures", ""]
    if failures:
        for record in failures:
            lines.append("- `%s`: %s" % (record["id"], record["message"]))
    else:
        lines.append("None.")
    lines.append("")

    skipped = [r for r in payload["tests"] if r["status"] == "skipped"]
    lines += ["## Skipped", ""]
    if skipped:
        for record in skipped:
            lines.append("- `%s`: %s" % (record["id"], record["message"]))
    else:
        lines.append("None.")
    lines.append("")

    lines += [
        "## Coverage of required areas",
        "",
        "| Area | Matching tests |",
        "| --- | --- |",
    ]
    for row in payload["coverage"]:
        lines.append("| %s | %d |" % (row["topic"], row["tests"]))
    lines += [
        "",
        "## Test inventory",
        "",
        "| Test | Status | Seconds |",
        "| --- | --- | --- |",
    ]
    for record in payload["tests"]:
        lines.append("| `%s` | %s | %s |" % (record["id"], record["status"], record["duration_seconds"]))
    lines.append("")
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="run_tests.py", description="Run the ProDoc Guard test suite."
    )
    parser.add_argument("--quiet", action="store_true", help="suppress the per-test stream")
    parser.add_argument("--no-gates", action="store_true", help="skip the post-suite document gates")
    parser.add_argument(
        "--output",
        default=None,
        help="directory for generated results (default: %s/, untracked)" % DEFAULT_OUTPUT_DIRNAME,
    )
    parser.add_argument(
        "--update-evidence",
        action="store_true",
        help="write the tracked evidence in docs/ instead of the scratch directory",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="allow --update-evidence to replace existing evidence files",
    )
    parser.add_argument(
        "--pattern",
        default="test_*.py",
        help="only run matching test modules (default: test_*.py)",
    )
    args = parser.parse_args(argv)

    json_path, report_path, mode = output_paths(REPO_ROOT, args.output, args.update_evidence)
    problem = evidence_overwrite_guard((json_path, report_path), args.update_evidence, args.force)
    if problem:
        sys.stderr.write("run_tests: %s\n" % problem)
        return 2

    loader = unittest.TestLoader()
    suite = loader.discover(str(TESTS_DIR), pattern=args.pattern, top_level_dir=str(TESTS_DIR))
    runner = unittest.TextTestRunner(
        stream=sys.stderr if args.quiet else sys.stdout, verbosity=0 if args.quiet else 2
    )
    result = Collector(runner.stream, True, runner.verbosity)
    started = time.time()
    suite.run(result)
    duration = time.time() - started

    gates = [] if args.no_gates else run_gates()
    totals = summarise(result.records, gates, duration)

    command = "python3 tests/run_tests.py"
    if args.pattern != "test_*.py":
        command += " --pattern %s" % args.pattern
    if args.update_evidence:
        command += " --update-evidence"
        if args.force:
            command += " --force"
    elif args.output:
        command += " --output %s" % args.output

    payload = {
        "schema": SCHEMA,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "command": command,
        "output_mode": mode,
        "pattern": args.pattern,
        "environment": environment(),
        "repository": repository_state(),
        "totals": totals,
        "gates": gates,
        "coverage": coverage(result.records),
        "tests": sorted(result.records, key=lambda r: r["id"]),
    }
    write_json(payload, json_path)
    write_report(payload, report_path)

    summary = "tests=%d passed=%d failed=%d errored=%d skipped=%d gates=%s result=%s" % (
        totals["tests"],
        totals["passed"],
        totals["failed"],
        totals["errored"],
        totals["skipped"],
        "pass" if totals["gates_passed"] else "fail",
        "PASS" if totals["ok"] else "FAIL",
    )
    sys.stdout.write(summary + "\n")
    try:
        shown_json = json_path.relative_to(REPO_ROOT)
        shown_report = report_path.relative_to(REPO_ROOT)
    except ValueError:
        shown_json, shown_report = json_path, report_path
    sys.stdout.write(
        "wrote %s and %s (%s)\n" % (shown_json, shown_report, mode)
    )
    if mode == "scratch":
        sys.stdout.write(
            "tracked evidence in docs/ was not touched; use --update-evidence --force to refresh it\n"
        )
    return 0 if totals["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
