# DESIGN v0.2 — repo-state: version stamp + status.json + CI enforcement (caty-ai public repos)

- Date: 2026-08-25
- Author: Alpha (design writer). Implementation writer: Codex GPT-5.6 Sol (code_workflow default).
- Status: v0.2 — incorporates all blocking findings from the L1-9 pre-implementation
  3-seat heterogeneous review of v0.1 (Kimi K3 / Grok 4.6 / GLM 5.3, all fresh-context
  read-only, all GO-WITH-CHANGES). Finding IDs below reference the seat reviews.
- Owner decisions frozen (2026-08-25 clarify batch):
  - D1: scope = ALL caty-ai public repos; CI-enforced so future repos/commits cannot forget
  - D2: canon + parent issue in caty-ai/family-os
  - D3: update mechanism = CI auto-update

## 1. Problem (unchanged from v0.1)

External AI reviewers/agents fetching our public repos through GitHub HTML pages receive
CDN-cached content of mixed generations (4 generations of one page observed in one session,
2026-08-25). README tails get truncated by tooling. Goal: any reader on any generation can
(a) see which generation it is, (b) follow one pointer to a canonical small state file.
Staleness DETECTION, not freshness proof. Non-goal: forcing GitHub to serve latest HTML.

## 2. Components

### 2.1 Stamp block — stamped-file set [rev: Grok F6, Kimi F5, GLM F4]

The stamped set per repo is exactly:
1. every `README*.md` at repo root (all four locales: `README.md`, `README.ja.md`,
   `README.zh.md`, `README.th.md` — whichever exist), and
2. the file named by `agents_entry` — `FOR-AGENTS.md` **or** `AGENTS.md`, whichever the
   repo actually has (harness has `AGENTS.md`; the check resolves the name, never assumes).

Block (idempotent, replace-between-markers), placed immediately after the readme-standard
centered header `</div>` (or after the H1 where no header div exists), before the intro/TOC.
In the agents file it goes after the H1 without displacing the existing "one-line route"
convention line:

```markdown
<!-- repo-state:begin (generated; do not edit) -->
<p align="center"><sub>generation: <code>48aa5ca</code> (2026-08-25T13:00:00Z) · verify: <a href="https://api.github.com/repos/caty-ai/caty-agent-harness/commits/main">API HEAD</a> · <a href="./status.json">status.json</a></sub></p>
<!-- repo-state:end -->
```

- SHA-first; timestamp is ISO time, not bare date [rev: Grok F2 "date is a costume"].
- The contract is the marker comments, not the rendered HTML (non-GitHub renderers may
  strip HTML) [rev: Kimi F8].
- readme-standard canon gets a one-line amendment blessing this position and the markers,
  so canon-driven README rewrites don't strip them [rev: Kimi F8, GLM Q3].

### 2.2 status.json (repo root, ≤ 2 KB) [rev: Grok F7/Q5, Kimi F7/Q5, GLM Q5]

```json
{
  "$schema": "https://raw.githubusercontent.com/caty-ai/family-os/main/docs/repo-state/status.schema.json",
  "schema_version": 1,
  "generator_version": "repo-state-gen v1",
  "repo": "caty-ai/caty-agent-harness",
  "stamp_mode": "auto",
  "generated_at": "2026-08-25T13:00:00Z",
  "describes_commit": "48aa5ca5ac773925bbb21c0839b55acc079740b3",
  "describes_commit_date": "2026-08-25T12:41:07Z",
  "branch": "main",
  "latest_tag": "v0.13.0",
  "latest_release_url": "https://github.com/caty-ai/caty-agent-harness/releases/tag/v0.13.0",
  "agents_entry": "AGENTS.md",
  "canonical_api": "https://api.github.com/repos/caty-ai/caty-agent-harness/commits/main",
  "canonical_raw": "https://raw.githubusercontent.com/caty-ai/caty-agent-harness/48aa5ca5ac773925bbb21c0839b55acc079740b3/status.json",
  "freshness_contract": "SHA comparison only; dates may only ever trigger distrust. Protocol: docs/repo-state/spec.md, section 'Reader protocol'."
}
```

Changes vs v0.1: `canonical_api` added (CDN-free); `canonical_raw` now points at
raw@describes_commit (immutable), not raw@branch; `generator_version`, `stamp_mode`,
`describes_commit_date`, `$schema` added. `generated_at` is set to the committer date of
`describes_commit`, NOT wall clock. Ordinary runs carry forward the existing release
fields, so regeneration of an unchanged content state without explicit release refresh is
fully deterministic and produces a byte-identical file [rev: GLM F2].

### 2.3 Reader protocol — SHA-based, never date-based [rev: Kimi F1 + Grok F2 + GLM F3/F7 — 3-seat convergent CRITICAL]

Written into the spec page, the FOR-AGENTS/AGENTS stanza, and `freshness_contract`:

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
5. For commissioned reviews, hand reviewers SHA-pinned raw URLs / clone-at-SHA up front;
   see `docs/repo-state/spec.md`, handover paragraph following Reader protocol. The stamps
   are the safety net for uncommissioned readers, not the primary path.

## 3. CI mechanism

### 3.1 Reusable workflow + caller [rev: Grok F1, Kimi F2/F6, GLM F2/F5/F8a]

- `caty-ai/family-os/.github/workflows/repo-state.yml` (workflow_call) + generator script
  `tools/repo-state-gen.sh` vendored in family-os, consumed by callers at a pinned tag.
- Caller (~12 lines) in each repo: triggers `push: branches [main]`,
  `release: types [published]`, `workflow_dispatch`, `pull_request` (check job only).
  Caller MUST set `permissions: contents: write` — reusable workflows cannot elevate
  the token themselves [rev: GLM F8a]. `concurrency: group: repo-state-${{ github.ref }}`
  serializes racing runs [rev: GLM F2, Grok F7].
- Loop/skip guards, event-scoped [rev: Grok F1 CRITICAL, GLM F5 — v0.1's guard both blocked
  the release path and failed to stop loops]:
  - `push` events only: skip when `github.actor == 'github-actions[bot]'` (primary) or the
    head commit message starts with `chore(repo-state):` (backup) [rev: Kimi F6, GLM F2].
    Push regeneration preserves the existing `latest_tag` / `latest_release_url` fields and
    does not probe GitHub releases or `git describe`.
  - `release` / `workflow_dispatch` events: never skipped. Release and
    manual-dispatch runs check out **main HEAD** (GITHUB_SHA for release events is the last
    commit on the default branch — confirmed against GitHub docs by two seats) and refresh
    release fields by querying `gh api repos/{owner}/{repo}/releases/latest`; explicit 404
    maps both fields to `null`, while any other transport or HTTP failure is fatal. These
    runs do not stamp the tag SHA [rev: Kimi F2 MAJOR].
  - Determinism is the real loop-stopper for ordinary push regeneration: when content and
    carried-forward release metadata are unchanged, output is byte-identical (§2.2) → no
    diff → no commit, regardless of token type [rev: Grok F1 — prefix guard alone is lethal
    with PAT/App tokens]. `release` / `workflow_dispatch` are explicit metadata refresh
    points; they diff only when content or refreshed metadata changes, and they fail
    instead of writing partial state when refresh errors occur.
- `describes_commit` := nearest non-stamp ancestor of the checked-out HEAD (walk past
  consecutive `chore(repo-state):` commits) [rev: Grok F1, GLM F6a].
- Stamp commits: message `chore(repo-state): <short-sha>`; author/committer =
  `github-actions[bot]` (standard noreply identity). Push failure fails the job loudly
  (no `|| true`); one `pull --rebase` retry [rev: Grok F7].

### 3.2 Delivery to main — canon compliance [rev: Grok F4, Kimi F4 MAJOR]

Handbook L0-5 says main is merge-only. Resolution, in order of preference:
1. **Single mode (default): bot push under a recorded, scoped canon exception** — text to
   land in `docs/03-git-protocol.md` via the normal handbook PR path:
   "`github-actions[bot]` may push `chore(repo-state):` stamp commits to main; all other
   direct pushes remain forbidden." Branch protection gets an allowance for the bot where
   protection exists. The exception is part of this design's Done-when, not an afterthought.
2. **verify-only mode (documented exception only, per repo, registry-recorded)**: where an
   allowance is impossible. The make target stamps the current BASE-branch HEAD (post-merge
   it describes HEAD^), never the PR-branch head — squash-merge would otherwise strand an
   unreachable SHA and produce weekly false alarms [rev: GLM F6b]. `stamp_mode` in
   status.json makes the mode machine-visible; audit rules are per-mode [rev: GLM Q4].
   Verify-only repos are stale-by-construction at every HEAD (safe direction); the spec
   says so explicitly [rev: Kimi Q4]. No third mode exists.

### 3.3 Check job (PR) vs weekly audit — division of labor [rev: Grok F3 vs GLM F1, synthesized]

- **PR check (`pull_request`, required status via org ruleset)**: presence + schema-valid +
  markers present in the full stamped set (§2.1) + cross-file consistency (stamp SHA/time
  in every stamped file == status.json). NO freshness diff — content PRs legitimately lack
  regenerated stamps [rev: GLM F1 tail]. Fork PRs get exactly this read-only job.
- **Weekly audit (family-os, extends the existing `family-links` Sunday run)**: for every
  org public repo (universe = the registry's orphan-checked set, `check_registry.py`
  `--require-reality`, fail-closed [rev: Grok F5, GLM F8c]):
  a. status.json exists, schema-valid;
  b. health invariant by IDENTITY, not position [rev: GLM F1 CRITICAL — v0.1's
     "HEAD or HEAD^" blessed a dead stamper forever]: auto-mode healthy ⇔ HEAD is a bot
     stamp commit ∧ describes_commit == nearest non-stamp ancestor; HEAD being a content
     commit is drift unless it clears within the next run (transient window);
     verify-only-mode healthy ⇔ per-mode rule (§3.2.2);
  c. regenerate-and-diff on main HEAD: run the generator, tree-diff outside stamp-managed
     regions must be empty [rev: Grok F4 "honest invariant", GLM F1];
  d. latest repo-state caller run conclusion per repo via API — a disabled/unparseable/
     failing caller is drift even when files look right [rev: Kimi F3b];
  e. results land as dated lines in the existing weekly report issue (visible heartbeat).
- **Dead-man's switch** [rev: Kimi F3 + Grok F5 + GLM F8e — convergent MAJOR]: the audit's
  ABSENCE must itself alarm. The existing FMA schedule-liveness probe (outside GitHub cron)
  watches the weekly report issue's freshness; report missing > 8 days ⇒ alert. GitHub's
  60-day auto-disable of scheduled workflows is the named enemy.

### 3.4 Cost statement [rev: Kimi F6, GLM F8b — owner accepts with eyes open]

Every content push to main yields one bot stamp commit (history ~2× commit count on quiet
repos; push-CI runs ~2× since stamp commits re-trigger on-push workflows — mitigate with a
`paths-ignore` on heavy workflows where wanted). This is the price of D3; recorded here so
nobody later mistakes it for a bug.

## 4. Rollout

1. family-os: schema + generator + reusable workflow + spec page + readme-standard
   amendment + L0-5 exception PR (handbook) + parent issue.
2. Child issues per repo. Every caller PR touches `.github/workflows/**` → risk gate
   requires 翔さん's human label (verified: `review-labels.yml` risk_paths_gates) — batch
   all label clicks into one sitting [rev: GLM F8d].
3. New-repo template gains caller + stamp stanza (D1 future-repos; backstop = registry
   orphan check, which already enforces org-wide accounting).
4. harness: release-sync composes with the `release: published` trigger; no manual
   `gh release create` there (known).

## 5. Future work (recorded, not in scope)

- Org-level `index.json` in family-os (all repos' HEAD SHAs, written by the weekly audit)
  as a SECOND channel — all three seats independently evaluated it as a replacement and
  rejected it (a central file can't mark which generation a cached page is), but two
  recommended it as a complement [Grok Q6, GLM Q6, Kimi Q6].
- caty.talk no-cache mirror and llms.txt: deferred (owner decision 2026-08-25).

## 6. Review record

- v0.1 reviewed 2026-08-25 by 3 heterogeneous fresh-context read-only seats
  (writer=Alpha/Anthropic; opus-5 excluded as same-family, substituted grok-4.6 per
  loom-seats): Kimi K3 GO-WITH-CHANGES · Grok 4.6 GO-WITH-CHANGES · GLM 5.3
  GO-WITH-CHANGES. All blocking findings and all flip conditions are incorporated above;
  full seat outputs archived with the parent issue.
- Convergent findings (adopted as confirmed): SHA-not-date reader protocol (3 seats);
  4-locale stamp set (3 seats); audit dead-man's switch (3 seats); event-scoped loop
  guards + release-path unblocking (Grok+GLM); L0-5 conflict (Grok+Kimi); identity-based
  health invariant (Grok+GLM).

## v0.2.1 amendments (2026-08-25 merge review)

- R1: Ordinary generation carries forward existing `latest_tag` / `latest_release_url`
  values; only explicit release refresh (`release`, `workflow_dispatch`, or
  `--refresh-release`) queries GitHub, with explicit 404 mapping to `null`.
- R2: `freshness_contract` now uses the exact required literal, and the handover citation
  points to `docs/repo-state/spec.md`, handover paragraph following Reader protocol.
- R3: Repo-state self-tests were hardened for ambiguity, missing anchors, `--check`
  marker corruption, PATH-without-`gh`, and deterministic timestamp coverage.
