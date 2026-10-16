# Decision Log

Append-only record of decisions that shape ProDoc Guard. Add new records at the
end; never edit or delete a record's substance.

## How to Use This Log

1. Copy the record template from `templates/DECISION_LOG.md`.
2. Use the next free four-digit ID; IDs are never reused or renumbered.
3. Record the date the decision was made, not the date it was implemented.
4. List the alternatives that were rejected, and why.
5. To change your mind, append a new record and set the old one's `Status` to
   `Superseded by D-NNNN`. Never rewrite history.

## Decisions

### D-0001 — Keep project memory as three Markdown files in the repository

- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** Assistants lose project context between sessions. The memory has to survive across products, be reviewable by humans, and keep working when a tool is removed. It also has to be free to adopt.
- **Alternatives Considered:** A hosted service with an API (rejected: adds an account, a subscription, and a dependency that can disappear); a local database or SQLite file (rejected: binary, unreadable in a diff, invisible in a code review); a chat transcript archive (rejected: nobody reads it and it cannot be reviewed); a single combined document (rejected: requirements, decisions and status have different audiences and different write permissions).
- **Decision:** Maintain exactly three canonical Markdown documents — `PRODUCT_REQUIREMENTS.md`, `DECISION_LOG.md`, `PROJECT_STATUS.md` — at the repository root, versioned with Git.
- **Rationale:** Markdown renders everywhere, diffs cleanly, needs no tooling, and lives where the work lives. Git already provides history, authorship, review, and access control.
- **Consequences:** Structure is enforced by convention rather than a schema, so a linter is required to make the convention real. Prose can still be wrong in ways no checker detects. Human readability becomes a hard constraint on every change.
- **Supersedes:** None

### D-0002 — Implement the CLI in Python 3 using only the standard library

- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** The CLI touches real repositories, so it must be auditable. It also has to run on a stranger's machine with no setup, inside CI containers, and on an air-gapped host.
- **Alternatives Considered:** Node.js with `commander` and `yaml` (rejected: adds a package manager and a lockfile for a small text tool); Go single binary (rejected: a build step per platform, and contributors must install a toolchain); Rust (rejected: disproportionate build and maintenance cost); Bash (rejected: brittle text handling and poor testability); Python with third-party libraries (rejected: any dependency creates an install step and a supply-chain surface).
- **Decision:** Ship `scripts/prodoc` as one Python 3.8+ file using only the standard library. Use PyYAML and the official `skills-ref` validator when they happen to be installed, and never require them.
- **Rationale:** Python 3 is present wherever Git is used, `unittest` covers the test suite without a dependency, and a single file can be read end to end before it is trusted.
- **Consequences:** The frontmatter parser implements a deliberate YAML subset rather than the full grammar, and falls back to PyYAML when available. The file grows large enough that structure matters more than it would in a multi-file package. Windows behaviour must be exercised explicitly rather than assumed.
- **Supersedes:** None

### D-0003 — Fix the document structure with level-2 headings

- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** Machines must be able to check that a section exists, and humans must be able to read and edit the same file. Something has to be the contract between them.
- **Alternatives Considered:** YAML frontmatter per document (rejected: converts prose into escaped scalars and produces hostile diffs); a JSON sidecar (rejected: two files describing one thing, guaranteed to drift); free-form prose (rejected: unverifiable); requiring a strict template with no flexibility (rejected: real projects need to add sections).
- **Decision:** Each canonical document must contain a fixed set of `##` level-2 headings, matched case-insensitively. Extra sections are allowed. Content within sections is free-form Markdown.
- **Rationale:** Headings are unambiguous, survive formatting, are visible in every editor and Git host, and let a checker verify structure without parsing prose.
- **Consequences:** Renaming a heading is a breaking change and requires a decision record. `prodoc validate` treats a missing heading as an error, so it must stay in step with the templates.
- **Supersedes:** None

### D-0004 — Confine automated writes to a managed verified-state block

- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** `prodoc update` has to record branch, commit and working-tree facts, but the surrounding file is the user's prose. A tool that rewrites user text will eventually destroy it.
- **Alternatives Considered:** Regenerate `PROJECT_STATUS.md` from scratch (rejected: destroys unverified human context); write a separate machine-generated state file (rejected: a second source of truth that drifts); interpolate facts on read (rejected: nothing is recorded, so a review cannot see what was true at the time).
- **Decision:** `prodoc update` replaces only the text between `<!-- prodoc:verified:start -->` and `<!-- prodoc:verified:end -->`, refuses to run when either marker is absent, and leaves every other byte untouched.
- **Rationale:** The blast radius of the only write that could silently damage a project shrinks to four lines that the tool owns.
- **Consequences:** The markers become load-bearing and must not be edited by hand. Missing markers are a hard error rather than a silent no-op. A test must assert that non-managed content survives byte-for-byte.
- **Supersedes:** None

### D-0005 — The CLI never mutates Git state

- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** The tool runs inside other people's repositories, often invoked by an assistant. A tool that commits or pushes can cause damage the user never reviewed.
- **Alternatives Considered:** `prodoc commit` convenience command (rejected: removes the human review gate); auto-staging documentation changes (rejected: `git add -A` class accidents); a `--push` flag behind a confirmation (rejected: the confirmation is a formality in a non-interactive shell).
- **Decision:** The CLI issues read-only Git commands only (`rev-parse`, `status`, `show`, `remote -v`). It never runs `add`, `commit`, `push`, `checkout`, `reset`, `merge`, `branch`, `tag`, or `stash`. Committing and pushing stay with the user, with explicit authorization.
- **Rationale:** The irreversible actions remain where a human can see them. The tool's value is verification and reporting, not automation of consequences.
- **Consequences:** Users and assistants must run Git themselves, so the skill has to document safe commit practice. Idempotency and safety become trivial to test. A test asserts HEAD is unchanged after every command.
- **Supersedes:** None

### D-0006 — A freshly initialized project fails validation on purpose

- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** `prodoc init` creates documents that are structurally valid but empty of meaning. If validation passed immediately, an empty project would look documented.
- **Alternatives Considered:** Pass validation with empty sections (rejected: green status on an empty project is exactly the false confidence this project exists to prevent); omit validation until first commit (rejected: the failure then appears at the worst moment); warn instead of error (rejected: warnings are ignored in CI).
- **Decision:** Bundled templates carry unfilled `prodoc:todo` markers (HTML comments). `prodoc validate` reports each remaining marker as an error, naming the missing information.
- **Rationale:** Initialization produces a correct skeleton, not a claim. The exit code states honestly that the documentation is not yet written.
- **Consequences:** The first `validate` after `init` is always red. Documentation must explain that this is expected, or users will treat the tool as broken. Filling a section means replacing the marker text and deleting it.
- **Supersedes:** None

### D-0007 — Bundle document templates under templates/ rather than assets/

- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** The Agent Skills specification recommends `assets/` for templates and allows any additional directory. The document skeletons are also directly executed against by `prodoc init`, which resolves their path.
- **Alternatives Considered:** `assets/templates/*.md` (rejected: nests one level deeper than any other reference and adds a directory that only ever holds templates); `references/` (rejected: references are loaded into an agent's context on demand, while templates are file content to be copied, and mixing them invites the agent to paste a template into a document it did not intend to create).
- **Decision:** Bundle the three skeletons in a top-level `templates/` directory, with `PRODOC_TEMPLATES` and `--templates` overriding the resolved location.
- **Rationale:** `templates/` states what the files are, keeps every bundled reference one level deep from `SKILL.md`, and separates content-that-gets-copied from documentation-that-gets-read.
- **Consequences:** A documented, deliberate deviation from the `assets/` convention, recorded in `docs/COMPATIBILITY.md`. The path is resolvable from the script's own location, so installed copies keep working.
- **Supersedes:** None

### D-0008 — Keep the specification's optional frontmatter fields

- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** The Agent Skills specification defines `name`, `description`, `license`, `compatibility`, `metadata` and `allowed-tools`. Codex's own skill-authoring guidance says to include only `name` and `description`. OpenCode reads OpenCode-specific behaviour from `metadata`.
- **Alternatives Considered:** Emit `name` and `description` only (rejected: OpenCode would lose the slash-command behaviour configured through `metadata`, and licence and environment requirements would have nowhere to live); add custom top-level keys (rejected: violates the specification and breaks clients that validate strictly); put everything in the body (rejected: environment requirements belong in metadata so a client can act on them before loading the body).
- **Decision:** Use `name`, `description`, `license`, `compatibility` and a small `metadata` map containing `author`, `version` and `opencode/slash`. Do not use custom top-level fields, and do not use `allowed-tools`, which is still experimental and could restrict an agent unexpectedly.
- **Rationale:** Every field used is defined by the specification, so strict clients ignore what they do not need and lenient ones gain the extra behaviour. The cost is one documented tension with Codex's authoring guidance.
- **Consequences:** The deviation from Codex's name-and-description guidance is documented in `docs/COMPATIBILITY.md` and asserted by a test. `allowed-tools` will be revisited if it leaves experimental status.
- **Supersedes:** None

### D-0009 — Scan only the three canonical documents for credentials

- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** The canonical documents are the files this tool writes, commits and shares, so they are where a pasted credential is most likely to end up and most likely to be reviewed by a colleague.
- **Alternatives Considered:** Scan the whole repository (rejected: slow on large trees, noisy on fixtures and vendored code, and duplicates dedicated secret scanners); scan the three documents plus the templates (rejected: templates contain no user data); do not scan at all (rejected: the failure mode, committing a live credential, is severe and cheap to catch).
- **Decision:** `prodoc check` scans `PRODUCT_REQUIREMENTS.md`, `DECISION_LOG.md` and `PROJECT_STATUS.md` for documented credential patterns, reports each match as an error, and prints only a redacted prefix of the candidate.
- **Rationale:** Narrow scope keeps the check fast, deterministic and free of false positives from test fixtures, while covering the files whose contents this tool is responsible for.
- **Consequences:** The scanner is a safety net with a known blind spot, and both the code and the documentation say so. Real remediation, rotating a leaked credential, stays a user decision because removing the line does not remove it from history.
- **Supersedes:** None

### D-0010 — Ship the pull-request check as a composite action

- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** Other repositories need to validate their own documents on a pull request, without adopting this repository's workflows or granting write access.
- **Alternatives Considered:** A root `action.yml` JavaScript action (rejected: needs a build step and a bundled `node_modules`, and runs with a token the check does not need); a copy-paste workflow snippet only (rejected: users then own the checker and it drifts); a hosted GitHub App (rejected: an account, a service, and outbound trust for a text check).
- **Decision:** Ship a composite action at `.github/actions/prodoc-check/action.yml` that resolves its scripts through `github.action_path`. Consumers reference it with `uses:`. It declares `permissions: contents: read`, runs `validate` and `check`, and never commits.
- **Rationale:** A composite action carries the checker with it, needs no build, and its permissions can be read at a glance in the workflow file.
- **Consequences:** Consumers must pin a ref, and the action must keep working when layered on an arbitrary checkout, so the templates path has to be resolvable from the action's own directory rather than the caller's. This repository's own workflow dogfoods it.
- **Supersedes:** None

### D-0011 — Require evidence on a closed vocabulary of work states

- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** The single most damaging failure in AI-assisted work is a confident, unevidenced claim of completion. Prose cannot be checked, so the claim has to have a mechanical shape.
- **Alternatives Considered:** Free-form status prose (rejected: unverifiable); a percentage-complete field (rejected: invented precision, and it hides what was actually verified); requiring a commit SHA on every item (rejected: not every piece of work has a commit, and a SHA does not prove testing); trusting the assistant to be honest (rejected: that is the problem being solved).
- **Decision:** Every work item starts with exactly one state from a closed list — `Planned`, `In Progress`, `Implemented`, `Tested`, `Deployed`, `Published`, `Blocked`, `Removed`. `Implemented`, `Tested`, `Deployed` and `Published` must cite evidence on the same line: a backticked path, a URL, or a 7–40 character commit SHA.
- **Rationale:** A closed vocabulary is checkable, greppable and honest about the difference between writing code and proving it works. The four evidence-bearing states are exactly the ones that mislead when unproven.
- **Consequences:** Claims without evidence are rejected rather than downgraded, so honest reporting sometimes means writing `In Progress` when the work feels finished. The Tests table carries the same rule, and `Not run` is a first-class result.
- **Supersedes:** None

### D-0012 — Never record the working tree as clean when it is not

- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** The verified-state block is the machine's claim about reality. If it records a clean working tree while uncommitted changes exist, the one fact users trust most becomes the one that misleads them.
- **Alternatives Considered:** Record only the commit, omitting tree state (rejected: a reader then cannot tell whether the document describes the commit or someone's afternoon); refuse to update while the tree is dirty (rejected: writing status before committing is the normal workflow, and refusing would push users to a tool they fight); record `unknown` (rejected: `git status` is always available, so `unknown` would hide an available fact).
- **Decision:** `prodoc update` records branch, full commit SHA, `clean` or `dirty`, and a UTC timestamp. A dirty tree is recorded as `dirty` and reported as a warning, never as `clean` and never as a failure.
- **Rationale:** Recording the truth about a dirty tree costs nothing and removes the most plausible way for this tool to lie. Refusing to run would trade one honesty problem for a usability problem.
- **Consequences:** A `dirty` verified block is normal and must not be read as an error. `prodoc check` warns when the recorded commit is behind `HEAD`, and treats a recorded commit that does not exist as an error, because that one is unrecoverable by re-running the command.
- **Supersedes:** None

### D-0013 — Put the implementation in scripts/ rather than a src/ package

- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** The implementation is one offline CLI plus one skill validator. A conventional `src/` package layout would need a package name, `__init__.py` files, an entry-point shim, and a decision about how a skill's `SKILL.md` refers to code it can execute.
- **Alternatives Considered:** `src/prodoc/` as an installable package with a console-script entry point (rejected: adds packaging and an install step for a tool whose premise is that there is no install step); a `pyproject.toml` with an editable install (rejected: a build toolchain and a dependency resolver where a file copy would do); a root-level `prodoc.py` (rejected: it mixes application code with the canonical documents at the repository root); `scripts/` only (chosen).
- **Decision:** Keep the executable code in `scripts/`, the Agent Skills convention for bundled code an agent runs, and put tests and the evidence generator in `tests/`.
- **Rationale:** The specification tells an agent to execute bundled scripts by relative path from the skill directory, so `scripts/prodoc` works in every client with nothing installed, built, or resolved.
- **Consequences:** There is no `src/` package and no installable distribution, so the CLI is consumed by copying it or adding it to `PATH`. Tests import the extensionless script by file path rather than by module name, which is unusual and contained in one helper. If a second consumer ever needs to import the code as a library, this decision must be revisited rather than worked around.
- **Supersedes:** None

### D-0014 — Stay vendor-neutral: one portable skill, no vendor plugins or keys

- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** Agent Skills are portable, but every client extends the format and expects skills in its own directory. It is easy to drift into a folder of per-vendor plugins, each with its own release, or into putting vendor keys in the shared `SKILL.md`. Claude Code's documentation is explicit that a non-specification frontmatter field causes a hard error when a skill is packaged for claude.ai or the Skills API, so vendor keys in the portable file are not merely inelegant — they break a distribution path.
- **Alternatives Considered:** Vendor-namespaced metadata keys in the shared `SKILL.md`, such as OpenCode's slash-command flag (rejected: it is a vendor key in the one file meant to be portable, and it removes nothing from the safe spec-only set); shipping thin per-client plugin packages for marketplaces (rejected: several release surfaces for identical files, and two of the clients that want it, Cursor and ChatGPT, require marketplace review); one implementation per client (rejected: duplication, drift, and much more code to audit); a single portable skill plus documented local adapters (chosen).
- **Decision:** Ship one `SKILL.md` that uses only specification-defined frontmatter fields, and one standard-library CLI. Handle client differences with install paths — the cross-vendor `.agents/skills/` directory first — and with adapters that are a local copy edit or an optional shipped file, never a fork. Publish a compatibility matrix that labels each integration verified, unverified, unsupported, or planned, defines what "verified" means, and states per row what was actually checked.
- **Rationale:** Project memory outlives any single assistant. A portable artifact plus honest documentation is more durable, and far smaller to audit, than a set of vendor packages that must each track a changing format. Removing the vendor key also unblocks claude.ai and Skills API packaging, which a vendor key would fail closed.
- **Consequences:** The OpenCode `/prodoc-guard` slash command is not enabled by default; users who want it add one line to their own copy. Cursor and ChatGPT cannot install from a repository without a plugin, so those routes are labelled `Planned` rather than claimed. "Verified" had to be defined narrowly — documentation read plus conformance measured by `scripts/check_skill.py` — because no client was launched to test activation, and existing tests now fail if a vendor-namespaced key, a non-standard-library import, or a claim of guaranteed activation appears.
- **Supersedes:** None

### D-0015 — Detect edits to existing decision records, and say what that is worth

- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** An independent review found that the append-only check compared the *set* of decision IDs against HEAD. Deleting a record was caught; editing one in place was invisible as long as the ID survived, which is the more likely accident and the more damaging one, because a silently rewritten rationale is indistinguishable from an original.
- **Alternatives Considered:** Hash the whole file against HEAD (rejected: every legitimate append changes the file, so the check would fire constantly); compare per-record content digests but include `Status` (rejected: superseding a record is supposed to mutate its Status, so that would forbid the sanctioned workflow); treat any change as a warning (rejected: an edited decision is exactly the thing this project promises to catch); store digests in a sidecar file (rejected: a second source of truth that drifts and can be edited independently).
- **Decision:** Compute a whitespace-normalized digest per decision record over its title and its substantive fields (`Date`, `Context`, `Alternatives Considered`, `Decision`, `Rationale`, `Consequences`, `Supersedes`), and compare digests by ID against `HEAD`. Report an edit as an error naming the record and the changed fields, a deletion as an error, a reordering of records as an error, and a `Status` change as a warning. State in `references/security.md`, `SKILL.md` and the CLI's own documentation that this is an integrity check against the current `HEAD`, not tamper-proof protection: anyone who can rewrite Git history can rewrite the baseline.
- **Rationale:** Comparing per-record digests catches the case sets miss, keeps the intended supersede workflow working, and needs no extra file. Excluding `Status` from the digest is what lets "change your mind by appending" coexist with "never rewrite history".
- **Consequences:** Reflowing a paragraph is not an edit, but fixing a typo in another field now fails the check, so a genuine correction has to be committed knowingly rather than slipped in. Validation and checking now overlap slightly, since a mangled record is reported by both. The guarantee is bounded in a way that must be stated wherever it is relied upon, and the tests assert the wording exists.
- **Supersedes:** None

### D-0016 — Separate observed Git metadata from recorded verification evidence

- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** The review found that the managed block, its markers, its field names, and the section heading all used the word "verified". `prodoc update` reads a branch, a commit and a timestamp and runs nothing, so the language implied that running one command verified the implementation and its tests. It also meant a project could look verified with no record of what was actually checked, and a release could be declared with no evidence at all.
- **Alternatives Considered:** Keep the wording and document the nuance (rejected: the misleading word was in the machine-written block, which is the part users trust most); rename the fields but keep one section (rejected: observed facts and human evidence have different authors and different trust levels, and one section forces them together); make the CLI run the tests so "verified" becomes true (rejected: that is deployment functionality this tool does not need and should not have); require a changelog or a signed attestation for releases (rejected: heavier machinery than the problem needs).
- **Decision:** Rename the managed block to observed state — `<!-- prodoc:observed:start -->`, fields `Observed branch`, `Observed commit`, `Observed working tree`, `Observed at` — and have `prodoc update` write a caveat inside the block stating it is not verification. Rename the section to `## Repository State` and add a required `## Verification Evidence` section whose entries are written by hand and must cite a commit identifier and an artefact. Reject a release-state claim (phase `Released`, or a `[Deployed]`/`[Published]` item) that has no verification entry, and refuse `prodoc update --phase Released` in the same situation. Accept the old markers and heading during a transition, report them as deprecated, and migrate them on the next `update`.
- **Rationale:** The two facts have different authors and different costs of being wrong, so they should not share a heading, a block, or a word. Requiring a commit and an artefact turns "we verified this" into something a reviewer can check, and it is the smallest mechanism that makes a release claim meaningful without adding a deployment feature.
- **Consequences:** `## Verification Evidence` is a newly required section, so existing documents fail validation until it is added — a deliberate breaking change for a pre-1.0 tool, mitigated by deprecation warnings for the old heading and block rather than an immediate hard failure. The `--json` output renames `facts` to `observed` and its keys, which is a breaking change for consumers. Field names became longer. The release gate can block a release for a missing entry, which is the intended behaviour and needs a clear remedy message.
- **Supersedes:** None

### D-0017 — Keep hash-check plus atomic rename, and document the residual window

- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** The review asked for the hash-check/atomic-replace sequence to be reviewed for concurrent updates, and for the concurrency guarantee to be documented or improved. The original sequence hashed the file, wrote a temporary file, then renamed it. A writer landing between the hash and the rename could be overwritten.
- **Alternatives Considered:** Advisory locking with a lock file (rejected: a crashed process leaves a stale lock that blocks every future update, which is a worse and more frequent failure than the race it closes); `O_EXCL` on the real file (rejected: it conflicts with replacing an existing document); accept the original window and document it (rejected as the only measure: the window is easy to narrow); do nothing and document (rejected: the improvement is cheap).
- **Decision:** Verify the hash twice — before writing and again immediately before the rename — fsync the temporary file before renaming, and re-read the file after the rename to confirm the written content. Document in `references/security.md` and in the function's docstring that the final check and the rename cannot be one atomic operation, that the residual window is two adjacent syscalls, and why advisory locking was rejected.
- **Rationale:** The double check closes the realistic case, which is a human or another assistant editing the document while a command runs, at no cost to reliability. The remaining window is microseconds wide and requires a second writer to hit it exactly; the alternative trades it for a stuck-state failure mode that a documentation tool should not have.
- **Consequences:** Two extra file reads per write, which is irrelevant for documents of this size. A test interposes on `os.fsync` to land a write inside the window, so the second check is exercised rather than assumed. The guarantee is now stated precisely instead of loosely, including what it does not cover.
- **Supersedes:** None

### D-0018 — Refuse to write through symlinks or outside the project

- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** The review asked for tests covering symlinks and repository boundaries, and for unintended writes outside the selected project to be prevented. `os.replace` onto a symlinked path replaces the link rather than the target, so a project that linked its status document into a shared directory would silently lose the link. A path that resolved elsewhere, and a redirect to a Git root, could both reach outside what the user selected.
- **Alternatives Considered:** Follow symlinks and write the target (rejected: writes data outside the selected project, which is precisely what was asked to be prevented); warn and continue (rejected: a warning does not undo a destroyed link); refuse only when the resolved target leaves the project (rejected: that still destroys in-project links and hides the intent); refuse symlinks and out-of-project targets, and report the real path (chosen).
- **Decision:** Before writing, refuse (exit 4) if the target is a symbolic link, telling the user the real path to write instead, or if the target's resolved parent is not the resolved project directory. `init` additionally treats a symlinked document as present rather than creating one, so it never replaces a link. Only redirect document resolution to a Git root that is an ancestor of the selected directory, so a nested repository is never reached into.
- **Rationale:** Both failures are silent and both are easy to rule out with a check that runs immediately before the write. Refusing and naming the real path preserves the user's intent instead of guessing at it.
- **Consequences:** Documented setups that symlink `PROJECT_STATUS.md` into a shared directory now fail with exit 4 and need a layout change. Tests cover a symlinked document, a symlink into a directory outside the project, a nested repository, a linked worktree, and a window in which no command creates a file outside the project.
- **Supersedes:** None

### D-0019 — Generated test reports go to an untracked directory by default

- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** The review found that running the test suite rewrote two tracked files (`docs/test-results.json` and `docs/TEST_REPORT.md`), so simply verifying the project dirtied the working tree. It also asked that committed evidence not be overwritten silently, while keeping an intentional way to refresh it.
- **Alternatives Considered:** Keep writing to `docs/` and document it (rejected: the working tree must stay clean for a review handoff or a release); write only to a temporary directory (rejected: then there is no committed evidence to cite, and `PROJECT_STATUS.md` cites exactly these files); make refreshing evidence a separate script (rejected: two entry points for one job); default to a scratch directory with an explicit flag for the tracked files (chosen).
- **Decision:** Default output is `test-output/`, which is gitignored. `--output DIR` writes elsewhere. `--update-evidence` writes the tracked files in `docs/` and refuses without `--force` when they already exist, exiting 2 with a message naming the files and the alternative. Add `--pattern` so a subset can be run, which also keeps the suite fast.
- **Rationale:** Verifying the project should not modify it, and the two behaviours have different risk: a scratch run is safe to repeat, while replacing cited evidence is a deliberate act that should require a flag. Refusing without `--force` also means a mistyped command cannot quietly destroy the evidence a reviewer is reading.
- **Consequences:** The evidence files are only regenerated on explicit request, so they can be one revision behind the code and must be refreshed before a release; the release checklist says so. `PROJECT_STATUS.md` continues to cite `docs/test-results.json`, which exists but is refreshed deliberately. The refusal path exits 2 rather than 1, since it is a usage error.
- **Supersedes:** None

### D-0020 — Split "verified" into specification-conformant and runtime-tested

- **Date:** 2026-10-15
- **Status:** Accepted
- **Context:** The review found that the compatibility matrix labelled clients `Verified` on the strength of reading their documentation and measuring conformance with `scripts/check_skill.py`. No client was ever launched, so no skill was discovered or invoked, yet the strongest-sounding label in the table was applied to six clients. The distinction the reviewer asked for was between integrations that conform to the specification and integrations that have been exercised.
- **Alternatives Considered:** Keep `Verified` with a footnote defining it narrowly (rejected: the label is what gets quoted, and the footnote gets dropped); drop per-client rows entirely (rejected: users need to know where to install, and which claims are unproven); mark everything unverified (rejected: conformance genuinely was measured, and pretending otherwise hides real work); two labels with an explicit evidence column (chosen).
- **Decision:** Replace `Verified` with `Specification-conformant` (documentation read plus conformance measured) and reserve `Runtime-tested` for a client where discovery and invocation were actually exercised and the run is recorded. State in the matrix that no client is labelled `Runtime-tested` because none was launched. Add a test that fails if a client row claims `Runtime-tested` without citing a recorded run.
- **Rationale:** The label should be the size of the evidence. Conformance is a real, checkable property and worth stating; it is not the same claim as "this works in your tool", and conflating them is the failure mode the whole project exists to avoid.
- **Consequences:** `Runtime-tested` currently appears only for the no-client path exercised by the suite itself, which is marked as not a client claim. Recording a real activation run becomes visible, valued work rather than an implicit assumption. Readers see a weaker headline claim, which is the honest one.
- **Supersedes:** None
