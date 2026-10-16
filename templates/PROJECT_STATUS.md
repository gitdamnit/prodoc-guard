# Project Status

<!--
Canonical document 3 of 3. This file is the answer to "where are we, really?".

Two different things live here, and they must not be confused:

  * `## Repository State` is machine-maintained by `prodoc update`. It records
    Git metadata the tool observed. It is NOT evidence that anything works.
  * `## Verification Evidence` is written by a human. It records what was
    actually verified, at which commit, with which artefact as proof.

Rules:
  * State only what is true right now. Planned work is not completed work.
  * Cite evidence for anything claimed as Implemented, Tested, Deployed or Published.
  * Never invent test results. "Not run" is a valid and honest result.
-->

## Current Phase

Planning

## Repository State

<!-- Machine-maintained by `prodoc update`. Do not hand-edit. -->
<!-- prodoc:observed:start -->
<!-- Observed from Git metadata only, by `prodoc update`. This block is not evidence that the implementation or its tests are correct; record that under `## Verification Evidence`. -->
- **Observed branch:** -
- **Observed commit:** -
- **Observed working tree:** unknown
- **Observed at:** -
<!-- prodoc:observed:end -->

## Verification Evidence

<!--
prodoc:todo: record what was actually verified, at which commit, with what artefact
-->

Written by a human, one line per verification. A commit identifier and an
artefact are both required; a release-state phase or a `Deployed`/`Published`
work item is rejected without at least one entry here.

```markdown
- **Verification:** commit `a1b2c3d` — full suite green (100 tests) — evidence `docs/test-results.json`
- **Verification:** commit `a1b2c3d` — installed into `.agents/skills/` and invoked by hand — evidence `docs/COMPATIBILITY.md`
```

_No verification recorded yet._

## Completed Work

<!-- prodoc:todo: replace the example below with the real, evidence-backed work items -->

Mark each item with a state, and cite evidence for anything past `Planned`:

```markdown
- [Implemented] Added the offline validator — `scripts/prodoc`
- [Tested] Validator suite green, 100 cases — `docs/TEST_REPORT.md`
- [Planned] Publish v0.1.0 to GitHub
```

Allowed states: `Planned`, `In Progress`, `Implemented`, `Tested`, `Deployed`, `Published`, `Blocked`, `Removed`.

_No work recorded yet._

## Tests

<!-- prodoc:todo: record the suites that were actually executed on the commit above -->

```markdown
| Suite | Command | Result | Evidence |
| --- | --- | --- | --- |
| unit | `python3 -m unittest` | Pass (100) | `docs/test-results.json` |
| manual | smoke test in a scratch repo | Not run | - |
```

| Suite | Command | Result | Evidence |
| --- | --- | --- | --- |

## Known Defects

<!-- prodoc:todo: defects you know about, with severity and reproduction. "None known" is a valid entry. -->

None known.

## Blockers

<!-- prodoc:todo: external things stopping progress, who owns them, and what unblocks them -->

None.

## Next Actions

<!-- prodoc:todo: the next concrete actions, in order, each small enough to finish -->

1.

## Release Status

<!-- prodoc:todo: version, release state, and what is still required before publication -->

Not released.
