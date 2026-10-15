# ProDoc Guard

**Project memory that lives in Git, not in an AI's head.**

An open-source [Agent Skill](https://agentskills.io) that keeps three canonical
project documents present, consistent, and — most importantly — honest, so that
requirements, decisions and status survive between AI sessions and remain
reviewable by humans.

Maintained by **Evan Zellner**. Licensed under MIT. Not affiliated with, endorsed
by, or sponsored by OpenAI, Anthropic, or any other vendor. It does not claim or
imply any vendor endorsement, approval, or marketplace listing.

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

Pick the location for the product you use. Install into a project to share it
with your team, or into your home directory to use it everywhere.

> **The install directory must be named `prodoc-guard`.** The specification
> requires the skill's `name` to match its parent directory name, and
> `scripts/check_skill.py` enforces it. Cloning into a differently named folder
> makes the skill invalid.

### OpenCode

OpenCode discovers skills from several locations, walking up from the working
directory to the Git worktree root:

| Scope | Path |
| --- | --- |
| Project | `.opencode/skills/prodoc-guard/SKILL.md` |
| Project (Claude-compatible) | `.claude/skills/prodoc-guard/SKILL.md` |
| Project (agent-compatible) | `.agents/skills/prodoc-guard/SKILL.md` |
| Global | `~/.config/opencode/skills/prodoc-guard/SKILL.md` |
| Global (Claude-compatible) | `~/.claude/skills/prodoc-guard/SKILL.md` |
| Global (agent-compatible) | `~/.agents/skills/prodoc-guard/SKILL.md` |

```bash
git clone https://github.com/gitdamnit/prodoc-guard.git /tmp/prodoc-guard
mkdir -p .opencode/skills
cp -R /tmp/prodoc-guard .opencode/skills/prodoc-guard
```

OpenCode loads skills on demand through its native `skill` tool. The skill
declares `metadata.opencode/slash: "true"`, so it is also available as the
`/prodoc-guard` command in the TUI. Activate it by asking a question that matches
its description, or invoke it directly.

### OpenAI Codex

Codex scans `.agents/skills` from the working directory up to the repository
root, plus a set of user and admin locations:

| Scope | Path |
| --- | --- |
| Repository | `$REPO_ROOT/.agents/skills/prodoc-guard/SKILL.md` |
| User | `~/.agents/skills/prodoc-guard/SKILL.md` |
| Admin (machine-wide) | `/etc/codex/skills/prodoc-guard/SKILL.md` |

```bash
mkdir -p .agents/skills
cp -R /tmp/prodoc-guard .agents/skills/prodoc-guard
```

Invoke explicitly with `$prodoc-guard` or from the `/skills` list, or let it
trigger implicitly from its description. Codex reads `agents/openai.yaml`, which
supplies the display name and default prompt. Restart Codex if a newly installed
skill does not appear.

### ChatGPT

**Standalone skills are not installable in ChatGPT on the web.** ChatGPT Chat and
Work can use skills that arrive inside a plugin, and the ChatGPT desktop app has a
Skills view for skills created in your projects. There is no documented
user-facing mechanism for installing an arbitrary skill folder from a Git
repository into ChatGPT on the web, so this project does not claim one. See
[docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) for exactly what is verified, what
is documented by the vendor, and what remains unknown.

### Other Agent Skills clients

Any client that reads `.agents/skills/<name>/SKILL.md` or
`~/.agents/skills/<name>/SKILL.md` will pick the skill up. The format is the open
[Agent Skills specification](https://agentskills.io/specification); the documents
and CLI are useful even if no client supports skills at all.

## Use

### As a skill

Once installed, ask the assistant to work normally. On substantial project work
it reads the three documents, creates anything missing, records decisions,
updates status, and reports what changed.

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

# refresh the machine-maintained verified-state block
python3 scripts/prodoc update --phase "In Progress"
```

Add `--json` to any command for machine-readable output on stdout, and
`--repo PATH` to work on another project. Exit codes are stable: `0` ok, `1`
errors found, `2` usage error, `3` environment error, `4` unsafe state (read-only
target or concurrent modification).

A freshly initialized project fails `validate` **on purpose**: template
placeholders are missing information, and the CLI names every one.

Install it on your `PATH` if you prefer a bare command:

```bash
install -m 755 scripts/prodoc ~/.local/bin/prodoc
prodoc status
```

### Optional: check documents in pull requests

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
your repository.

## What it will not do

- It does not commit, push, merge, tag, or release anything. Ever.
- It does not change branches, and it does not force-push.
- It does not call the network. No telemetry, no update checks.
- It does not require an account, subscription, or model API.
- It does not overwrite existing documents or uncommitted changes.

Read [references/security.md](references/security.md) for the full model, and
[SECURITY.md](SECURITY.md) for how to report a vulnerability.

## Test evidence

```bash
python3 tests/run_tests.py
```

This runs every test against a disposable Git repository with an isolated `HOME`,
then runs the document gates and writes:

- [`docs/test-results.json`](docs/test-results.json) — machine-readable results
- [`docs/TEST_REPORT.md`](docs/TEST_REPORT.md) — human-readable evidence

The current state of both files is the honest answer to "what is tested?".

## Documentation

| Document | Contents |
| --- | --- |
| [SKILL.md](SKILL.md) | The skill instructions |
| [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) | Verified per-product support, and documented gaps |
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
