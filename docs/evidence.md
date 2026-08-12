# Evidence

We keep claims beside primary evidence that an outside reader can inspect.
We record what we believe, what we built, what actually happened, and what we still do not know.
A claim whose link dies or whose review lapses fails closed and reverts to unknown.
If `last-reviewed` is older than 90 days, the claim is unknown until we reverify it.
Weekly CI flags stale evidence, humans edit this file, and CI never edits it.

## EV-001 — A guard that could pass while verifying nothing was found and closed

| field | value |
| --- | --- |
| claim-id | EV-001 |
| believe | A map that claims to check reality must fail when it cannot see reality. |
| built | Weekly registry checker `tools/check_registry.py` runs anonymously and, since PR #1, fails closed when the check cannot complete. |
| actually happened | The initial checker silently skipped every module under anonymous API rate limiting yet printed OK with exit 0. One reviewer run skipped 5 of 8. The fix moved to HTML checks and added `--require-reality` for the scheduled run. |
| still don't know | Whether every future fail-open shape is covered. See EV-002. |
| state (delivery · visibility · evidence) | implemented · published · observed |
| evidence | primary: https://github.com/caty-ai/family-os/pull/1 ; secondary: https://github.com/caty-ai/.github/pull/12 (hand-edited generated SVGs were detected as generator drift and resynced with determinism proof) |
| observed-at | 2026-08-12 |
| last-reviewed | 2026-08-12 |
| owner | maintainers |
| counter-evidence | none |

## EV-002 — The publication gate was deliberately broken to prove it fails red

| field | value |
| --- | --- |
| claim-id | EV-002 |
| believe | A gate you have never seen fail is not a gate. |
| built | `tools/check_publication_gate.py` has a denylist, a personal-URL allowlist, per-language label checks, an SVG scan, and a selftest with negative fixtures. |
| actually happened | The introduction was mutation-probed. An unlabeled module link was appended to `README.md`. The gate failed on the exact line. `README.md` was restored byte-identical and SHA-256 was verified. The PR records the full probe matrix and a five-seat adversarial review that started 5/5 NO-GO and converged to GO over 3 rounds. |
| still don't know | None for the recorded probes. Future leak-shape coverage is bounded by the selftest matrix. |
| state (delivery · visibility · evidence) | implemented · published · observed |
| evidence | https://github.com/caty-ai/family-os/pull/32 |
| observed-at | 2026-08-12 |
| last-reviewed | 2026-08-12 |
| owner | maintainers |
| counter-evidence | none |

## EV-003 — The weekly reality check has run on schedule and passed

| field | value |
| --- | --- |
| claim-id | EV-003 |
| believe | This map rots silently unless something outside it checks it against reality on a clock. |
| built | `.github/workflows/family-links.yml` runs on Mondays at 08:00 JST with `--require-reality` and also runs on every push and pull request. |
| actually happened | A scheduled run executed and passed registry vs GitHub reality, link resolution, and the footer contract. |
| still don't know | Long-run behavior. This scheduled lane is young. At writing, we have one scheduled run and no failure has exercised the auto-filed issue path. |
| state (delivery · visibility · evidence) | implemented · published · observed |
| evidence | https://github.com/caty-ai/family-os/actions/runs/31341629945 |
| observed-at | 2026-08-12 |
| last-reviewed | 2026-08-12 |
| owner | maintainers |
| counter-evidence | none |

## EV-004 — A full governed self-growth cycle (propose → trial → council → owner approve → adopt) on the public record

| field | value |
| --- | --- |
| claim-id | EV-004 |
| believe | An agent may propose its own changes, but nothing is adopted without a human decision. |
| built | The mechanism is published. `caty-ai/self-growth-loop` ships propose, trial, council, and adopt scripts, templates, a ledger spec, and tests asserting no code path reaches adoption without approval. |
| actually happened | **No public primary record yet** — real cycle records live in a private runtime ledger and have not been published. |
| still don't know | Whether a real cycle record will be published. Until one is, this claim stays unverified by our own rule. This entry is the rule working. |
| state (delivery · visibility · evidence) | implemented · published · **unverified** |
| evidence | mechanism only: https://github.com/caty-ai/self-growth-loop (published, MIT) |
| observed-at | 2026-08-12 |
| last-reviewed | 2026-08-12 |
| owner | maintainers |
| counter-evidence | none |
