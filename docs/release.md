# Releasing

The version lives in `src/erga/__init__.py`; hatch reads it from there. Main
carries `X.Y.Z.dev0` between releases.

1. CI green on main; `uv run pytest`, `ruff check`, `ruff format --check`
   and `mypy` clean locally. Docs current.
2. Update whatever pins the previous version: the Action examples in
   `README.md` and `docs/action.md`, and the milestones in
   `docs/requirements-v1.md`.
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
   the version.
6. Set `__version__` to `X.Y.(Z+1).dev0`. Commit as "Back to dev version
   after vX.Y.Z", push.

Release notes: one sentence on what the release is for, one bullet per
user-visible change, the install line last. The Releases page is the
history; there is no CHANGELOG file.
