# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and
this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `SKILL.md`, valid against the Agent Skills specification, describing the
  read-record-update-report workflow and the git safety rules.
- `scripts/prodoc`: an offline CLI with `init`, `validate`, `status`, `check` and
  `update`, JSON output on every command, and stable exit codes.
- `scripts/check_skill.py`: validates a skill directory against the specification,
  using the optional official `skills-ref` validator when it is installed.
- Templates for the three canonical documents, with `prodoc:todo` placeholders
  that `validate` reports as missing information.
- Reference material: `references/status-rules.md`, `references/security.md`,
  `references/github-workflow.md`.
- A least-privilege composite GitHub Action for pull-request document checks.
- A test suite of disposable-repository tests and a runner that writes
  `docs/test-results.json` and `docs/TEST_REPORT.md`.
- A compatibility matrix covering OpenCode, OpenAI Codex, Claude Code, Cursor,
  GitHub Copilot, Gemini CLI, ChatGPT and other Agent Skills clients, with
  verified, unverified, unsupported and planned states, and an explicit
  definition of what "verified" means here.
- The portable install path `.agents/skills/prodoc-guard/`, shared by the
  verified clients, plus per-client alternatives and optional local adapters.

### Fixed (independent audit, commit f1dc266)

- **P1 Decision history integrity.** `prodoc check` compared decision ID sets, so
  editing a record in place was invisible. It now compares a whitespace-normalized
  digest per record and reports an edit (`log.modified`, naming the changed
  fields), a deletion (`log.append_only`), and a reordering (`log.reordered`). A
  `Status` change is a warning, because superseding is intended. The guarantee is
  documented as an integrity check against HEAD, not tamper-proofing.
- **P1 Verified-state semantics.** `prodoc update` observed Git metadata under the
  word "verified". The block is now `prodoc:observed` with `Observed *` fields and
  a caveat, the section is `## Repository State`, and a new required
  `## Verification Evidence` section holds hand-written entries with a commit and
  an artefact. Release-state claims need one, and `update --phase Released`
  refuses without one. Old markers and headings are accepted, reported as
  deprecated, and migrated.
- **P2 Filesystem safety.** Writes are refused (exit 4) to a symbolic link or
  outside the selected project; `init` treats a symlinked document as present; the
  Git-root redirect never crosses a repository boundary. The write sequence now
  hashes twice (before writing and before the rename), fsyncs, and re-reads to
  confirm, with the residual window documented.
- **P2 Test evidence.** `tests/run_tests.py` no longer rewrites tracked files by
  default: results go to the untracked `test-output/`. Refreshing
  `docs/test-results.json` and `docs/TEST_REPORT.md` needs
  `--update-evidence --force`, and the runner refuses otherwise. Also fixed a
  self-invocation recursion in the new runner tests that made a full run take over
  twelve minutes.
- **P2 Compatibility labels.** `Verified` conflated conformance with testing. The
  matrix now distinguishes `Specification-conformant` from `Runtime-tested`, states
  that no client was launched, and a test fails any client row claiming
  `Runtime-tested` without a recorded run.

### Changed

- `prodoc update --json` renames `facts` to `observed`, and its keys to
  `observed branch`, `observed commit`, `observed working tree`, `observed at`.
- `## Verification Evidence` is a newly required section for `PROJECT_STATUS.md`;
  documents without it fail `validate` until it is added.
- The portable `SKILL.md` uses only specification-defined frontmatter fields. The
  OpenCode `/prodoc-guard` slash command is no longer enabled by default; it is a
  documented one-line local adapter. This keeps claude.ai and Skills API packaging
  working, which rejects non-specification fields.
- `docs/COMPATIBILITY.md` was rewritten from a per-product install guide into a
  compatibility matrix with explicit evidence per client.

### Notes

- Not yet released. No version has been tagged and no package has been published.
- No vendor plugins, per-client forks, or vendor SDKs are shipped, by design.
- No client was launched to verify skill activation; matrix rows that say
  `Verified` describe documented paths and measured conformance.
