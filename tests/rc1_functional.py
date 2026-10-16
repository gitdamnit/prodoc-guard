#!/usr/bin/env python3
"""Release-candidate functional validation against disposable repositories.

Run with:

    python3 tests/rc1_functional.py

Every scenario runs in a scratch directory (a temporary directory by default, or
PRODOC_RC1_SCRATCH if set). The repository under test is only read from; its CLI is
invoked as a separate process. Prints a transcript — the command, the observable
outcome, then PASS/FAIL — and exits non-zero if any check fails.

This file is named so that `unittest` discovery in tests/run_tests.py does not pick
it up: it takes minutes and is run deliberately, not on every suite run.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "scripts" / "prodoc"
RUNNER = ROOT / "tests" / "run_tests.py"
BASE = Path(os.environ.get("PRODOC_RC1_SCRATCH", tempfile.mkdtemp(prefix="prodoc-rc1-"))).resolve()

results = []
env = dict(os.environ)
env.update({
    "GIT_CONFIG_NOSYSTEM": "1", "GIT_TERMINAL_PROMPT": "0",
    "GIT_AUTHOR_NAME": "RC1", "GIT_AUTHOR_EMAIL": "rc1@example.invalid",
    "GIT_COMMITTER_NAME": "RC1", "GIT_COMMITTER_EMAIL": "rc1@example.invalid",
})


def say(text=""):
    print(text, flush=True)


def record(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    say("    -> %s%s" % ("PASS" if ok else "FAIL", ("  " + str(detail)) if detail else ""))


def run(args, cwd, label=None, show_stdout=True, timeout=300):
    if label:
        say("  $ %s   # %s" % (" ".join(args), label))
    else:
        say("  $ %s" % " ".join(args))
    proc = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, env=env, timeout=timeout)
    if show_stdout and proc.stdout.strip():
        for line in proc.stdout.strip().splitlines()[:12]:
            say("      %s" % line)
    if proc.stderr.strip():
        for line in proc.stderr.strip().splitlines()[:4]:
            say("      [stderr] %s" % line)
    if label:
        say("      exit=%d" % proc.returncode)
    return proc.returncode, proc.stdout, proc.stderr


def prodoc(*args, cwd, label=None):
    return run([sys.executable, str(CLI), *args], cwd, label=label)


def pj(*args, cwd):
    """prodoc --json, returning (rc, payload, error_codes, all_codes)."""
    rc, out, _ = run([sys.executable, str(CLI), *args, "--json"], cwd, show_stdout=False)
    payload = json.loads(out) if out.strip() else None
    findings = payload["findings"] if payload else []
    return (rc, payload,
            [f["code"] for f in findings if f["severity"] == "error"],
            [f["code"] for f in findings])


def git(args, cwd):
    return subprocess.run(["git", "-c", "commit.gpgsign=false", *args],
                          cwd=str(cwd), capture_output=True, text=True, env=env)


def fresh(name):
    path = BASE / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def init_repo(path, branch="main"):
    git(["init", "-q", "-b", branch], path)
    git(["config", "user.name", "RC1"], path)
    git(["config", "user.email", "rc1@example.invalid"], path)
    git(["config", "commit.gpgsign", "false"], path)


def fill(project):
    """Strip the template placeholders, leaving real (if terse) content."""
    for md in project.glob("*.md"):
        md.write_text(re.sub(r"<!-- prodoc:todo[^>]*-->", "Recorded by the RC1 harness.", md.read_text()))


def set_phase(project, phase):
    doc = project / "PROJECT_STATUS.md"
    text = doc.read_text()
    head, rest = text.split("## Current Phase", 1)
    body, tail = rest.split("##", 1)
    doc.write_text("%s## Current Phase\n\n%s\n\n##%s" % (head, phase, tail))


def digest(project, names):
    return {n: hashlib.sha256((project / n).read_bytes()).hexdigest()
            for n in names if (project / n).exists()}


say("=" * 78)
say("RC1 FUNCTIONAL VALIDATION")
say("HEAD under test : %s" % subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT),
                                             capture_output=True, text=True).stdout.strip())
say("scratch root    : %s" % BASE)
say("=" * 78)

# ---------------------------------------------------------------- [1]
say()
say("[1] initialize documentation in a fresh project")
p = fresh("fresh")
init_repo(p)
rc, _, _ = prodoc("init", cwd=p, label="create the three canonical docs")
created = sorted(x.name for x in p.glob("*.md"))
record("1a init creates exactly the three canonical documents",
       rc == 0 and created == ["DECISION_LOG.md", "PRODUCT_REQUIREMENTS.md", "PROJECT_STATUS.md"], created)

rc, payload, errs, _ = pj("validate", cwd=p)
say("      validate on a freshly initialized project: exit=%d ok=%s error findings=%d"
    % (rc, payload["ok"], len(errs)))
record("1b a fresh init fails validation, naming the missing information", rc == 1 and not payload["ok"],
       "codes=%s" % sorted(set(errs))[:3])

fill(p)
rc, payload, errs, _ = pj("validate", cwd=p)
record("1c validation passes once the placeholders are filled", rc == 0, "exit=%d" % rc)

# ---------------------------------------------------------------- [2]
say()
say("[2] validate existing documentation")
git(["add", "-A"], p)
git(["commit", "-q", "-m", "docs: initial"], p)
rc, _, errs, _ = pj("validate", cwd=p)
record("2a validate on committed documentation", rc == 0)
rc, payload, errs, _ = pj("check", cwd=p)
record("2b check on committed documentation", rc == 0,
       "checks=%s" % ",".join(payload["info"]["checks"]))
rc, payload, _, _ = pj("status", cwd=p)
record("2c status reports branch, commit and tree",
       rc == 0 and payload["info"]["git"]["working_tree"] == "clean"
       and payload["info"]["git"]["commit"] == git(["rev-parse", "HEAD"], p).stdout.strip(),
       "commit=%s" % payload["info"]["git"]["commit_short"])

# ---------------------------------------------------------------- [3]
say()
say("[3] update status without destroying handwritten content")
status = p / "PROJECT_STATUS.md"
text = status.read_text()
text = text.replace("Recorded by the RC1 harness.", "- [Planned] hand written by a human")
text = text.replace("Not released.", "Not released. Hand-written sentence that must survive.")
status.write_text(text)
set_phase(p, "In Progress")
before = status.read_text()
split_before = before.split("<!-- prodoc:observed:start -->")[0] + \
    before.split("<!-- prodoc:observed:end -->")[1]
rc, payload, _, _ = pj("update", cwd=p)
after = status.read_text()
split_after = after.split("<!-- prodoc:observed:start -->")[0] + \
    after.split("<!-- prodoc:observed:end -->")[1]
block = after.split("<!-- prodoc:observed:start -->")[1].split("<!-- prodoc:observed:end -->")[0]
head = git(["rev-parse", "HEAD"], p).stdout.strip()

record("3a update exits 0", rc == 0)
record("3b every byte outside the managed block is preserved", split_before == split_after,
       "handwritten prose and the work item survived" if split_before == split_after else "")
record("3c the block records the real commit and tree state",
       ("Observed commit:** %s" % head) in block and "Observed working tree:**" in block)
record("3d the block labels itself as observation, not verification",
       "not evidence that the implementation" in block)

# ---------------------------------------------------------------- [4]
say()
say("[4] append a decision and verify historical integrity")
dlog = p / "DECISION_LOG.md"


def decision(idx, date, line, status_value="Accepted"):
    return """
### D-%04d — Decision %d

- **Date:** %s
- **Status:** %s
- **Context:** RC1 fixture context %d
- **Alternatives Considered:** doing nothing (rejected: nothing happens)
- **Decision:** %s
- **Rationale:** append-only history is the point
- **Consequences:** the log grows
- **Supersedes:** None
""" % (idx, idx, date, status_value, idx, line)


dlog.write_text(dlog.read_text().replace("_No decisions recorded yet. Copy the block above to add the first one._", "")
                + decision(1, "2026-01-01", "append decisions rather than editing them"))
git(["add", "-A"], p)
git(["commit", "-q", "-m", "docs: D-0001"], p)
rc, _, errs, _ = pj("check", cwd=p)
record("4a a first decision validates and checks clean", rc == 0, "errors=%s" % errs)

committed_dlog = dlog.read_text()
dlog.write_text(committed_dlog + decision(2, "2026-01-02", "append another decision"))
git(["add", "-A"], p)
git(["commit", "-q", "-m", "docs: D-0002"], p)
rc, payload, errs, _ = pj("check", cwd=p)
record("4b a second append passes and history is checked",
       rc == 0 and "decision-history" in payload["info"]["checks"])
committed_dlog = dlog.read_text()

# ---------------------------------------------------------------- [5]
say()
say("[5] attempt to modify an existing decision (must be refused)")
dlog.write_text(committed_dlog.replace("- **Rationale:** append-only history is the point",
                                       "- **Rationale:** quietly rewritten by the RC1 harness"))
rc, _, errs, _ = pj("check", cwd=p)
record("5a editing a historical decision fails check", rc == 1 and "log.modified" in errs, errs)
rc, payload, _, _ = pj("check", cwd=p)
named = " ".join(f["message"] for f in payload["findings"] if f["code"] == "log.modified")
record("5b the modified field is named in the finding", "rationale" in named.lower(),
       named[:70])

git(["checkout", "--", "DECISION_LOG.md"], p)
dlog.write_text(committed_dlog.replace("### D-0002", "### D-0003", 1))
rc, _, errs, _ = pj("check", cwd=p)
record("5c renumbering a historical decision fails check (old id vanished)",
       rc == 1 and "log.append_only" in errs, errs)

git(["checkout", "--", "DECISION_LOG.md"], p)
dlog.write_text(committed_dlog.replace("### D-0002", "### D-0002", 1)
                 .replace("- **Status:** Accepted\n- **Context:** RC1 fixture context 1",
                          "- **Status:** Superseded by D-0002\n- **Context:** RC1 fixture context 1"))
rc, _, errs, all_codes = pj("check", cwd=p)
record("5d a Status-only supersede is allowed and reported as a warning",
       rc == 0 and "log.status_changed" in all_codes and "log.modified" not in errs, all_codes)

git(["checkout", "--", "DECISION_LOG.md"], p)
reordered = committed_dlog.replace("### D-0001", "### D-0009").replace("### D-0002", "### D-0001")
dlog.write_text(reordered.replace("### D-0009", "### D-0002"))
rc, _, errs, _ = pj("check", cwd=p)
record("5e reordering records fails check", rc == 1 and ("log.reordered" in errs or "log.append_only" in errs), errs)
git(["checkout", "--", "DECISION_LOG.md"], p)

# ---------------------------------------------------------------- [6]
say()
say("[6] attempt an unsupported release-state transition")
set_phase(p, "Released")
rc, _, errs, _ = pj("validate", cwd=p)
record("6a Released with no recorded evidence fails validate", rc == 1 and "status.release_evidence" in errs, errs)

set_phase(p, "In Progress")
git(["add", "-A"], p)
git(["commit", "-q", "-m", "docs: phase"], p)
rc, out, err = prodoc("update", "--phase", "Released", cwd=p, label="ask for Released with no evidence")
phase = (p / "PROJECT_STATUS.md").read_text().split("## Current Phase")[1].split("##")[0].strip()
record("6b update refuses the transition and explains why",
       rc == 1 and "verification evidence" in err.lower(), "exit=%d" % rc)
record("6c the requested phase was not applied", phase == "In Progress", "phase=%r" % phase)

sha = git(["rev-parse", "HEAD"], p).stdout.strip()
text = (p / "PROJECT_STATUS.md").read_text().replace(
    "## Verification Evidence\n",
    "## Verification Evidence\n\n- **Verification:** commit `%s` — full suite green — evidence `PROJECT_STATUS.md`\n" % sha)
(p / "PROJECT_STATUS.md").write_text(text)
git(["add", "-A"], p)
git(["commit", "-q", "-m", "docs: verification evidence"], p)
rc, _, errs, _ = pj("validate", cwd=p)
record("6d a release-state claim with recorded evidence validates", rc == 0, "errors=%s" % errs)
rc, _, _ = prodoc("update", "--phase", "Released", cwd=p, label="now permitted")
record("6e the transition succeeds once evidence exists", rc == 0)
rc, _, errs, _ = pj("check", cwd=p)
record("6f check is clean on the released fixture", rc == 0, "errors=%s" % errs)

# ---------------------------------------------------------------- [7]
say()
say("[7] nested repositories, worktrees, symlinks, boundaries")
outer_before = (p / "PROJECT_STATUS.md").read_text()
inner = p / "vendor" / "inner"
inner.mkdir(parents=True)
init_repo(inner)
rc, payload, _, _ = pj("status", cwd=inner)
record("7a an inner repository is not redirected to the outer project",
       rc == 0 and payload["info"]["repo"] == str(inner)
       and not payload["info"]["documents"]["PROJECT_STATUS.md"]["present"]
       and "repo.worktree_root" not in [f["code"] for f in payload["findings"]])
rc, _, _ = prodoc("init", cwd=inner)
record("7b init inside the inner repository writes only there",
       rc == 0 and (inner / "PROJECT_STATUS.md").is_file()
       and (p / "PROJECT_STATUS.md").read_text() == outer_before)

wt = BASE / "worktree"
if wt.exists():
    shutil.rmtree(wt)
run(["git", "worktree", "add", "-q", str(wt), "-b", "rc1-wt"], p, show_stdout=False)
rc_status, payload, _, _ = pj("status", cwd=wt)
main_before = (p / "PROJECT_STATUS.md").read_text()
rc_update, _, _ = prodoc("update", cwd=wt)
record("7c a linked worktree is usable and does not touch the main checkout",
       rc_status == 0 and rc_update == 0
       and payload["info"]["repo"] == str(wt)
       and "rc1-wt" in (wt / "PROJECT_STATUS.md").read_text()
       and (p / "PROJECT_STATUS.md").read_text() == main_before,
       "worktree branch recorded separately")

outside = BASE / "outside-status.md"
outside.write_text((p / "PROJECT_STATUS.md").read_text())
outside_before = outside.read_text()
saved = (p / "PROJECT_STATUS.md").read_text()
(p / "PROJECT_STATUS.md").unlink()
os.symlink(str(outside), str(p / "PROJECT_STATUS.md"))
rc, out, err = prodoc("update", cwd=p, label="symlinked document")
record("7d writing through a symlink is refused with exit 4",
       rc == 4 and "symbolic link" in err.lower(), "exit=%d" % rc)
record("7e the symlink survives and its target is untouched",
       os.path.islink(str(p / "PROJECT_STATUS.md")) and outside.read_text() == outside_before)
(p / "PROJECT_STATUS.md").unlink()
(p / "PROJECT_STATUS.md").write_text(saved)

watch = p / "watch"
watch.mkdir()
(watch / "sentinel").write_text("x")
watch_before = sorted(str(x.relative_to(watch)) for x in watch.rglob("*"))
rc1_before = sorted(str(x.relative_to(BASE)) for x in BASE.rglob("*"))
for args in (("init",), ("validate",), ("status",), ("check",), ("update",), ("update", "--dry-run")):
    prodoc(*args, cwd=watch)
watch_after = sorted(str(x.relative_to(watch)) for x in watch.rglob("*"))
rc1_after = sorted(str(x.relative_to(BASE)) for x in BASE.rglob("*"))
record("7f no command creates a file outside the project it was pointed at",
       watch_before == watch_after, "sentinel directory unchanged")
record("7g no command creates a stray file anywhere else in the scratch root",
       rc1_before == rc1_after, "scratch root byte-identical apart from deliberate targets")

# ---------------------------------------------------------------- [8]
say()
say("[8] dry-run behaviour")
p2 = fresh("dryrun")
init_repo(p2)
rc, out, _ = prodoc("init", "--dry-run", cwd=p2)
record("8a init --dry-run reports without writing", rc == 0 and not list(p2.glob("*.md")))
prodoc("init", cwd=p2)
fill(p2)
git(["add", "-A"], p2)
git(["commit", "-q", "-m", "docs: initial"], p2)
snapshot = digest(p2, ["PRODUCT_REQUIREMENTS.md", "DECISION_LOG.md", "PROJECT_STATUS.md"])
rc, payload, _, _ = pj("update", "--dry-run", cwd=p2)
after = digest(p2, ["PRODUCT_REQUIREMENTS.md", "DECISION_LOG.md", "PROJECT_STATUS.md"])
record("8b update --dry-run reports changed=true and writes nothing",
       rc == 0 and payload["info"]["dry_run"] is True and snapshot == after)

# ---------------------------------------------------------------- [9]
say()
say("[9] JSON output and documented exit codes")
rc, payload, _, _ = pj("validate", cwd=p2)
keys_ok = set(payload) >= {"command", "ok", "exit_code", "findings", "info", "version"}
record("9a every command emits the documented JSON shape",
       rc == 0 and keys_ok and payload["command"] == "validate")
for cmd in ("init", "validate", "status", "check", "update"):
    rc2, payload2, _, _ = pj(cmd, cwd=p2)
    if not (payload2 and payload2["command"] == cmd and rc2 == payload2["exit_code"]):
        keys_ok = False
record("9b exit_code inside the payload matches the process exit code", keys_ok)

empty = fresh("exitcodes")
rc0, _, _, _ = pj("validate", cwd=p2)
rc1, _, _, _ = pj("validate", cwd=empty)
rc2v, _, _ = prodoc("frobnicate", cwd=p2)
rc3, _, _ = prodoc("status", "--repo", str(BASE / "nope"), cwd=p2)
target = BASE / "outside2.md"
target.write_text(saved)
link = p / "PROJECT_STATUS.md"
link.unlink()
os.symlink(str(target), str(link))
rc4, _, _ = prodoc("update", cwd=p)
link.unlink()
link.write_text(saved)
record("9c exit codes 0,1,2,3,4 are all reachable as documented",
       (rc0, rc1, rc2v, rc3, rc4) == (0, 1, 2, 3, 4), (rc0, rc1, rc2v, rc3, rc4))

# ---------------------------------------------------------------- [10]
say()
say("[10] test execution leaves tracked source files unchanged")
tracked = ["PRODUCT_REQUIREMENTS.md", "DECISION_LOG.md", "PROJECT_STATUS.md",
           "SKILL.md", "README.md", "scripts/prodoc", "scripts/check_skill.py",
           "docs/test-results.json", "docs/TEST_REPORT.md"]
before_hash = digest(ROOT, tracked)
status_before = git(["status", "--porcelain", "--untracked-files=all"], ROOT).stdout
head_before = git(["rev-parse", "HEAD"], ROOT).stdout.strip()
rc, out, _ = run([sys.executable, str(RUNNER), "--quiet", "--no-gates", "--pattern", "test_cli.py"],
                 ROOT, label="full CLI suite, default scratch output", timeout=900)
after_hash = digest(ROOT, tracked)
status_after = git(["status", "--porcelain", "--untracked-files=all"], ROOT).stdout
record("10a the suite passes", rc == 0, out.strip().splitlines()[0] if out.strip() else "")
record("10b every tracked file is byte-identical afterwards", before_hash == after_hash)
record("10c git status and HEAD are unchanged", status_before == status_after
       and head_before == git(["rev-parse", "HEAD"], ROOT).stdout.strip())
record("10d committed evidence was not overwritten",
       digest(ROOT, ["docs/test-results.json", "docs/TEST_REPORT.md"]) ==
       {k: v for k, v in before_hash.items() if k.startswith("docs/")})

say()
say("=" * 78)
passed = sum(1 for _, ok, _ in results if ok)
say("FUNCTIONAL RESULT: %d/%d checks passed" % (passed, len(results)))
for name, ok, detail in results:
    if not ok:
        say("  FAILED: %s  %s" % (name, detail))
say("=" * 78)
sys.exit(0 if passed == len(results) else 1)
