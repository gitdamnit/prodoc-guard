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

### Notes

- Not yet released. No version has been tagged and no package has been published.
