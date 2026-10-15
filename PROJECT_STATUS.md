# Project Status

## Current Phase

In Progress

## Verified State

<!-- Machine-maintained. Refresh with `prodoc update`; do not hand-edit. -->
<!-- prodoc:verified:start -->
- **Branch:** main
- **Commit:** e8aafc64d15d57cce83f3b5982a11d4efff3b3d2
- **Working tree:** dirty
- **Verified at:** 2026-10-15T23:41:46Z
<!-- prodoc:verified:end -->

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
- [Implemented] Fourteen append-only architecture and policy decisions — `DECISION_LOG.md`
- [Implemented] Vendor-neutral portability: specification-only frontmatter, no vendor SDK, no per-client forks, enforced by tests — `SKILL.md`, `tests/test_skill_spec.py`
- [Implemented] Compatibility matrix for OpenCode, Codex, Claude Code, Cursor, GitHub Copilot, Gemini CLI and ChatGPT, labelled verified, unverified, unsupported or planned — `docs/COMPATIBILITY.md`
- [Implemented] Portable install path plus documented local adapters; no vendor plugin packaging, by design — `docs/COMPATIBILITY.md`
- [Planned] Publish v0.1.0 to GitHub after the release checklist is green
- [Planned] Verify the CLI on Windows and record the result here
- [Planned] Record a live skill activation in at least one client and publish it in the matrix

## Tests

| Suite | Command | Result | Evidence |
| --- | --- | --- | --- |
| cli, skill-spec (unit + integration, disposable Git repositories) | `python3 tests/run_tests.py` | Pass (100) | `docs/test-results.json`, `docs/TEST_REPORT.md` |
| Agent Skills specification | `python3 scripts/check_skill.py .` | Pass (0 errors) | `docs/test-results.json` (gate `skill-spec`) |
| Canonical documents | `python3 scripts/prodoc validate` | Pass | `docs/test-results.json` (gate `documents-validate`) |
| Consistency and secret scan | `python3 scripts/prodoc check` | Pass | `docs/test-results.json` (gate `documents-check`) |
| Windows | `python3 tests/run_tests.py` on Windows | Not run | - |
| Manual, OpenCode activation | install into `.opencode/skills/` and invoke | Not run | - |
| Manual, Codex activation | install into `.agents/skills/` and invoke `$prodoc-guard` | Not run | - |

## Known Defects

- The secret scan covers only the three canonical documents, so a credential
  pasted into any other file is not detected. Severity: low (documented scope,
  not a silent gap); see `D-0009`.
- `--quiet` suppresses output but not exit codes; a user who expects silence on
  failure is misreading the flag. Severity: cosmetic.
- The Windows path is implemented but untested, so it is listed as `Not run`
  rather than claimed. Severity: unknown until measured.

## Blockers

None. Publication is an authorization decision, not a technical one.

## Next Actions

1. Run `python3 tests/run_tests.py` on the commit that is tagged, and confirm the
   counts recorded above still match.
2. Work through `docs/RELEASE_CHECKLIST.md` and mark each item.
3. Refresh the verified-state block with `python3 scripts/prodoc update --phase Released`.
4. Commit the documentation, then tag and publish with explicit approval.

## Release Status

Not released. No version has been tagged, no package has been published, and no
public repository has been created. See `CHANGELOG.md` and
`docs/RELEASE_CHECKLIST.md`.
