# Compatibility

ProDoc Guard is built to be **platform-agnostic and vendor-neutral**. The core is
two things that no vendor owns:

1. A `SKILL.md` written to the open [Agent Skills specification](https://agentskills.io/specification).
2. `scripts/prodoc`, a standalone CLI with no model, no API key, and no
   vendor SDK.

Everything client-specific is limited to *where you copy the folder* and *how you
invoke it*. There is no per-client code path, no vendored plugin, and no
duplicated core.

Research date: **2026-10-15**. Sources are the vendors' own skill documentation,
linked per row. Vendor behaviour changes; re-check before relying on a row.

## What the status labels mean

| Label | Meaning |
| --- | --- |
| **Verified** | The client's current official documentation was read, its documented discovery paths and frontmatter rules are recorded below, and the single portable `SKILL.md` in this repository satisfies them — measured by `scripts/check_skill.py` (frontmatter keys, name/directory match, length limits, bundled-file references). This is a *documentation and conformance* verification. |
| **Unverified** | The client is listed as Agent Skills compatible, or its docs describe skills, but either the documentation was not read for this release or it does not document a discovery path for an externally authored folder. Format-compatible in principle; unproven here. |
| **Unsupported** | Known not to accept a standalone skill folder on that surface. A different distribution path is required. |
| **Planned** | No claim today. Listed so the gap is visible rather than implied. |

**No client was launched to test activation.** "Verified" does not mean a live
end-to-end activation test ran in that product, because no such test was executed
in this environment. Verified here means: the documented rules were followed and
the artifact conforms. What *was* executed is recorded in
[TEST_REPORT.md](TEST_REPORT.md) — the CLI, the CI path, and the specification
conformance checks all run without any client at all.

## Compatibility matrix

| Client | Status | Documented discovery paths | Invocation | What was checked |
| --- | --- | --- | --- | --- |
| **No agent at all** (manual, scripts, CI/CD) | **Verified** | n/a — operates on the working tree | `prodoc init\|validate\|status\|check\|update` | Exercised: 91 automated tests, all three gates green — `TEST_REPORT.md` |
| **OpenCode** | **Verified** | `.opencode/skills/`, `.claude/skills/`, `.agents/skills/`; globals `~/.config/opencode/skills/`, `~/.claude/skills/`, `~/.agents/skills/` | `skill` tool, or `/name` when declared in `metadata` | Paths and frontmatter rules read from the OpenCode Agent Skills page; conformance measured by `check_skill.py` |
| **OpenAI Codex** (CLI, IDE) | **Verified** | `$CWD/.agents/skills` up to `$REPO_ROOT/.agents/skills`, `~/.agents/skills`, `/etc/codex/skills` | `$prodoc-guard`, `/skills`, or implicit match | Paths read from *Build skills*; `name`/`description` requirement met; `agents/openai.yaml` supplied as an optional adapter |
| **Claude Code** | **Verified** | `.claude/skills/` (project, nested, enterprise, `--add-dir`); `~/.claude/skills/`; plugin `<plugin>/skills/` | `/prodoc-guard` (directory or `name` sets the command) | Paths read from *Extend Claude with skills*. Claude Code accepts every frontmatter field, and requires **spec-only fields** for claude.ai upload / Skills API / `package_skill.py` packaging — this skill uses spec-only fields, so it does not hard-error there |
| **Cursor** | **Verified** | `.agents/skills/`, `.cursor/skills/`; `~/.agents/skills/`, `~/.cursor/skills/`; also reads `.claude/skills/`, `.codex/skills/` and their user-level equivalents | `/` in Agent chat, or a Custom Mode | Paths and rules read from *Agent Skills*; `name` matches the parent folder as required |
| **GitHub Copilot** (VS Code, CLI, app, cloud agent) | **Verified** | `.github/skills/`, `.claude/skills/`, `.agents/skills/`; `~/.copilot/skills/`, `~/.claude/skills/`, `~/.agents/skills/` | `/prodoc-guard` slash command, or automatic by description | Paths read from *Use Agent Skills in VS Code*; constraints met — `name` ≤64 chars, lowercase/digits/hyphens, matches the parent directory, no namespace prefix; `description` ≤1024 |
| **Gemini CLI** | **Verified** | Workspace `.agents/skills/` or `.gemini/skills/`; user `~/.agents/skills/` or `~/.gemini/skills/` | `activate_skill` tool with an explicit consent prompt | Paths and the tier/precedence model read from *Agent Skills*. `.agents/skills/` is the portable alias. See the caveat below |
| **Any other Agent Skills client** | **Unverified** | Client-specific; most support `.agents/skills/<name>/SKILL.md` | Client-specific | The format is standard and the skill conforms, but no per-client rule was read. Clients listed on the ecosystem showcase but untested here include Junie, Goose, Amp, Letta, OpenHands, Mux, Roo Code, Factory, Kiro, TRAE, Snowflake Cortex Code, and others |
| **ChatGPT desktop app** | **Unverified** | Not documented for externally authored folders | `@` mention | The app has a Skills view for skills created in your projects, but its documentation does not state where an external skill folder is placed, so no path is claimed |
| **ChatGPT web** (Chat, Work) | **Unsupported** | Plugin-bundled skills only | Plugin installation | Standalone skill folders are not an installable unit there. See below |
| **Antigravity CLI** (Gemini CLI successor) | **Unverified** | Not documented in the sources read | Unknown | Gemini CLI documentation states it was replaced by Antigravity CLI for unpaid and Google One users on 2026-06-18 |
| **Plugin / marketplace packaging** (Cursor marketplace, ChatGPT plugins) | **Planned** | n/a | n/a | Cursor documents that repository-based skill distribution goes through a plugin with `.cursor-plugin/marketplace.json`; ChatGPT web requires a plugin. This project is not packaged as a plugin, by choice — see *Deliberate non-goals* |
| **Live activation verification per client** | **Planned** | n/a | n/a | Recording a real activation run per client, and publishing it in this file, is follow-up work |
| **Windows** | **Planned** | n/a | n/a | The CLI uses `os.replace` and no POSIX-only process behaviour, but the suite has only been run on Linux |

## The portable install path

Five of the six verified clients read `.agents/skills/`. That makes it the
practical, vendor-neutral default:

```
<project>/.agents/skills/prodoc-guard/SKILL.md     # shared with the team, via Git
~/.agents/skills/prodoc-guard/SKILL.md             # available in all your projects
```

The directory **must** be named `prodoc-guard`. Every client listed above requires
`name` to match the parent directory name, and several fail silently when it does
not. `scripts/check_skill.py` enforces it.

Where a client also reads its own path, prefer the portable one unless you need
the client-specific behaviour:

| Client | Portable path works? | Client-specific alternative it also reads |
| --- | --- | --- |
| OpenCode | yes | `.opencode/skills/`, `~/.config/opencode/skills/` |
| Codex | yes | `/etc/codex/skills` (admin), bundled system skills |
| Claude Code | yes (`.claude/skills/` is its native path) | `.claude/skills/`, `~/.claude/skills/`, enterprise and plugin locations |
| Cursor | yes | `.cursor/skills/`, `~/.cursor/skills/` |
| GitHub Copilot | yes | `.github/skills/`, `~/.copilot/skills/` |
| Gemini CLI | yes | `.gemini/skills/`, `~/.gemini/skills/` |

`.agents/skills/` is also how Claude Code, Cursor, and Copilot *interoperate*
with each other's folders, so a single copy can serve several products at once.

## Vendor extensions we deliberately do not use

Every client above accepts the specification's fields and then adds its own. The
portable `SKILL.md` uses **only** specification-defined fields — `name`,
`description`, `license`, `compatibility`, `metadata` — and therefore loads
everywhere without per-client branches.

| Client | Extra frontmatter fields available | Why we do not use them |
| --- | --- | --- |
| Claude Code | `disable-model-invocation`, `user-invocable`, `argument-hint`, `arguments`, `model`, `effort`, `context`, `agent`, `background`, `hooks`, `paths`, `shell`, `when_to_use`, `disallowed-tools` | Claude Code hard-errors if a non-spec field is present when packaging for claude.ai or the Skills API. Using one field would break that path for every user |
| Cursor | `paths`, `disable-model-invocation`, `icon`, `color` | Cursor-only presentation and scoping; `icon`/`color` are meaningless elsewhere |
| GitHub Copilot | `argument-hint`, `user-invocable`, `disable-model-invocation`, `context` | Copilot-specific invocation control; the default behaviour (auto-load plus slash command) is what this skill wants |
| Gemini CLI | none documented beyond the standard | — |
| OpenCode | `metadata["opencode/slash"]`, `metadata["opencode/autoinvoke"]` | Namespaced vendor keys in the portable file. If you want the OpenCode `/prodoc-guard` command, add one line to your local copy: `metadata: { opencode/slash: "true" }`. That is the whole adapter — see *Optional local adapters* |

This is the substance of "adapters only where necessary": the adapter is a line in
your local copy or a path you copy the folder to, never a fork of the skill.

## Optional local adapters

None of these are required, and none change the portable artifact.

| Adapter | Do this | Gains |
| --- | --- | --- |
| OpenCode slash command | add `opencode/slash: "true"` under `metadata` in your installed copy | `/prodoc-guard` in the TUI |
| Codex UI metadata | keep `agents/openai.yaml` (already shipped) | Display name, short description, default prompt in the skills list |
| Cursor Custom Mode | invoke the skill and press Option/Alt+Enter | Keeps the skill active for a whole session |
| Gemini CLI install | `gemini skills install <repo-url> --path . --consent` | Installs into the workspace or user tier, with consent acknowledged |
| Copilot-only scoping | add `paths:` to your copy if you want file-scoped surfacing | Not used here: this skill applies to any file in a project |
| Any CI system | run `python3 scripts/prodoc check` | No adapter needed; see below |

## Manual and CI/CD execution

The core does not need an agent, a client, or a model. This is the deployment
route that works everywhere and is the one this repository tests end to end.

```bash
# any machine with Git and Python 3.8+
python3 scripts/prodoc validate --json
python3 scripts/prodoc check --json      # exit 1 on inconsistency, missing evidence, secrets
python3 scripts/prodoc status
python3 scripts/prodoc update --phase "In Progress"
```

| Context | How | Notes |
| --- | --- | --- |
| Manual, before committing | run `validate` and `check` by hand | Exit codes are stable: 0 ok, 1 errors, 2 usage, 3 environment, 4 unsafe state |
| GitHub Actions | `uses: gitdamnit/prodoc-guard/.github/actions/prodoc-check@main` | Composite action, `contents: read`, never commits |
| Any other CI (GitLab, Jenkins, CircleCI, Buildkite, …) | run the `python3 scripts/prodoc check` line above | No plugin, no service, no network |
| Git hook | call `check` from `pre-commit` | Optional; keep it non-`--force` so it can only block, never write |
| Release gate | `docs/RELEASE_CHECKLIST.md` | Human checklist plus the same commands |

The CLI never commits, pushes, changes branches, or opens sockets, so wiring it
into CI cannot mutate a repository.

## ChatGPT, as a separate integration question

ChatGPT is **not** treated as an Agent Skills host for this project, and the core
does not depend on it.

| Surface | Position |
| --- | --- |
| ChatGPT web (Chat, Work) | **Unsupported** for a standalone skill folder. Skills there arrive bundled inside a plugin. Packaging into a plugin is *Planned*, not done |
| ChatGPT desktop app | **Unverified**. A Skills view exists for skills created in your projects; the documentation read did not specify a location for an externally authored folder |
| Codex (CLI, IDE, ChatGPT desktop) | **Verified** as described above. Codex is a separate product from ChatGPT's chat surfaces and has its own documented skill locations |

If a ChatGPT route matters to you, treat it as a new integration with its own
packaging and review, not as a capability this skill already has.

## Activation is not guaranteed, anywhere

No client promises that a skill will be used. GitHub Copilot's own documentation
puts it plainly: discovery "makes skills available to the model but does not
guarantee that it invokes a skill for every relevant prompt". Gemini CLI requires
an explicit consent prompt before a skill activates. Codex and OpenCode choose by
matching the `description`.

Therefore:

- This project never claims automatic activation in any environment.
- Invoke explicitly when it matters: `/prodoc-guard` (Claude Code, Cursor,
  Copilot, OpenCode with the adapter), `$prodoc-guard` (Codex), `@` (ChatGPT
  desktop).
- Run the checks yourself when they must run: `python3 scripts/prodoc check`.
  CI is the only activation guarantee, because CI runs commands, not judgements.

## Deliberate non-goals

- **No vendor plugins or marketplace packages.** No `.cursor-plugin/`, no ChatGPT
  plugin manifest, no Claude Code plugin wrapper. They would add per-vendor
  release surfaces for the same files.
- **No vendor SDKs or API calls.** The core is Git plus the standard library.
- **No vendor frontmatter.** One portable `SKILL.md`.
- **No per-client forks.** A client that needs an adapter gets an install
  instruction, not a copy of the implementation.
- **No databases, hosted services, or accounts.** Same reason: nothing to vendor.

## Known limitations

- **Structure is checked, not meaning.** Documents can pass every check and still
  describe the wrong system.
- **The secret scan covers the three canonical documents only.**
- **Windows** is implemented but `Not run`; treat it as unverified.
- **`.agents/skills/` is a convention, not a standard path.** It is supported by
  the clients above today; the specification itself does not mandate a location.
- **Vendor documentation moves.** Re-read the linked page before installing if
  behaviour matters. This file records what was true on 2026-10-15.

## Reporting a compatibility problem

Open an issue with the client and version, the exact path you installed to, the
command or prompt you used, and what happened. A failing case is worth more than a
passing one.
