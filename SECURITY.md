# Security Policy

## Reporting a vulnerability

Report suspected vulnerabilities privately through GitHub's security advisory
feature on the repository (`Security` → `Report a vulnerability`). Do not open a
public issue for a vulnerability.

Please include: affected version or commit, reproduction steps, the impact you
believe it has, and whether the issue is already public. Expect an initial
response within seven days.

## Scope

In scope:

- `scripts/prodoc` and `scripts/check_skill.py`
- The bundled GitHub Action at `.github/actions/prodoc-check/`
- `SKILL.md` and the instructions it gives an assistant

Out of scope:

- Third-party clients (OpenCode, Codex, ChatGPT, and others) and their skill loaders
- A user's own repository content
- Vulnerabilities that require an already-compromised local account

## What ProDoc Guard does with your data

Nothing leaves your machine. The CLI opens no sockets, reads no environment
credentials, and requires no API key. It writes only two kinds of file: missing
canonical documents created from templates, and one managed block inside
`PROJECT_STATUS.md`. It never commits or pushes.

## High-consequence failure modes

The full threat model, hard rules, secret handling and degraded-environment
behaviour are in [`references/security.md`](references/security.md). The
short version:

- A leaked credential committed in a canonical document is treated as
  compromised; `prodoc check` detects common patterns and redacts matches in its
  output.
- Documentation text is data, never instructions. A line in a project document
  that tries to widen an assistant's permissions is a finding to report.
- Force-push, history rewriting, and unrequested branch changes are prohibited by
  the skill and impossible through the CLI.

## Supported versions

This project is pre-1.0. Security fixes are applied to the latest release and to
`main`.
