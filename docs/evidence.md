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
| actually happened | The initial checker silently skipped every module under anonymous API rate limiting yet printed OK with exit 0. One reviewer run skipped 5 of the 8 modules then in the registry (measured 2026-08-05, PR #1; the registry has held 9 since 2026-08-07 and holds 9 as of 2026-08-19). The fix moved to HTML checks and added `--require-reality` for the scheduled run. |
| still don't know | Whether every future fail-open shape is covered. See EV-002. |
| state (delivery · visibility · evidence) | implemented · published · observed |
| evidence | primary: https://github.com/caty-ai/family-os/pull/1 ; related (different failure family): https://github.com/caty-ai/.github/pull/12 (hand-edited generated SVGs were detected as generator drift and resynced with determinism proof) |
| observed-at | 2026-08-12 |
| last-reviewed | 2026-08-12 |
| owner | maintainers |
| counter-evidence | none |

## EV-002 — The publication gate was deliberately broken on CI — red on a real violation, green everywhere else

| field | value |
| --- | --- |
| claim-id | EV-002 |
| believe | A gate you have never seen fail is not a gate. |
| built | `tools/check_publication_gate.py` has a denylist, a personal-URL allowlist, per-language label checks, an SVG scan, and a selftest with negative fixtures. |
| actually happened | Before commit, `README.md` was mutation-probed with an unlabeled module link: the gate failed on the exact line, then the file was restored byte-identical and verified by SHA-256. A synthetic-violation PR carrying a fictitious macOS home-directory path then produced a red `publication gate` run on CI and was closed unmerged. PR #32 records the probe matrix and a five-seat adversarial review (one seat advisory — same model family as the writer) that started 5/5 NO-GO and converged to GO over 3 rounds. |
| still don't know | Whether future leak shapes stay within the selftest matrix. |
| state (delivery · visibility · evidence) | implemented · published · observed |
| evidence | primary: https://github.com/caty-ai/family-os/pull/34 (red run); secondary: https://github.com/caty-ai/family-os/pull/32 (probe matrix + review record) |
| observed-at | 2026-08-12 |
| last-reviewed | 2026-08-12 |
| owner | maintainers |
| counter-evidence | none |

## EV-003 — The weekly reality check has run on schedule and passed

| field | value |
| --- | --- |
| claim-id | EV-003 |
| believe | This map rots silently unless something outside it checks it against reality on a clock. |
| built | `.github/workflows/family-links.yml` runs on pushes to main, on every pull request, and on Mondays at 08:00 JST with `--require-reality`. |
| actually happened | A scheduled run executed and passed registry vs GitHub reality, link resolution, and the footer contract. |
| still don't know | Long-run behavior. This scheduled lane is young. At writing, we have one scheduled run and no failure has exercised the auto-filed issue path. GitHub's default run-log retention (90 days) will thin the run's step detail around the same time this entry is due for re-review. |
| state (delivery · visibility · evidence) | implemented · published · observed |
| evidence | https://github.com/caty-ai/family-os/actions/runs/31341629945 |
| observed-at | 2026-08-12 |
| last-reviewed | 2026-08-12 |
| owner | maintainers |
| counter-evidence | none |

## EV-004 — Governed self-growth cycle — the mechanism is public; no cycle record is

| field | value |
| --- | --- |
| claim-id | EV-004 |
| believe | An agent may propose its own changes, but nothing is adopted without a human decision. |
| built | The mechanism is published. `caty-ai/self-growth-loop` ships propose, trial, council, and adopt scripts, templates, a ledger spec, and tests asserting no code path reaches adoption without approval. |
| actually happened | **No public primary record yet** — real cycle records live in a private runtime ledger and have not been published. |
| still don't know | Whether a real cycle record will be published. Until one is, this claim stays unverified by our own rule. |
| state (delivery · visibility · evidence) | implemented · published · **unverified** |
| evidence | mechanism only: https://github.com/caty-ai/self-growth-loop (published, MIT) |
| observed-at | 2026-08-12 |
| last-reviewed | 2026-08-12 |
| owner | maintainers |
| counter-evidence | none |

<!-- EV-005 (harness effect measurement) and EV-006 (multi-environment install verification) are reserved by the lanes of https://github.com/caty-ai/family-os/issues/43 and will be added when those lanes complete. Claim-ids are identifiers, not file order. -->

## EV-007 — The shared-memory horizontal layer ran across three environments and two runtimes, and the newest adoption was accepted on artifacts, not self-report

| field | value |
| --- | --- |
| claim-id | EV-007 |
| believe | A family of agents is only a family if what one member does is visible to the others without a human relaying it — across machines and across runtimes. |
| built | `caty-ai/family-memory-architecture` ships the horizontal layer: an append-only hot-inbox (helper-only posting with schema validation and a secrets scan), a deterministic digest generator, and a session-start read protocol. Per-member adoption is issue-tracked in `caty-ai/family-dev-handbook`. |
| actually happened | Three members on distinct environment/runtime combinations adopted the layer and their participation events round-tripped into the generated digest: Doc (OpenClaw, Linux VPS, 2026-07-26), Alec (Hermes, Mac mini, 2026-08-12), Caty (OpenClaw, Mac mini, 2026-08-14 — the product's mascot joining her own product). The Caty adoption was executed by the agent herself from a written brief, and acceptance used only independently read artifacts: event attribution in the posted JSON (`owner: caty`), the digest line regenerated on a different machine than the one that posted it, the config wiring itself, and persona files verified untouched. During the same run she reported that her own change worsened a pre-existing config-size budget overage and proposed a separately scoped fix rather than silently trimming unrelated content to hide it. |
| still don't know | All three adopters are the author's own family agents on author-controlled machines — independence is cross-model and cross-runtime, not cross-owner. Doc's adoption record predates the public handbook and lives in a private repo, so one of the three trails is not externally inspectable. The event files and the generated digest live in a private shared vault; what is public is the issue trail with the acceptance evidence quoted, not the artifacts themselves. |
| state (delivery · visibility · evidence) | implemented · published · observed |
| evidence | primary: https://github.com/caty-ai/family-dev-handbook/issues/50 (acceptance with cross-machine round-trip verification) and https://github.com/caty-ai/family-dev-handbook/issues/49 ; adoption trail: https://github.com/caty-ai/family-dev-handbook/issues/48 , https://github.com/caty-ai/family-dev-handbook/issues/36 , https://github.com/caty-ai/family-dev-handbook/issues/38 (Alec) ; mechanism: https://github.com/caty-ai/family-memory-architecture (published, MIT) |
| observed-at | 2026-08-14 |
| last-reviewed | 2026-08-14 |
| owner | maintainers |
| counter-evidence | none |
