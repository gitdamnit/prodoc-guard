# Product Requirements

## Project Identity

**Name:** ProDoc Guard
**Tagline:** Project memory that lives in Git, not in an AI's head.
**Skill identifier:** `prodoc-guard`
**CLI command:** `prodoc`
**Repository:** https://github.com/gitdamnit/prodoc-guard (target)
**Licence:** MIT
**Maintainer:** Evan Zellner

## Purpose

AI assistants lose project context between sessions. They forget architectural
decisions, restate requirements from memory, duplicate documentation across
files, and report work as complete or tested when nothing was verified.

Project memory currently lives in conversation history: ephemeral, invisible to
the team, and impossible to review. ProDoc Guard moves that memory into the only
place that persists and can be audited — the Git repository — and gives it a
fixed structure, so any assistant, on any day, in any product, can pick up the
project and tell the difference between what was planned, what was built, what
was tested, and what shipped.

The authoritative source of truth is the Git repository, not an assistant's
memory.

## Intended Users

| User | Goal | Assumed knowledge |
| --- | --- | --- |
| Individual developer working with AI assistants | Stop re-explaining the project every session | Comfortable with Git and a terminal |
| Team using multiple assistants across products | One shared, reviewable project memory | Uses pull requests and code review |
| Maintainer of an agent skill | Validate skill structure against the spec | Reads SKILL.md and reference material |
| Reviewer of an AI-assisted change | See what was claimed, and whether it was verified | Reads documentation, not necessarily the code |

## Functional Requirements

| ID | Requirement | Acceptance signal |
| --- | --- | --- |
| FR-1 | A `SKILL.md` valid against the Agent Skills specification ships in the repository | `scripts/check_skill.py` exits 0; `skills-ref validate` (when installed) exits 0 |
| FR-2 | Exactly three canonical documents are maintained: `PRODUCT_REQUIREMENTS.md`, `DECISION_LOG.md`, `PROJECT_STATUS.md` | The three files exist at the repository root and validate |
| FR-3 | Missing documents are created from bundled templates without overwriting existing files | `prodoc init` twice leaves content byte-identical and exits 0 |
| FR-4 | Document structure is validated against required sections | `prodoc validate` exits 1 with the missing section named |
| FR-5 | Template placeholders are reported as missing information | `prodoc validate` on a freshly initialized project exits 1 listing each placeholder |
| FR-6 | Decision history is append-only | `prodoc check` exits 1 when a committed decision id is missing from the working tree |
| FR-7 | Decisions are well formed: unique, ascending, dated, with alternatives and rationale | `prodoc validate` names the decision and field at fault |
| FR-8 | Unverifiable completion claims are rejected | A `[Tested]` item with no evidence fails; a `Pass` row with no evidence fails |
| FR-9 | Credentials in the canonical documents are detected and redacted | `prodoc check` exits 1 and prints only a redacted prefix of the match |
| FR-10 | Repository state is reported: root, branch, detached HEAD, commit, working tree, remotes | `prodoc status --json` returns all fields |
| FR-11 | The verified-state block is refreshed from real Git facts only | `prodoc update` writes branch, commit, working tree and timestamp; nothing else changes |
| FR-12 | The skill instructs an assistant to read all three documents before substantial work, and to report files, commit SHA, state and outstanding tasks | `SKILL.md` contains those steps |
| FR-13 | Remote availability is established before any claim about a remote | The skill requires observed evidence before reporting a push or release |
| FR-14 | Every command works with no model API key and no network access | Offline test run passes with networking unavailable |
| FR-15 | A reusable pull-request check exists for the canonical documents | Composite action runs `validate` and `check`; workflow passes in CI |
| FR-16 | The core is platform-agnostic and vendor-neutral: one portable `SKILL.md` using only specification fields, and one CLI with no vendor SDK | `SKILL.md` has no vendor-namespaced metadata; shipped scripts import the standard library only |
| FR-17 | A compatibility matrix distinguishes verified, unverified, unsupported and planned integrations across the supported clients | `docs/COMPATIBILITY.md` contains all four labels and names OpenCode, Codex, Claude Code, Cursor, GitHub Copilot, Gemini CLI and ChatGPT |
| FR-18 | Client-specific differences are handled by install instructions or documented local adapters, never by forking the core | No per-client code path exists; adapters are local copy edits, and a test asserts it |
| FR-19 | The tool runs without any agent, manually and in CI/CD | Every command runs from a shell; CI runs them, and the suite needs no client |

## Nonfunctional Requirements

| ID | Requirement | Target |
| --- | --- | --- |
| NFR-1 | No required third-party dependency | Python 3.8+ standard library only; no `pip install` |
| NFR-2 | Fully offline | Zero network calls from the CLI; no telemetry |
| NFR-3 | No hosted backend, database, subscription, or remote inference | None present anywhere in the project |
| NFR-4 | Documentation stays portable | Plain Markdown with fixed level-2 headings; no proprietary format |
| NFR-5 | The CLI never mutates Git state | No `add`, `commit`, `push`, `checkout`, `reset`, `merge`, `branch`, `tag`, `stash` |
| NFR-6 | Writes are safe under concurrency | `update` exits 4 when the file changed since it was read |
| NFR-7 | Read-only targets degrade cleanly | Writing to a read-only file exits 4 without attempting privilege escalation |
| NFR-8 | `SKILL.md` stays within progressive-disclosure budgets | Under 500 lines and under 5,000 tokens |
| NFR-9 | Machine-readable output is available for automation | Every command supports `--json` on stdout |
| NFR-10 | Exit codes are stable and documented | 0 ok, 1 errors, 2 usage, 3 environment, 4 unsafe state |
| NFR-11 | Test coverage is reproducible by a third party | `python3 tests/run_tests.py` regenerates `docs/test-results.json` and `docs/TEST_REPORT.md` |
| NFR-12 | No vendor SDK, plugin, or runtime dependency in the core | Import allowlist enforced by test: standard library only |
| NFR-13 | No claim of guaranteed skill activation in any environment | Every document states that clients may decline to invoke a skill; no wording asserts otherwise |
| NFR-14 | Installation is a copy, not a build or an install step | The portable path `.agents/skills/prodoc-guard/` is documented and requires no package manager |

## Scope and Exclusions

**In scope for v0.1.0**

- The Agent Skills `SKILL.md` and its bundled template, reference, and script files.
- The offline `prodoc` CLI: `init`, `validate`, `status`, `check`, `update`.
- The three canonical documents and their fixed structure.
- A skill-directory validator for the Agent Skills specification.
- An optional, least-privilege GitHub Action for pull-request checks.
- Cross-platform installation and activation documentation.

**Out of scope for v0.1.0**

- Any hosted service, database, account, or subscription.
- Any required third-party API, including model APIs.
- Automatic commit, push, merge, or publication: every write to a remote is a
  human decision.
- Enforcing documentation in repositories that have not opted in.
- Semantic analysis of prose beyond structure, evidence presence, and credential patterns.
- Any dependency on, integration with, or modification of other projects by the
  same maintainer.
- Vendor plugins, marketplace packages, or per-client releases of the core.
  Distribution is a folder copy plus, at most, a documented local adapter.

## Technical Constraints

- **Languages:** Python 3.8+ for the CLI and tests; Markdown for documents; YAML for the action and skill metadata.
- **Dependencies:** standard library only. PyYAML and the official `skills-ref`
  validator are used when present, never required.
- **Platforms:** Linux, macOS and Windows with CPython 3.8+ and Git 2.x on `PATH`.
- **Forbidden:** network calls from the CLI, model API keys, hosted backends,
  destructive Git operations, force-push.
- **Independent:** the project must not import, wrap, or modify Bludit Wizard,
  TRAVIS, Stranger Danger, Git That Shit, Checkpoint Orchestrator, or any other
  existing project.

## Acceptance Criteria

v0.1.0 is complete when all of the following hold on the tagged commit:

1. `scripts/check_skill.py` exits 0 for the repository root.
2. `prodoc validate` and `prodoc check` exit 0 at the repository root.
3. `python3 tests/run_tests.py` reports zero failures, writes
   `docs/test-results.json`, and the counts match `docs/TEST_REPORT.md`.
4. Every behaviour in FR-1 to FR-15 has at least one automated test.
5. `README.md` documents verified installation and activation for OpenCode and
   OpenAI Codex, and states plainly what is and is not supported in ChatGPT.
6. The repository contains no detected credentials in the canonical documents.
7. The GitHub Actions workflow passes on a pull request against the default branch.
8. The shipped scripts import only the standard library, asserted by an automated test.
9. `docs/COMPATIBILITY.md` names every supported client and labels each integration
   verified, unverified, unsupported, or planned, with no row claiming live
   activation testing.
10. No document claims guaranteed automatic activation in any product.

## Release Objectives

| Objective | Rationale |
| --- | --- |
| Ship a skill a developer can install in under five minutes | Value depends on actually being used |
| Prove honesty enforcement is real, not aspirational | Anti-fabrication is enforced by tests, not by prose |
| Keep the implementation small enough to audit in one sitting | The tool touches real repositories |
| Make the documents useful without any tooling | Markdown plus discipline is the floor, not the ceiling |
| Leave the release checklist green and reproducible by a stranger | Publication readiness must be demonstrated |
| Stay portable across providers as the ecosystem fragments | Project memory outlives whichever assistant is fashionable |
| Make the CLI useful with no assistant present at all | Manual and CI use is the only guaranteed execution path |
