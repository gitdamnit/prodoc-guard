# Project Status

## Current Phase

In Progress

## Repository State

<!-- Machine-maintained by `prodoc update`. Do not hand-edit. -->
<!-- prodoc:observed:start -->
<!-- Observed from Git metadata only, by `prodoc update`. This block is not evidence that the implementation or its tests are correct; record that under `## Verification Evidence`. -->
- **Observed branch:** audit/corrections-p1-p2
- **Observed commit:** f1dc26668ca4af852c6bf36e0e1c42d5f5b5ce62
- **Observed working tree:** dirty
- **Observed at:** 2026-10-16T00:32:28Z
<!-- prodoc:observed:end -->

## Verification Evidence

Written by hand. One line per verification, with a commit identifier and an
artefact. The observed block above is not a substitute for anything here, and no
command writes entries in this section.

- **Verification:** commit `f1dc26668ca4af852c6bf36e0e1c42d5f5b5ce62` — full suite green (100 tests, 0 failures, 3/3 gates) — evidence `docs/test-results.json`
- **Verification:** commit `f1dc26668ca4af852c6bf36e0e1c42d5f5b5ce62` — `git archive` of HEAD extracted, every file hashing identically to its Git blob, and the extracted copy passed `check_skill.py` and `prodoc validate` — evidence `docs/TEST_REPORT.md`
- **Verification:** commit `f1dc26668ca4af852c6bf36e0e1c42d5f5b5ce62` — skill directory validated against the Agent Skills specification, 0 errors — evidence `docs/COMPATIBILITY.md`
- **Verification:** commit `f1dc26668ca4af852c6bf36e0e1c42d5f5b5ce62` — official reference validator (`agentskills validate`) reports "Valid skill", exit 0 — evidence `docs/COMPATIBILITY.md`

No client-side activation has been verified. No client has been launched, so no
`Runtime-tested` claim exists anywhere in this project.

## Completed Work

- [Implemented] Agent Skill with valid frontmatter, workflow steps and git safety rules — `SKILL.md`
- [Implemented] Offline CLI with `init`, `validate`, `status`, `check`, `update`, JSON output and stable exit codes — `scripts/prodoc`
- [Implemented] Commands run from a subdirectory resolve the canonical documents at the Git worktree root — `scripts/prodoc`
- [Implemented] Skill-directory validator for the Agent Skills specification — `scripts/check_skill.py`
- [Implemented] Bundled document templates whose placeholders fail validation until filled — `templates/PRODUCT_REQUIREMENTS.md`, `templates/DECISION_LOG.md`, `templates/PROJECT_STATUS.md`
- [Implemented] Reference material for status rules, the security model and Git workflow — `references/status-rules.md`, `references/security.md`, `references/github-workflow.md`
- [Implemented] Least-privilege composite pull-request check, plus CI that dogfoods it — `.github/actions/prodoc-check/action.yml`, `.github/workflows/ci.yml`
- [Implemented] Disposable-repository test suite and evidence generator — `tests/run_tests.py`
- [Tested] CLI, skill-specification and template-contract tests pass on this commit — `docs/test-results.json`
- [Implemented] Cross-platform installation, activation and limitation documentation — `README.md`, `docs/COMPATIBILITY.md`
- [Implemented] Twenty append-only architecture and policy decisions — `DECISION_LOG.md`
- [Implemented] Vendor-neutral portability: specification-only frontmatter, no vendor SDK, no per-client forks, enforced by tests — `SKILL.md`, `tests/test_skill_spec.py`
- [Implemented] Compatibility matrix for OpenCode, Codex, Claude Code, Cursor, GitHub Copilot, Gemini CLI and ChatGPT, labelled specification-conformant, runtime-tested, unverified, unsupported or planned — `docs/COMPATIBILITY.md`
- [Implemented] Decision-history integrity: detection of deletions, edits to existing records, and reordering, compared against HEAD — `scripts/prodoc`
- [Implemented] Separation of observed Git metadata from verified evidence, with a release-state evidence gate — `scripts/prodoc`, `templates/PROJECT_STATUS.md`
- [Implemented] Write boundaries: symlinked documents and paths outside the project are refused — `scripts/prodoc`
- [Implemented] Test reports write to an untracked scratch directory by default, with an explicit, non-silent path for refreshing committed evidence — `tests/run_tests.py`
- [Implemented] Official Agent Skills validation wired in as an opt-in flag, with the probe corrected to the real executable names — `scripts/check_skill.py`
- [Planned] Publish v0.1.0 to GitHub after the release checklist is green
- [Planned] Verify the CLI on Windows and record the result here
- [Planned] Record a live skill activation in at least one client and publish it in the matrix

## Tests

| Suite | Command | Result | Evidence |
| --- | --- | --- | --- |
| cli, skill-spec (unit + integration, disposable Git repositories) | `python3 tests/run_tests.py` | Pass (155) | `docs/test-results.json`, `docs/TEST_REPORT.md` |
| Agent Skills specification | `python3 scripts/check_skill.py .` | Pass (0 errors) | `docs/test-results.json` (gate `skill-spec`) |
| Canonical documents | `python3 scripts/prodoc validate` | Pass | `docs/test-results.json` (gate `documents-validate`) |
| Consistency and secret scan | `python3 scripts/prodoc check` | Pass | `docs/test-results.json` (gate `documents-check`) |
| Windows | `python3 tests/run_tests.py` on Windows | Not run | - |
| Manual, OpenCode activation | install into `.agents/skills/` and invoke | Not run | - |
| Manual, Codex activation | install into `.agents/skills/` and invoke `$prodoc-guard` | Not run | - |

## Known Defects

- The secret scan covers only the three canonical documents, so a credential
  pasted into any other file is not detected. Severity: low (documented scope,
  not a silent gap); see `D-0009`.
- The decision-history check cannot see a rewritten baseline: if an edit is
  committed, `HEAD` moves with it and the check has nothing to compare against.
  Severity: by design; immutability needs protected branches or signed commits,
  not a local tool. See `D-0015`.
- A concurrent writer that lands between the final hash check and the rename can
  still be overwritten. The window is two adjacent syscalls; closing it needs
  advisory locking, whose stuck-lock failure mode was judged worse. See `D-0017`.
- `--quiet` suppresses output but not exit codes; a user who expects silence on
  failure is misreading the flag. Severity: cosmetic.
- The Windows path is implemented but untested, so it is listed as `Not run`
  rather than claimed. Severity: unknown until measured.

## Blockers

None. Publication is an authorization decision, not a technical one.

## Next Actions

1. Work through `docs/RELEASE_CHECKLIST.md` and mark each item.
2. Run `python3 tests/run_tests.py --update-evidence --force` and `python3 scripts/prodoc update` on the commit to be published, and commit the result.
3. Tag and publish with explicit approval.

## Release Status

Not released. No version has been tagged, no package has been published, and no
public repository has been created. See `CHANGELOG.md` and
`docs/RELEASE_CHECKLIST.md`.
