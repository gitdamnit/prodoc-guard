# GitHub and Git Workflow

Mechanics for the repository side of ProDoc Guard: locating the right repository,
reading its state, committing documentation safely, handling pull requests, and
releasing. Load this before any commit, push, pull request, or release.

## Contents

- [Orientation commands](#orientation-commands)
- [Committing documentation](#committing-documentation)
- [Pull requests](#pull-requests)
- [Releases](#releases)
- [Failure modes](#failure-modes)

## Orientation commands

Run these before writing anything. All are read-only.

```bash
git rev-parse --show-toplevel              # repository root; work relative to this
git rev-parse --abbrev-ref HEAD            # branch name, or "HEAD" when detached
git rev-parse HEAD                         # full commit SHA to record
git status --porcelain                     # uncommitted work, one line per path
git remote -v                              # remotes; credentials are redacted by prodoc
git log --oneline -5                       # recent context
```

`prodoc status --json` returns the same picture in one call: `git.root`,
`git.branch`, `git.detached`, `git.commit`, `git.working_tree`, `git.changed`,
`git.remotes`, and per-document presence, phase and verified block.

Deciding which repository you are in matters more than it looks. A nested
checkout, a submodule, or a worktree can put the task in a repository other than
the one you assumed. Confirm the root before editing.

## Committing documentation

1. Confirm the user authorized a commit for this work.
2. Review what changed: `git status --porcelain`, then `git diff`.
3. Stage explicit paths only:

```bash
git add PRODUCT_REQUIREMENTS.md DECISION_LOG.md PROJECT_STATUS.md
```

4. Verify the staged set before committing:

```bash
git diff --cached --stat          # only the intended files
git diff --cached                 # only the intended hunks
```

5. Commit with a message that says what changed and why:

```bash
git commit -m "docs: record decision D-0007 on document format"
git rev-parse HEAD                # capture the SHA for the report
```

Rules:

- Never `git add -A`, `git add .`, or `git commit -a`.
- Never `--amend`. It rewrites history and can silently drop someone else's work.
- Never commit while `PROJECT_STATUS.md` contains a claim you did not verify.
- Never commit a document containing a secret. `prodoc check` must be green.
- One logical change per commit; do not bundle unrelated edits.

## Pull requests

A documentation change in a pull request should be reviewable on its own.

1. Work on a branch whose name states the change. Create it only when the user
   asks — ProDoc Guard never switches branches on its own.
2. Run the checks that CI will run, locally, before pushing:

```bash
python3 scripts/prodoc validate
python3 scripts/prodoc check
python3 scripts/check_skill.py .
```

3. Push with authorization, and observe the result:

```bash
git push --set-upstream origin <branch>
```

4. Open the pull request with a body that states: what changed, which decision or
   requirement it serves, what was tested, and what was not.

The bundled composite action checks the canonical documents on every pull
request. Copy this step into a workflow:

```yaml
- uses: gitdamnit/prodoc-guard/.github/actions/prodoc-check@main
```

It runs `validate` and `check` against the *checked-out* repository, needs only
`contents: read`, and never commits. Treat a red check as a real finding: fix the
document rather than the check.

## Releases

1. Move the relevant items to `[Deployed]` or `[Published]` with evidence, and add
   the test rows that prove it.
2. Update `CHANGELOG.md` and the version in every place it appears.
3. `prodoc update --phase Released`, then `prodoc validate && prodoc check`.
4. Commit the documentation before tagging, so the tag points at a state whose
   documented status is true.
5. Tag and publish only with explicit authorization:

```bash
git tag -a v0.1.0 -m "v0.1.0"
git push origin v0.1.0
```

6. Add a decision record for anything non-obvious about the release.
7. Record the release in `PROJECT_STATUS.md` under `## Release Status`, and never
   claim a release you did not observe.

## Failure modes

| Symptom | Meaning | Response |
| --- | --- | --- |
| `fatal: not a git repository` | Wrong directory, or an unversioned tree | Report it; run `prodoc init`/`validate` only if the user wants documents there |
| `HEAD` from `--abbrev-ref` | Detached HEAD (CI, tag build, bisect) | Record `detached-head`; do not create a branch unasked |
| Empty `git remote -v` | Local-only project | Work locally; say remote writes are impossible |
| `error: failed to push some refs` | Remote moved ahead | Report verbatim; fetch and show the divergence. Never force-push |
| `Permission denied` / `403` | Auth or policy failure | Report it; do not retry with different credentials |
| `read-only file system` | Immutable checkout | Produce a patch or the file content for the user to apply |
| Shallow clone, no history | `git show HEAD:<file>` fails | Skip append-only checks and state that they were skipped |
| Protected branch rejection | Branch ruleset | Move the change to a branch and open a pull request |
