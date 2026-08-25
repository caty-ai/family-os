# Repository state protocol

This document is the normative contract for repository state stamps. Agents use the
reader protocol to decide which bytes to trust. Maintainers use the generator and CI
mechanism to keep the contract consistent. The frozen design record is
[`DESIGN.md`](./DESIGN.md).

## 1. Stamp block and stamped-file set

The stamped-file set is exactly:

1. every existing `README*.md` at the repository root, including every locale; and
2. the file named by `agents_entry`: either `FOR-AGENTS.md` or `AGENTS.md`, according to
   which file the repository has.

Each stamped file contains exactly one block with these marker comments:

```markdown
<!-- repo-state:begin (generated; do not edit) -->
<p align="center"><sub>generation: <code>48aa5ca</code> (2026-08-25T13:00:00Z) · verify: <a href="https://api.github.com/repos/caty-ai/caty-agent-harness/commits/main">API HEAD</a> · <a href="./status.json">status.json</a></sub></p>
<!-- repo-state:end -->
```

The marker comments, not rendered HTML, are the contract. The SHA is the first seven
characters of `describes_commit`, and the timestamp is `generated_at` in ISO-8601 UTC.
The API link is `canonical_api`.

In a README, the block is immediately after the readme-standard centered header's
closing `</div>`, or immediately after the H1 when there is no centered header. In the
agents entry it is immediately after the H1; existing routing text remains intact.
Generation replaces the region between valid markers and never appends a second region.
A missing half, reversed pair, or duplicate marker is a hard error.

## 2. `status.json`

`status.json` is a UTF-8 JSON object at the repository root and is no larger than 2 KiB.
Its schema is [`status.schema.json`](./status.schema.json). Field semantics are:

| Field | Semantics |
| --- | --- |
| `$schema` | Canonical raw URL of the family-os status schema. |
| `schema_version` | Integer protocol version; currently `1`. |
| `generator_version` | Generator identity; currently `repo-state-gen v1`. |
| `repo` | GitHub `owner/repository` slug. |
| `stamp_mode` | Exactly `auto` or `verify-only`. No third mode exists. |
| `generated_at` | Committer date of `describes_commit`, normalized to ISO-8601 UTC. It is never wall-clock time. |
| `describes_commit` | Full lowercase 40-character SHA of the nearest ancestor whose commit message does not start with `chore(repo-state):`. |
| `describes_commit_date` | Committer date of `describes_commit`, in ISO-8601 UTC. |
| `branch` | Branch whose API HEAD is the comparison target, normally the default branch. |
| `latest_tag` | Latest detected tag. It may be omitted or `null` when no tag is available. |
| `latest_release_url` | Latest detected GitHub release URL. It may be omitted or `null` when no release is available or GitHub cannot be reached. |
| `agents_entry` | The stamped agent entry file, exactly `FOR-AGENTS.md` or `AGENTS.md`. |
| `canonical_api` | CDN-independent GitHub commits API URL for `repo` and `branch`. |
| `canonical_raw` | Immutable raw URL for `status.json` at `describes_commit`. |
| `freshness_contract` | A reminder that only the SHA protocol below can establish currentness. |

Because both time fields derive from the described commit, regenerating an unchanged
content state with unchanged release metadata produces byte-identical output.

## 3. Reader protocol — SHA-based, never date-based

1. Resolve true HEAD once via `https://api.github.com/repos/{owner}/{repo}/commits/{branch}`
   (or `git ls-remote`) — the API does not ride the page CDN.
2. A page is CURRENT ⇔ its stamp SHA == HEAD, or HEAD is a stamp commit and
   stamp SHA == HEAD^ [rev: GLM F7 — prevents false-stale desensitization].
3. On ANY mismatch (older or newer): re-fetch everything at `raw@<sha>` pinned to the API
   HEAD (or clone at that SHA). raw@branch fetches are advisory only — every file at a
   branch ref rides an independent cache, so a fresh status.json vouches for nothing else
   fetched at a branch ref [rev: GLM F3].
4. Dates/`generated_at` may only ever trigger DIStrust, never trust. Two dates from two
   caches are not comparable evidence [rev: Kimi F1 scenario].
5. For commissioned reviews, hand reviewers SHA-pinned raw URLs / clone-at-SHA up front
   (§2.6) — the stamps are the safety net for uncommissioned readers, not the primary path.

The review handover mechanism is therefore explicit: resolve one commit SHA first, then
hand every reviewer raw URLs pinned to that SHA, or a clone checked out at that SHA. Do
not hand reviewers branch-pinned raw URLs and do not use dates as evidence of freshness.

## 4. CI semantics

The reusable workflow has two jobs. `update` runs for default-branch pushes, published
releases, and manual dispatches. Push events alone are skipped when the actor is
`github-actions[bot]` or the head commit message begins `chore(repo-state):`. Release and
manual events are never skipped. Release runs check out the default branch HEAD, not the
release tag, so publishing a release refreshes release metadata without stamping the tag
SHA.

An update regenerates deterministic output and exits without a commit when the managed
files have no diff. Otherwise it commits as `github-actions[bot]` with message
`chore(repo-state): <short-sha>` and pushes. A rejected push gets one `pull --rebase`, a
fresh regeneration, and one retry; a second failure fails the job. Caller workflows must
grant `contents: write` and serialize runs with
`concurrency: group: repo-state-${{ github.ref }}`.

Automatic mode requires the recorded, scoped canon exception that allows
`github-actions[bot]` to push only `chore(repo-state):` commits to the default branch;
all other direct pushes remain forbidden. Branch protection must grant that bot the
corresponding allowance where protection exists.

The `check` job runs for pull requests and invokes only `repo-state-gen.sh --check`. It
requires a schema-valid `status.json`, a valid marker block in the entire stamped-file
set, and stamp SHA/time consistency with `status.json`. It deliberately performs no
freshness comparison or regeneration diff: a content pull request legitimately has not
yet received its post-merge automatic stamp.

The separate family-os weekly audit covers every orphan-checked public repository and
fails closed when reality cannot be enumerated. It verifies schema presence, applies the
mode-specific health invariant by commit identity, regenerates and diffs the managed
state, checks the latest caller-run conclusion, and appends dated results to the weekly
report issue. An external schedule-liveness probe treats a report older than eight days
as an alert, including GitHub's scheduled-workflow auto-disable failure mode.

For `auto`, audit health means HEAD is a bot stamp commit and `describes_commit` is its
nearest non-stamp ancestor; position alone is insufficient. The automatic mechanism
adds roughly one stamp commit and one extra push-triggered CI run per content push.

## 5. Verify-only mode

`verify-only` is a documented, per-repository, registry-recorded exception for a
repository where the bot cannot receive a scoped direct-push allowance. Its maintainer
target runs the generator against the current base-branch HEAD, not the pull-request
branch. After the content change merges, that stamp describes `HEAD^`; this avoids
recording an unreachable pull-request SHA after a squash merge.

Verify-only repositories are stale by construction at every post-merge HEAD. This is the
safe direction: readers detect a mismatch and pin their fetches to the API HEAD. CI still
checks presence, schema, the full stamped-file set, and cross-file consistency, while the
registry audit applies its separate verify-only health rule. Select the mode with
`repo-state-gen.sh --stamp-mode verify-only`; automatic repositories use `auto`.
