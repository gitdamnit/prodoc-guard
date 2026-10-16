# Release Checklist

Everything that must be true before a public release. Run the checks rather than
trusting this page.

State legend: `[ ]` not done, `[x]` done, `[~]` not applicable yet.

## 1. Correctness

- [ ] `python3 tests/run_tests.py` reports 0 failed, 0 errored, and leaves the
      working tree clean (its default output is untracked).
- [ ] `docs/test-results.json` and `docs/TEST_REPORT.md` were refreshed on purpose
      with `--update-evidence --force`, and committed with the code they describe.
- [ ] `python3 scripts/check_skill.py .` exits 0.
- [ ] `python3 scripts/prodoc validate` exits 0 at the repository root.
- [ ] `python3 scripts/prodoc check` exits 0 at the repository root.
- [ ] Every functional requirement in `PRODUCT_REQUIREMENTS.md` is covered by at
      least one test, or is explicitly listed as untested with a reason.

## 2. Documentation truthfulness

- [ ] `PROJECT_STATUS.md` `## Tests` rows match the generated report, including
      counts.
- [ ] Every work item marked `Implemented`, `Tested`, `Deployed` or `Published`
      cites evidence that exists.
- [ ] `## Known Defects` lists what is actually broken. "None known" is only
      correct if it is true.
- [ ] `## Blockers` is empty or explains each blocker.
- [ ] No `prodoc:todo` placeholder remains in any canonical document.
- [ ] The observed repository-state block is refreshed by `prodoc update` on the
      release commit, not hand-written.
- [ ] `## Verification Evidence` holds at least one entry with a commit identifier
      and an artefact that exists, and the commit exists in the repository.
- [ ] Nothing presents the observed block as verification of the implementation
      or of the tests.

## 3. Decisions

- [ ] Every architectural or irreversible choice made for this release has a
      record in `DECISION_LOG.md`.
- [ ] `prodoc check` reports no `log.modified`, `log.append_only` or
      `log.reordered`: no past record's substance was rewritten, deleted, or moved.
- [ ] Any `log.status_changed` warning is an intentional supersede that points at a
      superseding record.
- [ ] Decision ids are unique and ascending.

## 4. Security

- [ ] No credential, token, connection string, or private key anywhere in the
      repository. `prodoc check` covers the canonical documents; search the rest
      by hand or with a dedicated scanner.
- [ ] `SECURITY.md` names a working reporting route.
- [ ] The CLI still opens no sockets and reads no credentials.
- [ ] The composite action still declares `contents: read` and no `write`
      permission.

## 5. Compatibility

- [ ] `docs/COMPATIBILITY.md` matches the vendor documentation it cites, and
      every claim is labelled specification-conformant, runtime-tested, unverified,
      unsupported, or planned.
- [ ] No client row is labelled `Runtime-tested` without a recorded discovery-and-invocation run.
- [ ] The portable `SKILL.md` contains no vendor-namespaced frontmatter keys.
- [ ] The shipped scripts import only the standard library.
- [ ] Installation instructions were followed from a clean clone, in a scratch
      directory, for each supported environment.
- [ ] Platform limitations (for example: not yet tested on Windows) are stated.
- [ ] No document claims guaranteed automatic activation in any product.

## 6. Packaging

- [ ] `LICENSE` is present and names the copyright holder.
- [ ] `README.md` attribution is accurate.
- [ ] `CHANGELOG.md` has a dated section for the version being released.
- [ ] The version string in `scripts/prodoc`, `SKILL.md` metadata and
      `agents/openai.yaml` agree.
- [ ] No editor backup, `.DS_Store`, `__pycache__`, or temporary file is tracked.
- [ ] `.gitignore` covers generated scratch files.

## 7. Git and publication

- [ ] Working tree clean; `prodoc check` reports `clean`.
- [ ] The release commit is on the default branch and pushed.
- [ ] The tag matches the version and points at that commit.
- [ ] `prodoc update` was run after the final commit, so the verified state is
      true, and the resulting documentation commit is also released.
- [ ] The GitHub Actions workflow passes on the release commit.
- [ ] Nothing was force-pushed.

## 8. Claims

- [ ] No statement claims vendor endorsement, approval, marketplace listing, or
      affiliation.
- [ ] No claim of users, adoption, downloads, or performance that is not
      evidenced.
- [ ] Anything unverified is described as unverified.

## Release commands

```bash
python3 tests/run_tests.py --update-evidence --force
python3 scripts/check_skill.py .
python3 scripts/prodoc validate
python3 scripts/prodoc check
python3 scripts/prodoc update --phase Released   # refuses without verification evidence
python3 scripts/prodoc validate && python3 scripts/prodoc check
git add PRODUCT_REQUIREMENTS.md DECISION_LOG.md PROJECT_STATUS.md docs/
git diff --cached --stat
git commit -m "docs: vX.Y.Z release status"
git tag -a vX.Y.Z -m "vX.Y.Z"
git push origin vX.Y.Z
```
