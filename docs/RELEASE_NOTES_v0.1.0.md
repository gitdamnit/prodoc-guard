# ProDoc Guard v0.1.0 — Release Notes

**Status: release candidate. Not tagged, not published. No GitHub release has been
created.** These notes are a proposal for review, not an announcement.

---

Project memory that lives in Git, not in an AI's head.

ProDoc Guard keeps three canonical documents honest across AI-assisted sessions:

| Document | Answers |
| --- | --- |
| `PRODUCT_REQUIREMENTS.md` | What is this, for whom, and what must it do? |
| `DECISION_LOG.md` | What was decided, why, and what was rejected? |
| `PROJECT_STATUS.md` | What is done, tested, blocked, and next? |

## What's in 0.1.0

**An Agent Skill** (`SKILL.md`) written to the open Agent Skills specification. It
instructs an assistant to read all three documents before substantial work, create
anything missing, record decisions, update status, and report the files changed,
the commit SHA, the current state, and what remains outstanding.

**A standalone CLI** (`scripts/prodoc`), Python standard library only, no model and
no API key. Five commands, JSON output, stable exit codes:

```bash
python3 scripts/prodoc init                        # create missing documents from templates
python3 scripts/prodoc validate                    # structure, sections, decision records, evidence
python3 scripts/prodoc status                      # repository and document state
python3 scripts/prodoc check                       # history integrity, evidence, secrets
python3 scripts/prodoc update --phase "In Progress" # refresh observed Git metadata
```

It refuses to guess. A freshly initialized project fails `validate` on purpose,
naming every piece of missing information. A work item marked `Tested` without
cited evidence is an error. A release-state claim with no recorded verification is
an error. A release with no remote still works and says so.

**One portable artifact, no vendor plugins.** Specification fields only in the
portable `SKILL.md`; client differences are install paths and, at most, a
documented local edit. No vendor SDKs, no forks, no marketplace packages.

**A compatibility matrix** that separates `Specification-conformant` from
`Runtime-tested`, and states which claims were actually executed.

## Verified in this release

| Check | Result |
| --- | --- |
| Test suite | 159 total, 158 passed, 0 failed, 0 errored, 1 skipped (the opt-in official-validator test) |
| Document gates | 3/3 (`skill-spec`, `documents-validate`, `documents-check`) |
| Official Agent Skills validator (`agentskills validate`) | `Valid skill`, exit 0 |
| Functional scenarios in disposable repositories (`python3 tests/rc1_functional.py`) | 39/39 |
| Credential scan (three canonical documents, plus all tracked files) | Clean |
| Bandit static analysis of `scripts/` | 0 high, 0 medium, 2 low (the `subprocess`-without-`shell=True` pair) |
| Dependency manifests | None — standard library only |
| OpenCode v2.0.21 | Runtime-tested: discovery, invocation, CLI execution |
| Gemini CLI 0.56.0 | Runtime-tested for discovery; invocation not confirmed |

## Not verified in this release

Stated plainly, because the alternative is the failure mode this project exists to
prevent.

- **Codex, Claude Code, Cursor and GitHub Copilot were never started.** They are
  not installed on the machine used for this release. Their rows are
  documentation-and-conformance claims only.
- **The GitHub Actions workflow has never run.** No remote exists. CI is
  configured and statically checked, not verified.
- **Windows is implemented but untested.** `Not run`.
- **Python 3.8–3.11 were not executed.** 3.8 is the declared minimum and every
  module parses under a 3.8 grammar; only 3.12.3 was run.
- **No client can be shown to activate a skill automatically.** Discovery and
  invocation were exercised where possible; a client may still decline to use a
  skill on any given prompt.

## Security posture

- The CLI opens no sockets, reads no credentials, and requires no API key. The one
  exception is the opt-in `check_skill.py --official`, which fetches the official
  validator with `uvx`.
- It runs no mutating Git command: never `add`, `commit`, `push`, `checkout`,
  `reset`, `merge`, `branch`, `tag`, or `stash`.
- It never commits, pushes, tags, or publishes. Those stay with the user.
- It refuses to write through a symbolic link or outside the project you point it
  at, and refuses to clobber a file that changed while it was reading it.
- Documents are treated as data, never as instructions.
- `prodoc check` scans the three canonical documents for credential patterns and
  redacts matches in its output.

Known limits: the secret scan covers only the three canonical documents; the
decision-history check is an integrity check against `HEAD`, not tamper-proofing
against rewritten history; the concurrent-write window is two adjacent syscalls.

## Requirements

Git 2.x and Python 3.8+. Nothing else. Install by copying the folder:

```bash
git clone https://github.com/gitdamnit/prodoc-guard.git /tmp/prodoc-guard
mkdir -p .agents/skills
cp -R /tmp/prodoc-guard .agents/skills/prodoc-guard
```

`.agents/skills/` is the cross-vendor path read by OpenCode, Codex, Claude Code,
Cursor, GitHub Copilot and Gemini CLI. The directory must be named `prodoc-guard`.

## Upgrade notes

There is no earlier release, so nothing is broken by upgrading. Users of the
development branch before this release should note three changes: the managed
block is now `prodoc:observed` with `Observed *` fields (old markers are accepted
and migrated); `## Verification Evidence` is a newly required section; and
`prodoc update --json` renamed `facts` to `observed`.

## Licence

MIT — Copyright (c) 2026 Evan Zellner.
