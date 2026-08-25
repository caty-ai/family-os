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

<!-- The multi-environment install verification record will be added under a NEW claim-id (EV-008 expected) after https://github.com/caty-ai/family-os/issues/45 and https://github.com/caty-ai/family-os/issues/46 complete. Claim-ids are identifiers, not file order. -->
<!-- EV-008 stays reserved for that install verification. The caty-agent-harness rig separately runs an experiment NAMED "EV-008" (overflow sentinel); this ledger records that experiment as EV-009 — the two are different claims and must not be merged. -->

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

## EV-005 — A pre-product instrument test measured one gate in isolation, and the result was null

| field | value |
| --- | --- |
| claim-id | EV-005 |
| believe | Measure the instrument before trusting it to measure the product, and publish the null when the hypothesis is not supported. |
| built | A purpose-built experiment wrapper measured exactly one mechanism before the product: the completion-declaration gate; the design was sealed and pre-registered, and 270 runs were executed across 3 arms. |
| actually happened | EV-005 did not test the caty-agent-harness product: the primary result was not confirmed at +5.6 pt, p = 0.234, on a task bundle later judged miscalibrated for the subject model; the product machinery was never exercised, with attempts/run = 1.0 in all arms and the retry machinery never firing once in 270 runs. |
| still don't know | Whether the completion-declaration gate helps under better-calibrated tasks; all runs were on author-controlled environments; the experiment used a single subject model. |
| state (delivery · visibility · evidence) | implemented · published · observed |
| evidence | primary: https://github.com/caty-ai/caty-agent-harness/issues/63 (final comment = scope clarification, 2026-08-18) |
| observed-at | 2026-08-20 |
| last-reviewed | 2026-08-20 |
| owner | maintainers |
| counter-evidence | The primary hypothesis was not supported: +5.6 pt, p = 0.234. |

## EV-006 — The first true product test improved verified completion on context-overflowing work, with limitations stated

| field | value |
| --- | --- |
| claim-id | EV-006 |
| believe | The full product should be tested as installed under sealed, machine-scored conditions, and the limitations should be published alongside the win. |
| built | Sealed, pre-registered, machine-scored: corpora/graders/runners hash-sealed BEFORE the runs (SEAL-MANIFEST, 185 files, sha256 f31e9af8…); 105 sequences run to completion; subject model Claude Haiku 4.5; arms: bare vs full product install (install.sh) plus a naive-retry control. |
| actually happened | On the pre-registered M/L context-overflow sizes pooled task_resolved primary, bare 4/30 (13%, CI 5–30%) vs harness 13/30 (43%, CI 27–61%), effect +30 pt, CMH exact p = 0.0079; unread completion claims measured against tool-call transcripts at M/L collapsed from bare 222/226 (98%) to harness 2/26 (8%); time and cost at M/L were roughly half (M 2.3 h → 1.3 h, L 3.9 h → 2.3 h; tokens M 122M → 50M, L 241M → 98M); honest negatives remained: S size showed no advantage with bare 10/15 (67%) vs harness 9/15 (60%), CSV genre p3 was 0/10 in both arms, wrong-answer rates did not improve at bare 22–31% vs harness 24–38%, unsupported quotes were higher under the harness at 166 vs 138, and half of the harness's overflow-size deliveries still failed verification, so what collapsed was specifically the unread completion claim, not wrongness in general. |
| still don't know | Only a single model lane (Haiku 4.5) has been run so far; the runs were on author-controlled machines; both arms were restricted to Read/Glob/Write (no search), so the result does not extrapolate to search-enabled operation. |
| state (delivery · visibility · evidence) | implemented · published · observed |
| evidence | primary: https://github.com/caty-ai/caty-agent-harness/issues/100 (final comment = full run result, 2026-08-19) ; published analysis page: https://github.com/caty-ai/caty-agent-harness/blob/main/docs/benchmark.md |
| observed-at | 2026-08-20 |
| last-reviewed | 2026-08-20 |
| owner | maintainers |
| counter-evidence | EV-005 is the preceding instrument-level null; in the product test, S size showed no advantage with bare 10/15 (67%) vs harness 9/15 (60%), p3 was 0/10 in both arms, wrong-answer rates did not improve at bare 22–31% vs harness 24–38%, and unsupported quotes were higher under the harness at 166 vs 138. |

## EV-009 — Adaptive activation (overflow sentinel) was pre-measured per model under seal, and the default-on decision was published with its limits

| field | value |
| --- | --- |
| claim-id | EV-009 |
| rig experiment name | **EV-008** — the harness-side pre-registration, seal, and every published page use the name "EV-008"; this ledger's EV-008 is reserved for the multi-environment install verification (see the comment above EV-007), so the sentinel experiment is recorded here as EV-009. |
| believe | Whether a mechanism should be on by default is a measurable question, and it should be measured per model — with the decision rule registered before the runs — rather than decided by taste after shipping. |
| built | A sealed, pre-registered experiment on the harness's overflow sentinel (adaptive activation: fire only when the measured per-turn context level crosses a threshold, then decompose the job before the context overflows). Per model: 4 sealed cells (M/L sizes × 2 instances), arms bare / always-on harness / sentinel, 20 hidden-key questions per cell; numbers regenerated deterministically from the primary ledgers (`step5-reconcile.py`, 2026-08-25). |
| actually happened | Default-on GO was declared on 2026-08-25 on four pre-registered conditions: codex fire rate 0 (0/127 turns; rule-of-three 95% upper bound 2.4%/turn) · codex tap-overhead GM 0.9944 ≤ 1.05 · claude-sonnet-5 all-pair median token ratio 0.801 < 1.0 (best cell −71%) · no consistent harmful false-fire (1/4 pairs only). Search-type runtimes never fired — by design (qwen adds 0 fires across ≈770 sentinel turns); grok-4.6 fired correctly on 4/4 cells at 20/20 correctness but never paid (median sentinel/bare 2.145) — firing is not the same as paying. |
| still don't know | The codex condition FAILed first: M4 (n=1 per pair) came out at GM 1.337 and was sent back per protocol; the passing 0.9944 comes from M4′ (n=3 per M-tier pair, a data-informed post-design sealed via a 3-seat delta review) — the FAIL is history to carry, not to erase. The sonnet stretch goal (< 0.8) was missed at 0.801. Standard cells are n=1 per pair; between-run SD ≈ 30–40% of the mean at M-tier, so 0.9944 is "inside the threshold", not "clearly below it". The product implementation is not yet shipped: this is a pre-measurement of the mechanism on an experiment rig, not a measurement of a shipped feature. All runs were on author-controlled machines. |
| state (delivery · visibility · evidence) | implemented · published · observed |
| evidence | primary: https://github.com/caty-ai/caty-agent-harness/issues/159 (final comment = GO report, 2026-08-25) ; published analysis: https://github.com/caty-ai/caty-agent-harness/blob/main/docs/benchmark.md#ev-008 ; published docs: https://github.com/caty-ai/caty-agent-harness/pull/176 and https://github.com/caty-ai/caty-agent-harness/releases/tag/v0.14.1 |
| observed-at | 2026-08-25 |
| last-reviewed | 2026-08-25 |
| owner | maintainers |
| counter-evidence | M4 (codex, n=1) FAILed the tap-overhead condition at GM 1.337 before M4′ (n=3) passed at 0.9944; grok-4.6 fires correctly but never pays (median sentinel/bare 2.145), so default-on is not recommended there; the sonnet stretch goal (< 0.8) was missed at 0.801. |
