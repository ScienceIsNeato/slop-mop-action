# Slop-Mop GitHub Action

[![Used by](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2FScienceIsNeato%2Fslop-mop-action%2Fmain%2Fmetrics%2Fusage-badge.json)](https://github.com/ScienceIsNeato/slop-mop-action/network/dependents)

Run Slop-Mop in GitHub Actions and get a hull grade for the repo.

This repository is intentionally small. The action installs the `slopmop`
Python package, runs `sm swab` or `sm scour`, writes Slop-Mop's JSON and SARIF
outputs, optionally uploads SARIF to GitHub Code Scanning, surfaces the hull
grade in the job summary, and can enforce a minimum grade. Gate behavior,
SARIF shape, JSON schema, and the grading scale live in the main Slop-Mop
project.

Main project: https://github.com/ScienceIsNeato/slop-mop

## Hull Grades

Every full run grades the repo's hull — a deterministic rating computed by
Slop-Mop from how many gates are failing:

| Grade | Hull | Meaning |
| --- | --- | --- |
| A+ | shipshape | All gates green |
| A | seaworthy | All green, with warnings |
| B | serviceable | 1 gate failing |
| C | weathered | 2 gates failing |
| D | fouled | 3 gates failing |
| F | scuttled | 4+ gates failing |
| N/A | dry-dock | Repo never initialized |

The grade headlines the job summary and is exposed as action outputs
(`grade`, `hull`, `failing`, `warned`, `provisional`). Hull grades require
`slopmop >= 2.5.0`; on older versions the grade outputs are empty and the
action still works.

## Usage

```yaml
name: Slop-Mop

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read
  security-events: write
  actions: read

jobs:
  slop-mop:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5

      - uses: ScienceIsNeato/slop-mop-action@v1
        with:
          command: scour
```

Enforce a minimum hull grade (independent of pass/fail):

```yaml
- uses: ScienceIsNeato/slop-mop-action@v1
  with:
    command: scour
    fail-on-failure: "false"   # advisory on gate failures...
    minimum-grade: "B"          # ...but the hull must be serviceable or better
```

For fully advisory mode:

```yaml
- uses: ScienceIsNeato/slop-mop-action@v1
  with:
    fail-on-failure: "false"
```

To skip Code Scanning upload:

```yaml
- uses: ScienceIsNeato/slop-mop-action@v1
  with:
    upload-sarif: "false"
```

Use the grade downstream:

```yaml
- uses: ScienceIsNeato/slop-mop-action@v1
  id: slopmop

- name: Comment grade
  run: echo "Hull rating ${{ steps.slopmop.outputs.grade }} (${{ steps.slopmop.outputs.hull }})"
```

## Inputs

| Input | Default | Description |
| --- | --- | --- |
| `command` | `scour` | Slop-Mop validation command. Supported values: `swab`, `scour`. |
| `args` | `--no-auto-fix` | Extra arguments passed to `sm` before action-managed output flags. |
| `python-version` | `3.12` | Python version used by `actions/setup-python`. |
| `install-extra` | empty | PyPI extra installed as `slopmop[extra]`. Empty in v2 — gate tools come from the committed manifest, not the broad `all` extra. Set `all` for v1 install-everything behaviour. |
| `slopmop-version` | *(latest release)* | Version specifier. Pinned by default for deterministic install caching; the Slop-Mop release workflow bumps it on each release. Must support `sm doctor --required-deps`. See [Gate tools & caching](#gate-tools--caching). |
| `manifest-file` | `.slopmop/required-deps.json` | Committed dependency manifest from `sm doctor --required-deps`. The action installs exactly the tools it lists, by exact pin. |
| `verify-manifest` | `true` | Fail the run when the committed manifest has drifted from the repo's live gate config. |
| `project-install` | empty | Shell command that installs the target project's own deps before scanning (e.g. `python -m venv venv && ./venv/bin/pip install -e ".[all]"`). Needed when type-aware gates or dependency auditing should resolve the project's real environment. |
| `results-file` | `slopmop-results.json` | JSON results file path. |
| `sarif-file` | `slopmop.sarif` | SARIF file path. |
| `upload-sarif` | `true` | Upload SARIF with `github/codeql-action/upload-sarif`. |
| `sarif-category` | `slopmop` | Code Scanning category. |
| `strict-sarif-upload` | `false` | Fail if SARIF upload fails. |
| `fail-on-failure` | `true` | Fail the action when `sm` exits non-zero. |
| `minimum-grade` | empty | Fail when the hull grade is worse than this letter (`A+`, `A`, `B`, `C`, `D`, `F`). Empty disables enforcement. |

## Outputs

| Output | Description |
| --- | --- |
| `result` | `passed` or `failed`, based on the `sm` exit code. |
| `exit_code` | Raw `sm` exit code. |
| `results_file` | JSON results file path. |
| `sarif_file` | SARIF file path. |
| `grade` | Hull grade letter: `A+`, `A`, `B`, `C`, `D`, `F`, or `N/A`. Empty when not emitted. |
| `hull` | Hull condition: `shipshape`, `seaworthy`, `serviceable`, `weathered`, `fouled`, `scuttled`, `dry-dock`. |
| `failing` | Number of failing gates counted toward the grade. |
| `warned` | Number of warned gates. |
| `provisional` | `true` when operational skips may have hidden failing gates. |
| `hull_grade_json` | Compact `hull_grade` JSON object. |
| `grade_met` | `true`/`false` when `minimum-grade` is set and comparable; empty otherwise. |

## Gate tools & caching

Several gates wrap off-the-shelf tools — `flake8`, `black`, `vulture`, `radon`,
`mypy`, `pyright`, `bandit`, … In **v2** the action installs exactly the tools
your repo's gate config needs — by exact pin — from a committed dependency
manifest, instead of pulling the whole `slopmop[all]` extra:

- **Generate the manifest once** (and after any gate-config change):

  ```bash
  sm doctor --required-deps > .slopmop/required-deps.json
  ```

  Commit that file. It's the schema-versioned union of every enabled gate's
  declared requirements (tool name, install channel, exact pin) — the single
  source of truth for what CI installs.

- The action installs `slopmop` **core**, then reads the manifest and installs
  each tool by channel: Python tools are injected into Slop-Mop's pipx venv with
  `--include-apps` (exposing their console scripts on `PATH` *and* making them
  importable); npm tools install globally under a local prefix; system runtimes
  (`node`, etc.) are expected from a `setup-*` step and warned about if missing.
- **Drift guard:** with `verify-manifest: true` (default) the action re-emits the
  live manifest and fails if the committed file is stale — so the auditable
  artifact can't silently fall out of sync. Regenerate and recommit to fix.
- The whole install (pipx venv + injected tools + any npm tools) is cached with
  `actions/cache`, keyed on OS + resolved Python version + extra +
  `slopmop-version` + **a hash of the manifest**, so a tool repin/add/remove
  invalidates the cache and a plain cache hit skips reinstallation entirely.

### Your project's own dependencies

The action installs slop-mop and its gate tools — **not your project's
dependencies**. Type-aware gates (pyright/mypy) and dependency auditing resolve
against the *project* environment (`./venv`, `./.venv`, or `$VIRTUAL_ENV`).
If your repo's gates need that (Python packages usually do), either provision
the environment in a workflow step before this action, or let the action do it:

```yaml
- uses: ScienceIsNeato/slop-mop-action@v2
  with:
    command: scour
    project-install: |
      python -m venv venv
      ./venv/bin/pip install -e ".[all]"
```

Skipping this on a repo that needs it doesn't error — gates quietly analyze
the wrong environment (phantom unknown-type findings, auditing slop-mop's
tools instead of your deps). When in doubt, set it.

`slopmop-version` is **pinned by default** (and part of the cache key), so the
cache refreshes exactly when the pin changes. The Slop-Mop release workflow
opens a PR here to bump the pin on every release, so it tracks the latest
release without manual edits. Override the input to track a range (e.g.
`>=2.5.0`) — note that a range reintroduces cache staleness, since the key
then stays constant while the resolved version drifts.

## SARIF

When `upload-sarif` is `true`, the action uploads the SARIF file produced by
Slop-Mop. The consuming workflow must grant:

```yaml
permissions:
  contents: read
  security-events: write
  actions: read
```

Set `strict-sarif-upload: "true"` if SARIF upload failures should fail the
action. The default keeps adoption forgiving: Slop-Mop's own verdict still
controls the final pass/fail result.

## Grade Semantics

The action does not compute grades. It reads the `hull_grade` object that
Slop-Mop emits in its JSON results (the v3 envelope's `data` payload) and
surfaces it. Notes:

- `N/A` (dry-dock) means the repo has no Slop-Mop configuration yet. It never
  fails `minimum-grade` — the job summary shows the onboarding command
  instead.
- `provisional: true` means operational skips (missing tool, fail-fast, time
  budget) may have hidden failing gates; the letter is a floor, not a final.
- Partial runs (custom `-g` args) don't emit a grade.

## Versioning

`@v2` is a moving tag that tracks `main`. When a pin bump or fix merges, a
workflow repoints `v2` at the new commit, so consumers pick it up on their next
run without changing anything.

This is automatic on purpose. It used to be manual, and the result was that
`main` carried pins for 2.13.x, 2.14.x and 2.15.0 while `@v2` still installed
`==2.12.0` — every consumer stuck three releases back, with nothing anywhere
saying so.

Immutable `v2.x.y` tags are cut alongside notable releases for anyone who wants
to pin exactly. They are not moved.

## Marketplace Notes

This repository is designed for GitHub Marketplace publication:

- `action.yml` lives at the repository root.
- The repository contains only action metadata, action plumbing, docs, and a
  license.
- `.github/workflows` holds this repo's own maintenance jobs (usage metrics,
  the `v2` tag move) — not tests of the action itself. Test the action from a
  separate scratch repository before publishing releases.
