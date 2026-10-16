"""Shared test helpers for ProDoc Guard.

Every test runs against a disposable Git repository and an isolated HOME, so no
real project, user configuration, or network resource is touched.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLI = REPO_ROOT / "scripts" / "prodoc"
CHECK_SKILL = REPO_ROOT / "scripts" / "check_skill.py"
TEMPLATES = REPO_ROOT / "templates"
CANONICAL_DOCS = ("PRODUCT_REQUIREMENTS.md", "DECISION_LOG.md", "PROJECT_STATUS.md")

AUTHOR_NAME = "ProDoc Tests"
AUTHOR_EMAIL = "tests@example.invalid"


def load_prodoc():
    """Import scripts/prodoc (extensionless) as a module."""
    loader = importlib.machinery.SourceFileLoader("prodoc_cli_under_test", str(CLI))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def base_env(home):
    """A hermetic environment: no system/global Git config, no prompts, no network auth."""
    env = dict(os.environ)
    env.update(
        {
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(Path(home) / ".config"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "true",
            "GIT_AUTHOR_NAME": AUTHOR_NAME,
            "GIT_AUTHOR_EMAIL": AUTHOR_EMAIL,
            "GIT_COMMITTER_NAME": AUTHOR_NAME,
            "GIT_COMMITTER_EMAIL": AUTHOR_EMAIL,
            "PYTHONIOENCODING": "utf-8",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    env.pop("PRODOC_TEMPLATES", None)
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    return env


def run_cli(args, cwd, env):
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )


def run_git(args, cwd, env, check=True):
    proc = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    if check and proc.returncode != 0:
        raise AssertionError("git %s failed (%d): %s" % (" ".join(args), proc.returncode, proc.stderr))
    return proc


# --------------------------------------------------------------------------
# fixture documents
# --------------------------------------------------------------------------


def valid_product_requirements():
    body = ["# Product Requirements", ""]
    for section in (
        "Project Identity",
        "Purpose",
        "Intended Users",
        "Functional Requirements",
        "Nonfunctional Requirements",
        "Scope and Exclusions",
        "Technical Constraints",
        "Acceptance Criteria",
        "Release Objectives",
    ):
        body.append("## %s" % section)
        body.append("")
        body.append("Fixture content for %s." % section)
        body.append("")
    return "\n".join(body)


def valid_decision_log(with_decision=True, decision_id="D-0001"):
    body = [
        "# Decision Log",
        "",
        "## How to Use This Log",
        "",
        "Append-only. Copy the block below.",
        "",
        "```markdown",
        "### D-9999 — Example only, inside a fence",
        "",
        "- **Date:** YYYY-MM-DD",
        "- **Status:** Accepted",
        "- **Context:** example",
        "- **Alternatives Considered:** example",
        "- **Decision:** example",
        "- **Rationale:** example",
        "- **Consequences:** example",
        "- **Supersedes:** None",
        "```",
        "",
        "## Decisions",
        "",
    ]
    if with_decision:
        body.extend(
            [
                "### %s — Fixture decision" % decision_id,
                "",
                "- **Date:** 2026-01-01",
                "- **Status:** Accepted",
                "- **Context:** fixture context",
                "- **Alternatives Considered:** other things",
                "- **Decision:** do the thing",
                "- **Rationale:** because",
                "- **Consequences:** some",
                "- **Supersedes:** None",
                "",
            ]
        )
    else:
        body.append("_No decisions recorded yet._")
        body.append("")
    return "\n".join(body)


def valid_project_status(
    phase="Planning",
    commit="-",
    tree="unknown",
    tests_rows=None,
    work=None,
    verification=None,
    legacy=False,
):
    """A structurally valid PROJECT_STATUS.md.

    legacy=True emits the deprecated heading, markers and field names, so the
    migration and deprecation paths can be exercised.
    """
    if tests_rows is None:
        tests_rows = ["| none | - | Not run | - |"]
    if work is None:
        work = ["- [Planned] Fixture work item"]
    if verification is None:
        verification = []
    if legacy:
        state_heading = "Verified State"
        start, end = "<!-- prodoc:verified:start -->", "<!-- prodoc:verified:end -->"
        state_fields = [
            "- **Branch:** %s" % ("-" if commit == "-" else "main"),
            "- **Commit:** %s" % commit,
            "- **Working tree:** %s" % tree,
            "- **Verified at:** 2026-01-01T00:00:00Z",
        ]
    else:
        state_heading = "Repository State"
        start, end = "<!-- prodoc:observed:start -->", "<!-- prodoc:observed:end -->"
        state_fields = [
            "- **Observed branch:** %s" % ("-" if commit == "-" else "main"),
            "- **Observed commit:** %s" % commit,
            "- **Observed working tree:** %s" % tree,
            "- **Observed at:** 2026-01-01T00:00:00Z",
        ]
    body = [
        "# Project Status",
        "",
        "## Current Phase",
        "",
        phase,
        "",
        "## %s" % state_heading,
        "",
        start,
        *state_fields,
        end,
        "",
        "## Verification Evidence",
        "",
        *(verification or ["_No verification recorded yet._"]),
        "",
        "## Completed Work",
        "",
        *work,
        "",
        "## Tests",
        "",
        "| Suite | Command | Result | Evidence |",
        "| --- | --- | --- | --- |",
        *tests_rows,
        "",
        "## Known Defects",
        "",
        "None known.",
        "",
        "## Blockers",
        "",
        "None.",
        "",
        "## Next Actions",
        "",
        "1. Finish the fixture.",
        "",
        "## Release Status",
        "",
        "Not released.",
        "",
    ]
    return "\n".join(body)


def valid_docs():
    return {
        "PRODUCT_REQUIREMENTS.md": valid_product_requirements(),
        "DECISION_LOG.md": valid_decision_log(),
        "PROJECT_STATUS.md": valid_project_status(),
    }


# --------------------------------------------------------------------------
# base test case
# --------------------------------------------------------------------------


class RepoCase(unittest.TestCase):
    """A disposable Git repository plus an isolated HOME."""

    #: when True, setUp creates a repository with one commit
    init_git = True

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="prodoc-test-")
        self.addCleanup(shutil.rmtree, self._tmp, ignore_errors=True)
        self.home = Path(self._tmp) / "home"
        self.home.mkdir()
        self.env = base_env(self.home)
        self.repo = Path(self._tmp) / "project"
        self.repo.mkdir()
        if self.init_git:
            self.git("init", "-q")
            self.git("config", "user.name", AUTHOR_NAME)
            self.git("config", "user.email", AUTHOR_EMAIL)
            self.git("config", "commit.gpgsign", "false")

    # -- git -------------------------------------------------------------
    def git(self, *args, **kwargs):
        return run_git(args, self.repo, self.env, **kwargs)

    def git_in(self, directory, *args, **kwargs):
        """Run git in another directory (nested repositories, worktrees)."""
        return run_git(args, Path(directory), self.env, **kwargs)

    def commit_all(self, message="chore: fixture"):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD").stdout.strip()

    def head(self):
        return self.git("rev-parse", "HEAD").stdout.strip()

    def branch(self):
        return self.git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()

    # -- prodoc ----------------------------------------------------------
    def cli(self, *args, cwd=None):
        return run_cli(args, cwd or self.repo, self.env)

    def cli_json(self, *args, cwd=None):
        proc = self.cli(*(list(args) + ["--json"]), cwd=cwd)
        payload = None
        if proc.stdout.strip():
            payload = json.loads(proc.stdout)
        return proc, payload

    # -- documents -------------------------------------------------------
    def write_docs(self, docs=None, commit=False):
        for name, text in (docs or valid_docs()).items():
            (self.repo / name).write_text(text, encoding="utf-8")
        if commit:
            return self.commit_all("docs: fixture documents")
        return None

    def read(self, name):
        return (self.repo / name).read_text(encoding="utf-8")

    def errors(self, payload):
        return [f for f in payload["findings"] if f["severity"] == "error"]

    def warnings(self, payload):
        return [f for f in payload["findings"] if f["severity"] == "warning"]

    def codes(self, payload, severity=None):
        return [
            f["code"]
            for f in payload["findings"]
            if severity is None or f["severity"] == severity
        ]
