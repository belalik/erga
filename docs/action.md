# The erga GitHub Action

Status: added in v0.3. The action is a thin composite wrapper around the CLI:
it sets up uv, then runs `uvx erga==<version> build`. Everything the CLI does
is documented in the [README](../README.md) and
[requirements-v1.md](requirements-v1.md); this file covers only what changes
when you run it from a workflow.

## What it does and does not do

It produces the output file and exits. It does not check out your repository,
and it does not commit, push, or open pull requests. Delivery is composed in
your workflow from single-purpose actions you already trust, which is the
dominant pattern for thin tool wrappers and keeps erga out of the business of
guessing how your repo wants to receive data. The two recipes are in the
README.

Because it does not check out, `actions/checkout` must come first. Without it
the workflow fails on a missing config rather than doing something surprising.

## Inputs

| Input | Required | Default | Notes |
|-------|----------|---------|-------|
| `version` | yes | none | The erga release to install, e.g. `"0.2.0"`. |
| `config` | no | `erga.yml` | Path to the config, relative to the workspace. |
| `api-key` | no | empty | OpenAlex API key. Pass a secret, never a literal. |

`version` has no default on purpose. A default would mean an upgrade could
arrive on a Tuesday morning in a repo nobody is watching, and the whole point
of this tool is that the data in your repo changes only when you can see why.
Upgrading is an edit to your workflow file, reviewed like any other.

### Where the output goes

Every path in the config resolves against the config file's own directory,
not the workspace root. Placing the config where the site wants its data is
therefore usually the entire configuration:

| Config at | Writes | Curation files read from |
|-----------|--------|--------------------------|
| `_data/erga.yml` | `_data/publications.json` | `_data/manual.yml`, etc. |
| `erga.yml` | `publications.json` | `manual.yml`, etc. |

The Jekyll case is the happy accident that makes the default recipe short:
`_data/` is exactly where Jekyll looks, and it exposes the config itself as
`site.data.erga`, so templates can iterate the configured author list without
a second source of truth. A per-author filter should read `authors[].tracked_as`
rather than `authors[].name`: `tracked_as` is the configured name, identical
across every alias and spelling variant the registrars carry, so filtering on
it needs no alias logic in the template.

### The API key

The key is optional. Without one, erga uses OpenAlex's keyless per-IP quota
and says so in the log. That is fine for small runs, but shared CI runner IPs
make it unreliable at department scale, so a key is worth having once you are
tracking more than a handful of authors.

`api-key` is wired to the default `OPENALEX_API_KEY` variable. If your config
renames `openalex.api_key_env`, this input will not reach it; set that
variable as job-level `env` instead, which does propagate into the action's
steps. Step-level `env` on the `uses:` step does not reliably propagate, which
is why the key is an input rather than something the action reads from the
environment: a key that silently fails to arrive looks exactly like a working
keyless run until the rate limit hits.

## Workflow guidance

**Declare `permissions` explicitly.** Recipe 1 needs `contents: write`; recipe
2 needs `pull-requests: write` as well. Declaring them narrows the default
token, and it documents for the next reader what the workflow is allowed to
touch.

**Use a concurrency group** so a scheduled run and a manual one cannot race
each other into a conflicting commit:

```yaml
concurrency:
  group: erga-${{ github.ref }}
  cancel-in-progress: false
```

**Schedule off the top of the hour.** `cron: "0 * * * *"` is the most
contended minute on GitHub's scheduler and your run will drift or be dropped.
Any other minute is better: `"17 5 * * 1"` rather than `"0 5 * * 1"`.

**Scheduled workflows are disabled after 60 days** without repository
activity. A publications list that updates itself is exactly the kind of repo
that goes quiet, so expect this and re-enable it, or accept that a commit now
and then keeps it alive.

**Weekly is usually right.** Publication metadata does not change hourly, and
every run costs API budget and a commit's worth of noise.

## Versioning and tags

Releases carry a full semver tag, so today you reference the action as
`belalik/erga@v0.3.0`. There is deliberately no moving tag yet: while the
schema can still change, a tag that silently advances is the wrong default.
A moving `v1` will be minted with the 1.0 release, per the `actions/checkout`
convention, and `belalik/erga@v1` will track the current major line from then
on.

Note the distinction, because it bites: `@v1` pins the *action* wrapper, while
the `version` input pins the *CLI* that does the work. Moving to a new `@v1`
revision changes how the wrapper invokes erga; it never changes which erga you
get. Two separate decisions, deliberately.

Inside the action, `astral-sh/setup-uv` is pinned to an exact tag rather than
a major. That repository publishes no moving major tag, so `@v9` does not
resolve at all, and a workflow referencing it fails at setup with an error
that reads like a network problem. Caching is off for the same pragmatic
reason: the uvx pattern has no lockfile to key a cache on, and leaving it
enabled warns on every single run.

## How it is tested

Two jobs in this repository's CI, doing deliberately different work:

- `action` runs on every push and pull request against a fixture config whose
  author is tracking-only and whose manual entries carry venues. That build
  makes no OpenAlex or Crossref request at all, so it is fast and its output
  is fixed, and it asserts the exact result. It proves the wiring: inputs
  reaching the CLI, the setup-uv pin resolving, config-relative paths,
  curation files, output written.
- `action-live` runs weekly against live OpenAlex with a small pinned author,
  covering the one thing the deterministic job cannot see: that OpenAlex still
  answers in the shape erga expects. Unmapped-type warnings in that log are
  the early signal of upstream vocabulary drift.

Both install the published package from PyPI, since that is what `uvx` does,
so neither says anything about the working tree. The test matrix covers that.
