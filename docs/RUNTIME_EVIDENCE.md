# Runtime Evidence

Actual skill discovery and invocation runs, with the commands and the observed
output. This file exists so that a `Runtime-tested` label in
[`COMPATIBILITY.md`](COMPATIBILITY.md) points at something a reviewer can check.

**Date:** 2026-10-15
**Skill under test:** `prodoc-guard` at commit `5e389a28e9e67a39620b48980d02bcc76b58b957`
**Install layout:** `cp` of the tracked files into `<project>/.agents/skills/prodoc-guard/`, the portable path
**Projects:** disposable Git repositories under `/tmp`, each with the three canonical documents initialized

Tool versions:

| Tool | Version |
| --- | --- |
| OpenCode | v2.0.21 |
| Gemini CLI | 0.56.0 |
| Git | 2.43.0 |
| Python | 3.12.3 |

## Summary

| Client | Discovery | Invocation | CLI execution |
| --- | --- | --- | --- |
| OpenCode | Verified by execution | Verified by execution | Verified by execution |
| Gemini CLI | Verified by execution | Attempted; not independently confirmed | Not attempted |
| OpenAI Codex | Not installed | Not tested | Not tested |
| Claude Code | Not installed | Not tested | Not tested |
| Cursor | Not installed | Not tested | Not tested |
| GitHub Copilot | Not installed | Not tested | Not tested |

## OpenCode — `Runtime-tested`

Command:

```bash
cd /tmp/opencode/rc1/agent/opencode-proj
opencode run --auto "Invoke the prodoc-guard skill in this project. Then run its CLI …"
```

Observed output (trimmed to the evidence):

```text
> build · <model>
→ Skill "prodoc-guard"
> build · <model>
$ python3 .agents/skills/prodoc-guard/scripts/prodoc status
prodoc status: OK
  WARN:   no Git remotes configured; remote writes are impossible
  repo:    /tmp/opencode/rc1/agent/opencode-proj
  git:     branch=main commit=0cfdf73 tree=clean
  remotes: none
  PRODUCT_REQUIREMENTS.md  present
  DECISION_LOG.md          present
  PROJECT_STATUS.md        present  phase=Planning
> build · <model>
- Skill: prodoc-guard
- Branch: main
- Commit: 0cfdf73
- Phase (PROJECT_STATUS.md): Planning
- Note: docs all present; no Git remote configured (local-only).
```

Why this is evidence of all three stages:

- **Discovery**: the skill was found from `.agents/skills/`, so it was offered to
  the agent in a session that started in a directory it had never seen before.
- **Invocation**: the client itself printed `Skill "prodoc-guard"` — that is the
  harness reporting a call to its native `skill` tool, not the model asserting that
  it read something.
- **CLI execution**: the reported branch, short commit (`0cfdf73`) and phase match
  the disposable repository's actual state, and the CLI output is reproduced
  verbatim above.
- **Boundaries**: the disposable project at HEAD `0cfdf73` was left clean, and the
  development repository's HEAD was unchanged.

## Gemini CLI — `Runtime-tested (discovery)`

### Discovery

Command:

```bash
cd /tmp/opencode/rc1/agent/gemini-proj
gemini --skip-trust skills list
```

Observed output (trimmed):

```text
Here are the available skills:

- **`antigravity-support`**: Help and setup instructions for Antigravity CLI.
- **`skill-creator`**: Guide for creating or updating Gemini CLI skills.
- … (built-in and user skills omitted) …
- **`prodoc-guard`**: Maintain canonical project documentation (`PRODUCT_REQUIREMENTS.md`, `DECISION_LOG.md`, `PROJECT_STATUS.md`) across AI workflows.
```

The skill was enumerated from its own `description`, from the workspace tier, in a
project Gemini CLI had not seen before.

Two notes for anyone reproducing this:

- The workspace must be trusted. Untrusted, Gemini reports
  `Skipping project agents due to untrusted folder` and finds nothing. `--skip-trust`
  trusts the workspace for the session only and does not write a trust setting.
- `gemini skills list` checks the auth configuration even though it calls no model.
  With a disposable `HOME` it refuses with
  `Please set an Auth method …`; the run above used the machine's existing auth.

### Invocation — attempted, not independently confirmed

Command:

```bash
gemini --skip-trust --approval-mode plan -p "Use the prodoc-guard skill. …"
```

Observed output (trimmed):

```text
Error executing tool activate_skill: Tool "activate_skill" not found. Did you mean one of: "write_file", "update_topic", "read_file"?
Skill Name: prodoc-guard
Current Phase: Planning
```

The model selected the skill and read the project's documentation, but activation
failed: `activate_skill` is not exposed in plan mode. A second attempt with `-y`
(yolo, all tools auto-approved) completed and reported
`prodoc-guard skill activated successfully`, but that line is the model's own
summary; the transcript does not show the tool result, and the facts it then
reported are also present in the project's own documents. It is therefore **not**
recorded as confirmed invocation.

An independent run should verify this by inspecting the `activate_skill` tool
result, for example with logging enabled, rather than by trusting the summary.

## Not tested

| Client | Reason |
| --- | --- |
| OpenAI Codex | Not installed on this machine (`codex` absent) |
| Claude Code | Not installed (`claude` absent) |
| Cursor | Not installed (`cursor`, `cursor-agent` absent) |
| GitHub Copilot | Not installed (`copilot` absent) |

No client was installed for this exercise, and no credentials were configured.

## Isolation and side effects

- The Gemini discovery attempt was first tried with a disposable `HOME`, which
  failed for lack of auth and is recorded above. The runs that succeeded used the
  machine's existing user configuration; no credentials or settings were created
  or edited.
- The file set of `~/.config/opencode` was compared before and after the OpenCode
  run: unchanged.
- The file set of `~/.gemini` gained only session artifacts under
  `~/.gemini/history/` and `~/.gemini/tmp/`. `settings.json` and
  `google_accounts.json` were neither read nor written.
- The development repository was not modified: HEAD was `5e389a2` before and after,
  with no tracked changes.
- One Gemini API call returned HTTP 503 (`This model is currently experiencing high
  demand`) and the CLI retried automatically. Recorded because it is the kind of
  transient failure a future run may see.

## Reproducing

```bash
BASE=/tmp/prodoc-runtime
mkdir -p "$BASE/proj" && cd "$BASE/proj"
git init -q -b main . && git config user.email t@e.invalid && git config user.name T
mkdir -p .agents/skills/prodoc-guard
git -C /path/to/prodoc-guard archive HEAD | tar -x -C .agents/skills/prodoc-guard
python3 .agents/skills/prodoc-guard/scripts/prodoc init --quiet
git add -A && git commit -qm "docs: initial"

# OpenCode
opencode run --auto "Invoke the prodoc-guard skill and run its CLI in this project."

# Gemini CLI
gemini --skip-trust skills list
```
