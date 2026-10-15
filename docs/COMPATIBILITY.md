# Compatibility

What is verified, what is documented by the vendor but not verified here, and
what is unknown. Research date: **2026-10-15**.

Sources consulted:

- Agent Skills specification — <https://agentskills.io/specification>
- Agent Skills client showcase — <https://agentskills.io/clients>
- OpenAI, *Build skills* — <https://developers.openai.com/codex/skills>
- OpenAI `skills` repository, `skill-creator` — <https://github.com/openai/skills>
- OpenCode, *Agent Skills* — <https://opencode.ai/docs/skills/>

## Status of each environment

| Environment | Discovery | Invocation | Status |
| --- | --- | --- | --- |
| OpenCode | `.opencode/skills/`, `.claude/skills/`, `.agents/skills/`, and the global equivalents | `skill` tool; `/prodoc-guard` via `metadata.opencode/slash` | **Verified** against the documented paths and frontmatter rules |
| OpenAI Codex (CLI, IDE) | `$CWD/.agents/skills` up to `$REPO_ROOT/.agents/skills`, `~/.agents/skills`, `/etc/codex/skills` | `$prodoc-guard`, `/skills`, or implicit match | **Verified** against the documented paths; `agents/openai.yaml` supplied for UI metadata |
| ChatGPT desktop app | Skills created in your projects; a Skills view in the sidebar | `@` mention | **Partially documented.** Standalone skills are documented as available in the desktop app; the exact placement of an external folder is not documented, so no path is claimed here |
| ChatGPT web (Chat, Work) | Skills bundled inside a **plugin** | Plugin installation | **Not supported for standalone skills.** Use the [plugin](https://developers.openai.com/plugins/build/plugins) route, which this project does not ship |
| Other Agent Skills clients | `.agents/skills/<name>/SKILL.md` or the documented client path | Client-specific | **Format-compatible.** Not tested per client |
| No client at all | — | — | The three documents and `scripts/prodoc` are useful with no agent at all |

### Why ChatGPT is called out

Installing a skill in OpenCode does **not** make it available in ChatGPT, and the
reverse is also true. Each product has its own discovery paths and its own
invocation mechanism. Where a mechanism is not documented by the vendor, this
project says so rather than inventing one. Skill discovery and explicit
activation therefore have to be documented per environment, as the tables above
do.

### Discovery is not invocation

Even in an environment where a skill is discovered, the assistant may decline to
use it: models choose skills by matching the `description` against the task. Write
tasks that clearly involve project documentation, status, or decisions, or invoke
the skill explicitly (`$prodoc-guard`, `/prodoc-guard`, `@`). No skill can
guarantee activation in every conversation; the CLI exists so the checks can be
run regardless.

## Verification performed

| Check | Result |
| --- | --- |
| `scripts/check_skill.py .` on this repository | Pass — 0 errors |
| Frontmatter fields restricted to specification-defined keys | Pass |
| `name` matches the directory, matches `^[a-z0-9]+(-[a-z0-9]+)*$` | Pass |
| `description` within 1024 characters and written as "what + when to use" | Pass |
| `compatibility` within 500 characters | Pass |
| `SKILL.md` under 500 lines, body under 5000 tokens | Pass |
| Every bundled-file reference from `SKILL.md` resolves | Pass |

The official `skills-ref` validator from
<https://github.com/agentskills/agentskills> is run by `scripts/check_skill.py`
when it is installed. It is not a dependency, so results here do not depend on it.

## Deliberate deviations, and why

### 1. `templates/` instead of `assets/`

The specification recommends `assets/` for templates and explicitly allows
"any additional files or directories". This project bundles the three document
skeletons in a top-level `templates/` directory because they are file content to
be copied, not documentation to be read into context alongside `references/`.
Recorded as `D-0007` in `DECISION_LOG.md`.

### 2. Optional frontmatter fields are used

Codex's skill-authoring guidance says to include only `name` and `description`.
The Agent Skills specification defines `license`, `compatibility` and `metadata`
as well, and OpenCode reads product-specific behaviour from `metadata`
(`opencode/slash`). This project uses the specification-defined fields and no
custom top-level keys, so strict clients ignore what they do not need. Recorded as
`D-0008`.

### 3. The repository root is also the skill directory

The skill directory must be named after the skill, so the repository root *is*
`prodoc-guard/` and holds `SKILL.md`. Codex's guidance recommends against extra
files such as a `README.md` inside a skill folder. A public, installable project
needs a README, a licence, tests and CI, so this repository keeps them and
accepts the extra files. Only `SKILL.md` and the files it references are loaded
into an agent's context, so the practical cost is zero.

### 4. `allowed-tools` is not declared

The field is marked experimental, and support varies between clients. Declaring
it could restrict an assistant in ways that differ per product, so it is omitted
rather than guessed. Recorded as `D-0008`.

## Known limitations

- **No client can guarantee the skill is used.** Activation depends on the
  description matching the task, or on explicit invocation.
- **The CLI needs Python 3.8+ and Git.** Without Git, `status` and `check` lose
  history-dependent results and say so explicitly.
- **The secret scan covers the three canonical documents only.** It is a safety
  net, not a secret scanner for a repository.
- **Structure is checked, not meaning.** A document can pass every check and still
  describe the wrong system. Evidence citations narrow the gap; they do not close
  it.
- **Windows** is supported by the CLI, which uses `os.replace` and no POSIX-only
  process behaviour, but the test suite has been run on Linux only. Treat Windows
  as unverified until a run is published in `docs/TEST_REPORT.md`.

## Reporting a compatibility problem

Open an issue with the product and version, the exact install path you used, the
command or prompt you ran, and what happened. A failing case is worth more than a
passing one.
