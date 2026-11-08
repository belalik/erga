# Releasing

The version lives in `src/erga/__init__.py`; hatch reads it from there. Main
carries `X.Y.Z.dev0` between releases.

1. CI green on main; `uv run pytest`, `ruff check`, `ruff format --check`
   and `mypy` clean locally. Docs current. For a change that touches the
   output, a live control per consumer: copy its config and curation
   files into the scratchpad, fetch its main `publications.json` with
   `gh api` (a local clone lags the CI refreshes), build under the
   previous release (`uvx --from erga==<prev>`) and under the working
   tree (`uv run --project <repo>`), and compare the two outputs field by
   field; the counts feed the release notes and the step 7 entries.
2. Update whatever pins the previous version: the Action examples in
   `README.md` and `docs/action.md`, the milestones in
   `docs/requirements-v1.md`, and `version` plus `date-released` in
   `CITATION.cff`.
3. Set `__version__` to the release. Commit as "Bump version to X.Y.Z",
   push.
4. Tag and push the tag:

       git tag -a vX.Y.Z -m "erga X.Y.Z"
       git push origin vX.Y.Z

5. Publish the GitHub Release. Publishing it is what triggers
   `release.yml`, which builds and uploads to PyPI through Trusted
   Publishing; nothing is published by the tag alone.

       gh release create vX.Y.Z --title "erga X.Y.Z" --notes-file <notes>

   Watch the run, then confirm `https://pypi.org/pypi/erga/json` reports
   the version. Find the run with `gh run list --workflow release.yml`;
   filtering with `--commit` takes the full 40-character SHA only, and a
   short one matches nothing at exit 0, which reads as "no run triggered".
6. Set `__version__` to `X.Y.(Z+1).dev0`. Commit as "Back to dev version
   after vX.Y.Z", push.
7. Route each consumer the release: an entry for its `docs/inbox.md`,
   sent with `~/projects/claude-code-config/tools/route-inbox.sh` (no git
   there), naming the pin to move, every place it sits, and what changed
   for that site. An override the release makes unneeded is shown by a
   build without it, from a copy of the previous file with that record's
   patched fields blanked: left in place, the ratchet supplies the
   override's own value and the check cannot fail (2026-11-08). Consumers: smartmove-site (`uvx erga==X.Y.Z` in its
   deploy workflow, docs and CLAUDE.md) and dpsd-new (the Action's `uses:`
   and `version:`). If an earlier entry is still untriaged, send an
   amending entry that says so. Any local check the entry suggests runs
   `uvx --refresh-package erga erga==X.Y.Z`: a machine that resolved the
   previous version earlier that day holds a cached index without the new
   one, the build fails, and the old `publications.json` left in place
   diffs as "no changes" (smartmove-site, 2026-10-17). CI starts with a
   fresh index and is immune.

Release notes: one sentence on what the release is for, one bullet per
user-visible change, the install line last. The Releases page is the
history; there is no CHANGELOG file.
