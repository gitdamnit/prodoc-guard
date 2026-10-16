# ProDoc Guard

**Project memory that lives in Git, not in an AI's head.**

An open-source, **platform-agnostic** [Agent Skill](https://agentskills.io) that
keeps three canonical project documents present, consistent, and — most
importantly — honest, so that requirements, decisions and status survive between
AI sessions and remain reviewable by humans.

It is deliberately **vendor-neutral**: no provider plugins, no vendor SDKs, no
hosted service, no model API. The core is a specification-format `SKILL.md` plus
one Python script, so the same folder works in OpenCode, Codex, Claude Code,
Cursor, GitHub Copilot, Gemini CLI, and anything else that reads Agent Skills —
and usefully, in no agent at all. See the
[compatibility matrix](docs/COMPATIBILITY.md).

Maintained by **Evan Zellner**. Licensed under MIT. Not affiliated with, endorsed
by, or sponsored by OpenAI, Anthropic, Google, Microsoft, Anysphere, or any other
vendor. It does not claim or imply any vendor endorsement, approval, or
marketplace listing.

```
prodoc-guard/
├── SKILL.md                      # the Agent Skill
├── scripts/prodoc                # offline CLI (Python 3 stdlib only)
├── scripts/check_skill.py        # validates a skill directory against the spec
├── templates/                    # the three document templates
├── references/                   # status rules, security model, Git workflow
└── docs/                         # compatibility, test report, release checklist
```

## The problem

AI assistants lose project context between sessions. They forget why an
architecture was chosen, restate requirements from memory, duplicate
documentation across files, and report work as complete, tested, or shipped when
nothing was verified. Project memory that lives only in a chat transcript cannot
be reviewed, diffed, or handed to a colleague.

## The fix

Three canonical documents, at the repository root, versioned with the code:

| Document | Answers |
| --- | --- |
| `PRODUCT_REQUIREMENTS.md` | What is this, for whom, and what must it do? |
| `DECISION_LOG.md` | What was decided, why, and what was rejected? |
| `PROJECT_STATUS.md` | What is done, tested, blocked, and next? |

The skill instructs the assistant to read all three before substantial work and
to update them honestly. The CLI makes "honestly" checkable: a completion claim
without evidence fails the build, and a deleted decision record is an error.

## Requirements

- **Git** 2.x on `PATH` (the CLI works without a repository, but loses Git checks).
- **Python 3.8+**. No packages to install; the standard library is enough.
- No network access, no account, no model API key, no hosted service.

## Install

ProDoc Guard is one portable folder. Nothing is vendor-specific: the same files
work everywhere, and installing for one product is the same operation as
installing for another.

> **The install directory must be named `prodoc-guard`.** The specification
> requires the skill's `name` to match its parent directory name, every client
> below enforces it, and some fail silently when it is wrong.
> `scripts/check_skill.py` checks it for you.

### The portable path

`.agents/skills/` is the cross-vendor convention: OpenCode, Codex, Claude Code,
Cursor, GitHub Copilot, and Gemini CLI all read it. Install there and most
products pick it up from one copy.

```bash
git clone https://github.com/gitdamnit/prodoc-guard.git /tmp/prodoc-guard
mkdir -p .agents/skills
cp -R /tmp/prodoc-guard .agents/skills/prodoc-guard    # project-wide, committed to Git
# or: cp -R /tmp/prodoc-guard ~/.agents/skills/prodoc-guard   # all your projects
```

### Per-client paths

Each client also reads its own directory, and several read their competitors'.
Use the portable path unless a client needs something else.

| Client | Also reads | Invoke it with |
| --- | --- | --- |
| OpenCode | `.opencode/skills/`, `~/.config/opencode/skills/`, `.claude/skills/` | the `skill` tool, or `/prodoc-guard` after the optional adapter |
| OpenAI Codex | `.agents/skills` up the tree, `~/.agents/skills/`, `/etc/codex/skills` | `$prodoc-guard`, the `/skills` list, or an implicit match |
| Claude Code | `.claude/skills/`, `~/.claude/skills/` | `/prodoc-guard` (the directory name is the command) |
| Cursor | `.cursor/skills/`, `~/.cursor/skills/` | `/` in Agent chat, or a Custom Mode |
| GitHub Copilot | `.github/skills/`, `~/.copilot/skills/` | `/prodoc-guard`, or automatic by description |
| Gemini CLI | `.gemini/skills/`, `~/.gemini/skills/` | the `activate_skill` tool, with a consent prompt |

Examples:

```bash
cp -R /tmp/prodoc-guard .opencode/skills/prodoc-guard   # OpenCode-native
cp -R /tmp/prodoc-guard .claude/skills/prodoc-guard     # Claude Code-native
cp -R /tmp/prodoc-guard .github/skills/prodoc-guard     # Copilot-native
cp -R /tmp/prodoc-guard .cursor/skills/prodoc-guard     # Cursor-native

# Gemini CLI can install from a Git repository directly
gemini skills install https://github.com/gitdamnit/prodoc-guard.git --path . --consent
```

Codex additionally reads the optional `agents/openai.yaml` that ships with this
folder, which supplies a display name and default prompt.

### ChatGPT is a separate question

ChatGPT web is **not** an Agent Skills host for a standalone folder: skills there
arrive inside a plugin, and this project does not ship one. The ChatGPT desktop
app has a Skills view, but its documentation does not state where an externally
authored folder goes, so no path is claimed. See
[docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) for the full matrix.

### Other clients

Any client that reads `.agents/skills/<name>/SKILL.md` will pick the skill up. The
format is the open [Agent Skills specification](https://agentskills.io/specification),
and the three documents plus the CLI are useful even if no client supports skills
at all.

### Activation is never guaranteed

No client promises to use a skill. Copilot's own documentation says discovery
"makes skills available to the model but does not guarantee that it invokes a
skill for every relevant prompt"; Gemini CLI asks for consent before activating
one; Codex and OpenCode match on the `description`. Invoke the skill explicitly
when it matters, and run `python3 scripts/prodoc check` in CI when the check must
actually happen. See [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md).

## Use

### As a skill

Once installed, ask the assistant to work normally — or invoke it explicitly. On
substantial project work it reads the three documents, creates anything missing,
records decisions, updates status, and reports what changed.


### As a CLI

The CLI works without any assistant, and without a model API key.

```bash
# create the three documents from the templates (never overwrites anything)
python3 scripts/prodoc init

# check structure: required sections, decision records, evidence, placeholders
python3 scripts/prodoc validate

# report repository and document state
python3 scripts/prodoc status

# check consistency: append-only history, verified commit, claims, secrets
python3 scripts/prodoc check

# refresh the machine-maintained observed repository-state block (Git metadata only)
python3 scripts/prodoc update --phase "In Progress"
```

Add `--json` to any command for machine-readable output on stdout, and
`--repo PATH` to work on another project. Exit codes are stable: `0` ok, `1`
errors found, `2` usage error, `3` environment error, `4` unsafe state (read-only
target or concurrent modification).

A freshly initialized project fails `validate` **on purpose**: template
placeholders are missing information, and the CLI names every one.

Two things are kept apart on purpose. `prodoc update` records **observed** Git
metadata — branch, commit, tree state, timestamp — and says nothing about whether
anything works. What was actually checked goes in `## Verification Evidence`, by
hand, with a commit and an artefact:

```markdown
- **Verification:** commit `a1b2c3d` — full suite green (148 tests) — evidence `docs/test-results.json`
```

A release-state claim (phase `Released`, or a `[Deployed]`/`[Published]` item)
is rejected without at least one such entry, and `prodoc update --phase Released`
refuses to make that transition without one.

Install it on your `PATH` if you prefer a bare command:

```bash
install -m 755 scripts/prodoc ~/.local/bin/prodoc
prodoc status
```

### Run it anywhere: manual, hooks, and CI/CD

The core needs no agent and no model, so the same command works by hand, in a Git
hook, and in any CI system.

```bash
# manual, before you claim something is done
python3 scripts/prodoc check

# any CI: GitLab, Jenkins, CircleCI, Buildkite, GitHub Actions, ...
python3 scripts/prodoc validate --json && python3 scripts/prodoc check --json
```

GitHub Actions can use the bundled composite action:

```yaml
name: docs
on: [pull_request]
permissions:
  contents: read
jobs:
  prodoc:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: gitdamnit/prodoc-guard/.github/actions/prodoc-check@main
```

The composite action needs only `contents: read` and never commits or modifies
your repository. Because `check` exits `1` on a problem, CI is the one place where
the documentation rules are actually enforced rather than hoped for.

An optional `pre-commit` hook, if you want the same gate locally:

```bash
cat > .git/hooks/pre-commit <<'EOF'
#!/bin/sh
python3 scripts/prodoc check || exit 1
EOF
chmod +x .git/hooks/pre-commit
```

## What it will not do

- It does not commit, push, merge, tag, or release anything. Ever.
- It does not change branches, and it does not force-push.
- It does not call the network. No telemetry, no update checks.
- It does not require an account, subscription, or model API.
- It does not overwrite existing documents or uncommitted changes.
- It does not ship vendor plugins, vendor SDKs, or per-client forks of the core.
- It does not write through symbolic links, or outside the project you point it at.
- It does not describe observed Git metadata as verification of anything.
- It does not claim that any client will activate it automatically.

Read [references/security.md](references/security.md) for the full model, and
[SECURITY.md](SECURITY.md) for how to report a vulnerability.

## Test evidence

```bash
python3 tests/run_tests.py                      # results to test-output/ (untracked)
python3 tests/run_tests.py --pattern test_cli.py  # a subset
```

Every test runs against a disposable Git repository with an isolated `HOME`, so
verifying the project does not modify it. Results go to `test-output/`, which is
gitignored; use `--output DIR` to put them elsewhere.

The committed evidence cited from `PROJECT_STATUS.md` is refreshed explicitly,
and never overwritten silently:

```bash
python3 tests/run_tests.py --update-evidence            # refuses: evidence exists
python3 tests/run_tests.py --update-evidence --force    # replaces docs/ evidence
```

The current state of [`docs/test-results.json`](docs/test-results.json) and
[`docs/TEST_REPORT.md`](docs/TEST_REPORT.md) is the honest answer to "what is
tested?", and it is refreshed deliberately rather than as a side effect of running
the suite.

## Documentation

| Document | Contents |
| --- | --- |
| [SKILL.md](SKILL.md) | The skill instructions |
| [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) | Compatibility matrix: specification-conformant, runtime-tested, unverified, unsupported and planned integrations |
| [references/status-rules.md](references/status-rules.md) | Status vocabulary, evidence rules, anti-patterns |
| [references/security.md](references/security.md) | Threat model and safety guarantees |
| [references/github-workflow.md](references/github-workflow.md) | Git, remote, PR and release mechanics |
| [CHANGELOG.md](CHANGELOG.md) | Release history |
| [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md) | What must be true before publishing |
| [PRODUCT_REQUIREMENTS.md](PRODUCT_REQUIREMENTS.md) | This project's own requirements |
| [DECISION_LOG.md](DECISION_LOG.md) | This project's own decisions |
| [PROJECT_STATUS.md](PROJECT_STATUS.md) | This project's own status |

## License

MIT — see [LICENSE](LICENSE). Copyright (c) 2026 Evan Zellner.
