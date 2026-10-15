# Status Rules

Reference for `PROJECT_STATUS.md`, `DECISION_LOG.md`, and the evidence rules that
`prodoc validate` and `prodoc check` enforce. Load this when a status entry is
ambiguous, when you are unsure whether work may be claimed, or when a check fails.

## Contents

- [Authority](#authority)
- [Phase vocabulary](#phase-vocabulary)
- [Work state vocabulary](#work-state-vocabulary)
- [Evidence rules](#evidence-rules)
- [Tests table](#tests-table)
- [Decision records](#decision-records)
- [Update cadence](#update-cadence)
- [Anti-patterns](#anti-patterns)

## Authority

The Git repository is the source of truth. In order:

1. The user's current request.
2. `PRODUCT_REQUIREMENTS.md` — what the project must do.
3. `DECISION_LOG.md` — the choices already made, and the reasons.
4. `PROJECT_STATUS.md` — where the work stands.
5. Conversation history, model memory, summaries and assumptions — least authority.

If documents disagree with each other, the requirements win for *intent* and the
repository's actual state wins for *fact*. Report the conflict; do not paper over
it.

## Phase vocabulary

`## Current Phase` holds exactly one of these values. `prodoc update --phase`
accepts only this list.

| Phase | Means |
| --- | --- |
| `Planning` | Requirements are being written; no usable implementation yet |
| `Prototype` | Something runs, but interfaces and behaviour are expected to change |
| `In Progress` | Committed to a shape; features being implemented and tested |
| `Paused` | Intentionally not being worked on right now |
| `Blocked` | Cannot proceed; see `## Blockers` |
| `Maintenance` | Feature-complete for now; fixes and upkeep only |
| `Released` | Published; changes go through the release process |
| `Archived` | No further development expected |

Phase is a summary, not a promise. It must not contradict the work items.

## Work state vocabulary

Every line in `## Completed Work` starts with exactly one state in brackets:

```markdown
- [Implemented] Added the offline validator — `scripts/prodoc`
- [Tested] Validator suite green, 24 cases — `docs/TEST_REPORT.md`
- [Deployed] Internal preview at https://example.invalid/preview
- [Published] v0.1.0 tagged and released — `CHANGELOG.md`
```

| State | May be claimed when | Evidence required |
| --- | --- | --- |
| `Planned` | It is agreed work, not started | no |
| `In Progress` | Someone is actively working on it | no |
| `Implemented` | The code exists in the repository | yes |
| `Tested` | Tests were actually executed and their outcome is recorded | yes |
| `Deployed` | It runs in a real environment reachable by others | yes |
| `Published` | It is released or publicly available | yes |
| `Blocked` | Work stopped; the blocker is listed in `## Blockers` | no |
| `Removed` | It existed and was deliberately deleted | no |

States are not a ladder you may skip upward by assumption: `Implemented` does not
imply `Tested`. Nothing implies `Deployed` or `Published`.

## Evidence rules

Accepted evidence, on the same line as the claim:

| Kind | Example | Notes |
| --- | --- | --- |
| Repository path | `` `src/parser.py` `` | Must exist in the working tree |
| Test report | `` `docs/TEST_REPORT.md` `` | Preferred for `Tested` |
| Commit SHA | `a1b2c3d` | 7–40 hex characters |
| URL | `https://example.invalid/build/42` | A claim of a URL is not proof it was fetched |
| Version tag | `` `v0.1.0` `` | Tag must exist for `Published` |

Not evidence: "it works", "should be fine", a summary written by the assistant, a
plan, a TODO comment, or the absence of an error message.

When you cannot produce evidence but the user needs the item recorded, write the
claim with an explicit marker instead of implying verification:

```markdown
- [Implemented] Refactored the parser — reported by user, not independently verified
```

## Tests table

`## Tests` contains a four-column table. `prodoc validate` fails on a `Pass`,
`Fail`, or `Partial` row without evidence.

```markdown
| Suite | Command | Result | Evidence |
| --- | --- | --- | --- |
| unit | `python3 -m unittest discover -s tests` | Pass (31) | `docs/test-results.json` |
| integration | `python3 tests/run_integration.py` | Fail (2) | `docs/test-results.json` |
| manual | fresh-eyes install in a scratch repo | Not run | - |
```

Rules:

- Report the command that was actually run, so it can be re-run.
- Report counts when you have them. "Pass" alone invites optimism.
- A failing suite stays in the table. Deleting failures is fabrication.
- `Not run`, `N/A`, and `Partial` are legitimate results and need no evidence.

## Decision records

Append-only. `prodoc check` compares the working tree with `HEAD` and fails if a
decision id that exists at `HEAD` has disappeared.

```markdown
### D-0007 — Store the canonical documents as Markdown, not YAML

- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** Documents must be readable by humans in Git hosting UIs and diffed meaningfully.
- **Alternatives Considered:** YAML (rejected: hostile diffs and poor prose rendering); SQLite (rejected: binary, breaks review); JSON (rejected: noisy diffs, escaping).
- **Decision:** Keep the three documents as Markdown with fixed headings.
- **Rationale:** Reviewers read and edit them directly; every tool in the ecosystem renders them.
- **Consequences:** Structure is enforced by heading conventions rather than a schema.
- **Supersedes:** None
```

Rules:

- One decision per record. Split compound decisions.
- Record decisions when they are *made*, not when they are implemented.
- Change your mind by appending `D-00NN` with `Status: Accepted` and updating the
  old record's status to `Superseded by D-00NN`. Never delete.
- A decision with no rejected alternatives usually means the alternatives were not
  considered. Say so explicitly if there genuinely was no choice.
- Typo fixes to a record are acceptable. Rewriting its substance is not.

## Update cadence

| Event | Update |
| --- | --- |
| Session start on a project | Read all three documents; `prodoc status` |
| Decision made | Append to `DECISION_LOG.md` |
| Requirement changed | Edit `PRODUCT_REQUIREMENTS.md`; log the decision |
| Code committed or saved | `prodoc update`; move the item to `Implemented` |
| Tests executed | Record the row in `## Tests` with evidence |
| Blocked | Add to `## Blockers`; set phase if the whole project is blocked |
| Deployed or released | `prodoc update --phase`; move the item to `Deployed`/`Published` |
| Before reporting to the user | `prodoc validate` and `prodoc check` |

## Anti-patterns

| Anti-pattern | Why it hurts | Instead |
| --- | --- | --- |
| "All tests pass" with no evidence | Cannot be re-checked; hides real failures | Cite the report and the count |
| Marking work `Tested` because it was written carefully | Untested code enters the record as verified | Run the tests, or write `Implemented` |
| Deleting a decision that no longer applies | Erases why the project is shaped this way | Append a superseding record |
| Editing `## Completed Work` to hide a regression | The record becomes fiction | Add `[Removed]` or a defect entry |
| Duplicating the same content in two documents | The copies drift and disagree | One home per fact; link to it |
| Recording a commit SHA that does not exist | Users cannot trace the state | Run `prodoc update` to record real facts |
| Reporting a push that was never verified | The user believes remote state changed | Show the command output, or say it was not pushed |
