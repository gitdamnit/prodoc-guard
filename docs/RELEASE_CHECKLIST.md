# Release Checklist — v0.1.0 release candidate

State legend: `[x]` done and evidenced, `[ ]` not done, `[~]` not applicable yet.

Checked for the release candidate on **2026-10-15**. Evidence lives in
[`test-results.json`](test-results.json), [`TEST_REPORT.md`](TEST_REPORT.md),
[`RUNTIME_EVIDENCE.md`](RUNTIME_EVIDENCE.md) and
[`COMPATIBILITY.md`](COMPATIBILITY.md).

## 1. Correctness

- [x] `python3 tests/run_tests.py` reports 0 failed, 0 errored, and leaves the
      working tree clean (its default output is untracked).
- [x] `docs/test-results.json` and `docs/TEST_REPORT.md` were refreshed on purpose
      with `--update-evidence --force`.
- [x] `python3 scripts/check_skill.py .` exits 0.
- [x] The official reference validator (`uvx --from skills-ref agentskills validate .`)
      reports `Valid skill`, exit 0.
- [x] `python3 scripts/prodoc validate` exits 0 at the repository root.
- [x] `python3 scripts/prodoc check` exits 0 at the repository root.
- [x] End-to-end scenarios pass in disposable repositories: initialization,
      validation, status update, decision append, history tampering, release gate,
      nested repositories, worktrees, symlinks, dry runs, JSON output, exit codes
      (39/39).
- [x] Every functional requirement in `PRODUCT_REQUIREMENTS.md` is covered by a
      test, or is explicitly listed as untested with a reason (`Windows`,
      activation in uninstalled clients).

## 2. Documentation truthfulness

- [x] `PROJECT_STATUS.md` `## Tests` rows match the generated report, including
      counts.
- [x] Every work item marked `Implemented`, `Tested`, `Deployed` or `Published`
      cites evidence that exists.
- [x] `## Known Defects` lists what is actually broken.
- [x] `## Blockers` is empty or explains each blocker.
- [x] No `prodoc:todo` placeholder remains in any canonical document.
- [x] The observed repository-state block is refreshed by `prodoc update`, not
      hand-written.
- [x] `## Verification Evidence` holds entries with a commit identifier and an
      artefact that exists, and each commit exists in the repository.
- [x] Nothing presents the observed block as verification of the implementation or
      of the tests.

## 3. Decisions

- [x] Every architectural or irreversible choice made for this release has a record
      in `DECISION_LOG.md` (D-0001 … D-0020).
- [x] `prodoc check` reports no `log.modified`, `log.append_only` or `log.reordered`.
- [x] Decision ids are unique and ascending.

## 4. Security

- [x] No credential, token, connection string, or private key anywhere in the
      tracked tree. The canonical documents are covered by `prodoc check`; the
      whole tree was scanned separately.
- [x] The shipped core imports the standard library only, asserted by an automated
      test.
- [x] The shipped core imports no network module, asserted by an automated test.
- [x] `SECURITY.md` names a working reporting route.
- [x] The CLI opens no sockets and reads no credentials, except the documented
      opt-in `--official` fetch.
- [x] The composite action declares `contents: read` and no `write` permission.
- [x] No review ZIP, cache, generated output, or local configuration file is
      tracked.
- [x] Static analysis with `bandit -r scripts/`: 0 high, 0 medium, 2 low
      (`B404`/`B603`, the `subprocess`-without-`shell=True` pair). Accepted: the argv
      is an allowlist plus one path argument, and no shell is used.
- [x] No dependency manifest exists, so there is no dependency-vulnerability
      surface to audit.

## 5. Compatibility

- [x] `docs/COMPATIBILITY.md` matches the vendor documentation it cites, and every
      claim is labelled specification-conformant, runtime-tested, unverified,
      unsupported, or planned.
- [x] Every `Runtime-tested` claim cites a recorded run in `RUNTIME_EVIDENCE.md`.
- [x] No client is labelled `Runtime-tested` unless discovery or invocation was
      actually executed. Codex, Claude Code, Cursor and GitHub Copilot are not
      installed here and carry no runtime claim.
- [x] Installation was exercised from a clean export for the portable
      `.agents/skills/prodoc-guard/` path.
- [x] Platform limitations are stated: Windows `Not run`, Python 3.8–3.11 not
      executed.
- [x] No document claims guaranteed automatic activation in any product.

## 6. Packaging

- [x] `LICENSE` is present and names the copyright holder (MIT, Evan Zellner).
- [x] `README.md` attribution is accurate and disclaims vendor endorsement.
- [x] `CHANGELOG.md` has a dated section for this version, marked as a release
      candidate.
- [x] The version string in `scripts/prodoc` and `SKILL.md` metadata agree
      (`0.1.0`), asserted by an automated test.
- [x] `agents/openai.yaml` carries no version field, so there is nothing to keep in
      step.
- [x] No editor backup, `.DS_Store`, `__pycache__`, or temporary file is tracked.
- [x] `.gitignore` covers generated scratch output (`test-output/`).
- [x] A source-only archive was produced from `git archive HEAD` and verified
      byte-for-byte against the tracked tree.

## 7. Git and publication

- [x] Working tree clean, apart from one pre-existing untracked file that is not
      ours (`prodoc-guard-review.zip`) and is excluded from every commit.
- [ ] **Not done, requires authorization:** merge to the default branch.
- [ ] **Not done, requires authorization:** tag `v0.1.0` and push.
- [ ] **Not done, requires authorization:** create the public GitHub repository
      (`gitdamnit/prodoc-guard`) and publish the release.
- [ ] **Not done:** a real GitHub Actions run on a pushed commit. No remote
      exists, so CI is configured and statically checked only. Treat CI as
      **unverified** until a workflow run is recorded.
- [x] Nothing was force-pushed, and no history was rewritten beyond an unpushed
      local tip corrected before this candidate was cut.

## 8. Claims

- [x] No statement claims vendor endorsement, approval, marketplace listing, or
      affiliation.
- [x] No claim of users, adoption, downloads, or performance that is not evidenced.
- [x] Anything unverified is described as unverified.

## Release commands

For whoever holds publication authorization:

```bash
python3 tests/run_tests.py --update-evidence --force
python3 scripts/check_skill.py . --official
python3 scripts/prodoc validate && python3 scripts/prodoc check
python3 scripts/prodoc update --phase Released
python3 scripts/prodoc validate && python3 scripts/prodoc check

git add PRODUCT_REQUIREMENTS.md DECISION_LOG.md PROJECT_STATUS.md docs/
git diff --cached --stat
git commit -m "docs: v0.1.0 release status"
git tag -a v0.1.0 -m "v0.1.0"
git remote add origin git@github.com:gitdamnit/prodoc-guard.git
git push -u origin main --tags      # requires explicit authorization
```

After the first push, confirm the Actions workflow passes and record the run URL in
`PROJECT_STATUS.md` before treating CI as verified.
