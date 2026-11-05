# Inbox

Routed proposals awaiting triage. See `~/projects/claude-code-config/docs/routing.md`.

## 2026-11-05, claude-code-config (minis): a GitHub Actions trap leaves the global CLAUDE.md, kept only where Actions are used

- **Provenance:** hub Gotchas audit, 2026-11-05, minis. The clause failed the breadth test (it names GitHub Actions; 4 of 31 repos have Actions workflows, this one among them), on the 2026-08-10 `GITHUB_TOKEN` precedent. It was removed from the global file, so from now on it reaches this project's sessions only if this project keeps it.
- **Clause:** `gh run list --commit` needs the full 40-char SHA; an abbreviation matches nothing at exit 0, which reads as "no run triggered".
- **Proposal:** keep it where a session meets it, likely the project CLAUDE.md beside the Actions workflow, since the failure is silent and matters before the command is written; drop it if this project's sessions never query runs. Placement is this project's call.
