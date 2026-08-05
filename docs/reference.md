# Family OS — full reference

[← Back to the entrance](../README.md) ｜ [← Engineering documentation](engineering.md)

This is the exact contract behind the map: who owns which fact, which edges exist, and what happens when evidence is missing. [The engineering page](engineering.md) explains the shape in prose; this page is the pinned version.

---

<a id="scope"></a>

## Scope and reading rules

This document is the **current contract**, not a decision log. It states what holds today.

Four rules govern how to read it.

- **One question, one authority.** Every exact question below has exactly one module that may answer it. Everyone else is an observer.
- **A pointer is not a copy.** Where this page names another module's contract, that module's repository remains canonical. A disagreement resolves in favour of the module, not this page.
- **A shape is not permission.** `proposed` rows describe a form that has been reasoned about. They do not authorise implementation, credentials, or a new consumer.
- **Absence is `unknown`.** When evidence does not arrive, the correct result is `unknown` or preserved local progress. It is never a synthesised success.

---

<a id="claim-states"></a>

## Claim states

| State | Means | You may build on it |
| --- | --- | --- |
| `implemented` | the interface exists today and is backed by evidence | yes |
| `decided` | an accepted boundary or practice | yes, as a boundary |
| `proposed` | shape only, no approved consumer | no |
| `unknown` | no fact may be inferred until the sole authority answers | no |

A `proposed` edge may not acquire a consumer until its contract owner records version negotiation, migration, and rollback or downgrade behaviour.

---

<a id="nodes"></a>

## Nodes

| Node | Class | Owns | May depend on | Must not depend on or become |
| --- | --- | --- | --- | --- |
| Family OS | non-runtime coordination | family policy, the logical map, pointers, rendered observation | read-only module and memory-bus output, out of band | runtime callback, registry, controller, secret store, liveness authority |
| Family Dev Handbook | non-runtime governance | issue, PR, worktree, handoff, and parallel-development rules | human and module process records | runtime state, monitoring, installation, architecture authority |
| Family Memory Architecture | runtime horizontal infrastructure | the memory bus; registered schedule expectation, check-in, provenance | bounded declarations and envelopes | a module's task, process, resource, or delivery meaning |
| Caty Agent Harness | runtime, vertical foundation | task meaning, state, attempt, retry, checkpoint, done-check, completion, dead-letter | explicit adapters and optional supervision evidence | a supervision verdict, map or handbook control, memory-bus task truth |
| Persona Engine | runtime, standalone | persona layers and emotion gradation | its own configuration | growth governance, task authority |
| Sitter | runtime, observation | local process and reply facts, dispatch-attempt evidence, delegated same-attempt restart | an explicit caller request | task, provider, delivery, or memory-bus authority |
| Self Growth Loop | runtime, application | proposal, governance, and adoption records; growth interpretation | harness terminal evidence; attributable human or evaluator input; future target receipts | owner identity authority, target-applied fact, metric fact, direct task writes |
| X Collector | runtime, optional input | collected external material | its own sources | growth adoption authority, task authority |
| Persona Growth Loop | planned frontend | minimised, idempotent proposal production | future growth intake only | direct harness, ledger, adoption, or scheduler authority |
| Owner | external authority | identity-critical authorisation | an attributable decision surface | substitution by a runtime module |
| Target owner | external authority | the apply and revert fact, and its credentials | an accepted request contract | state owned by the growth loop |
| Provider adapter owner | external authority | correlated remote status and cancel facts | the provider API | fabrication by the harness or Sitter |
| Consumer or transport owner | external authority | the actual receipt fact | the transport contract | a process exit interpreted as delivery |
| Metric source | external authority | metric observations | the measurement source | fabrication by the growth loop |
| Deployment operator | external authority | credentials, scheduler, break-glass, mechanism-owner declaration | the concrete deployment | a Family OS secret or control path |

Allowed dependency direction:

1. Non-runtime documents read pointers and facts out of band.
2. Runtime modules never require Family OS or the handbook to make progress.
3. Requests flow toward the module owning the next decision; evidence flows back without transferring authority.
4. The memory bus receives bounded infrastructure envelopes, never a module's mutable state.
5. Optional and proposed edges fail by preserving local progress or `unknown`.

---

<a id="authority"></a>

## Authority

Each exact question has one authoritative answerer. The final column is what you must record when the evidence does not arrive.

| Exact question | Sole authority | Permitted observers | Explicitly not authoritative | Missing-evidence posture |
| --- | --- | --- | --- | --- |
| What does this task mean? | harness | growth loop, via declared criteria | Sitter, memory bus, Family OS | task stays unresolved in the harness |
| Which attempt is current? | harness | Sitter, for the explicitly delegated attempt id | a Sitter restart counter, memory bus | do not advance the attempt |
| Should the task retry, complete, or go to dead-letter? | harness | growth loop may interpret the terminal result | Sitter, provider, receipt, memory bus | harness-owned pending or `unknown` |
| Did the local supervised process exit, stall, or emit the expected reply? | Sitter | the calling harness | harness terminal state, provider adapter | Sitter's local fact is `unknown` |
| Did Sitter perform the explicit same-attempt restart? | Sitter | harness | Sitter deciding a new attempt | no inferred restart or result |
| What is the correlated remote provider status or cancel result? | provider adapter owner | the calling harness | a process exit, Family OS | caller preserves remote status `unknown` |
| Did the consumer actually receive the item? | receipt or transport contract owner | the calling harness | process exit, provider completion, a Sitter reply observation | delivery stays `unknown` |
| Was a registered scheduled job expected, and did its check-in arrive? | memory bus | Family OS rendered observation | module task state, mechanism health | stale or missing, per the memory-bus contract |
| Which producer, host, source, transport, or destination generated the check-in? | memory-bus provenance plane, from declared identities | Family OS | a universal writer registry | legacy provenance is `unknown`; base liveness continues |
| Is the concrete helper mechanism installed, runnable, or rolled back? | the concrete mechanism owner | operator; the memory bus may observe its declared check-in | Family OS, the task domain, the generic memory-bus plane | mechanism health `unknown` or degraded |
| Is the registered schedule live? | memory bus | operator, Family OS view | helper health alone | schedule liveness `unknown` or stale |
| Is this document current according to its freshness metadata? | Family OS document plane | humans and agents | runtime health or liveness | mark the observation stale or `unknown` |
| What is the development workflow contract? | Family Dev Handbook | developers and agents | runtime modules | governance guidance unavailable |
| What proposal, quorum, or adoption record exists? | growth loop | humans and agents | persona modules, harness, Family OS | remain at the prior valid state or `unknown` |
| Did the owner authorise this identity-critical transition? | the owner, evidenced by a durable attributable reference | the growth loop records the reference | a flag or actor string, an agent relay without a reference | fail closed; authorisation `unknown` |
| Was the change adopted? | growth loop | the reconciled view | owner authorisation alone, target owner | adoption record `unknown` or pending |
| Did the target apply or revert the change? | target owner | growth loop, via a correlated receipt | an adoption record, harness task completion | applied or reverted stays `unknown` |
| What metric value was observed? | metric source | the growth loop's evaluation protocol | fabrication by the growth loop | metric `unknown` |
| Was the adopted change effective? | the growth loop's evaluation protocol, using metric-source facts | humans and agents | adopted or applied alone | effectiveness `unknown` or pending |
| Who owns credentials, scheduler, and break-glass here? | the declared deployment operator | the concrete module or mechanism | Family OS, the handbook, the generic memory-bus plane | the operation fails closed |

---

<a id="vocabulary"></a>

## Ambiguous words, split

Seven words cause most cross-module confusion, because each one sounds like a single fact and is actually several. Each has exactly one owner.

| Word | Owned by | Commonly mistaken for |
| --- | --- | --- |
| `returned` | the provider adapter owns the remote result; Sitter may report only a local reply observation; the harness owns task interpretation | any one of the three standing for the other two |
| `ack` | the transport receipt owner owns consumer acknowledgement; the memory bus owns only its own check-in receipt | one acknowledgement covering both |
| `delivered` | the consumer or transport owner | a process exit, or a provider terminal state |
| `healthy` | the mechanism owner for mechanism health; the memory bus for registered schedule liveness; Family OS only for document freshness | one health signal covering the system |
| `adopted` | the growth loop's governance record | the target having changed |
| `applied` | the target owner | an adoption record |
| `effective` | the growth loop's evaluation protocol, using metric-source facts | adopted, or applied |

---

<a id="interfaces"></a>

## Interfaces

| State | Producer → interface → consumer | Contract owner | Forbidden interpretation | Absence posture |
| --- | --- | --- | --- | --- |
| `decided` | module repository → evidence pointer, out of band → Family OS | the module owns the result; Family OS owns the pointer slot | Family OS copying a module spec, or becoming a runtime callback | pointer stale or `unknown`; the module keeps running |
| `decided` | Family OS → policy, map, pointer, observation → humans and agents | Family OS | any runtime command, registry, secret, or liveness verdict | visibility degrades; runtime unaffected |
| `decided` | handbook → development-governance documents → developers and agents | the handbook | runtime monitoring, installation, or state-map truth | development coordination degrades |
| `decided` | registered runtime or helper → check-in and provenance envelope → memory bus | the memory bus owns the envelope; the producer owns its identity assertion | a module task, resource, write target, credential, or destructive authority | a legacy identity means provenance is `unknown`; base liveness is unchanged |
| `decided` | memory bus → additive read-only observation → Family OS | the memory bus owns the source fact; Family OS owns the rendering | any Family OS write or control path; any authority transfer | the Family OS view is stale or `unknown`; the memory bus continues |
| `implemented` | growth loop → `tr-enqueue` task request → harness | the harness's public enqueue contract | the growth loop writing task state, attempt, retry, or dead-letter | the trial stays pending; an enqueue rejection stays visible |
| `implemented`, read-only | harness → terminal artifact → growth loop | the harness owns the terminal fact; the growth loop owns the interpretation | terminal meaning adopted, applied, or effective | growth evaluation stays pending or `unknown` |
| `proposed`, no consumer | harness → versioned supervision request → Sitter | unassigned; the harness owns task and attempt semantics, Sitter owns accepted local-supervision semantics only | Sitter creating attempts, retrying, completing, or dead-lettering | the harness uses its local posture; no external supervision |
| `proposed`, no consumer | Sitter → verdict-free mechanical evidence → harness | unassigned until the request contract is approved | any `done`, provider-success, delivery, retry, or dead-letter verdict from Sitter | the harness preserves evidence `unknown` and applies its own policy |
| `proposed`, runtime absent | persona or sensor → minimised idempotent proposal → growth loop | unassigned; the growth loop owns intake semantics, the source owns supplied content | a raw private stream, a direct harness or ledger write, implicit authorisation | no proposal; the growth loop continues |
| partially `implemented` | evaluator, owner, or sensor → bounded attributable input → growth loop | the input author owns the input; the owner owns identity-critical decisions; the growth loop owns the record | an actor string or a relay standing in for owner authorisation | missing or legacy authorisation stays `unknown`; identity-critical transitions fail closed |
| `proposed` | growth loop → correlated apply or revert request → target owner | unassigned per target; the target owns apply semantics | a request counting as applied, or granting target credentials | the growth loop stays adopted or apply-pending; the target is unchanged |
| `proposed` | target owner → correlated apply or revert receipt → growth loop | the target owner, under its future public contract | the growth loop synthesising a receipt or mutating target state | applied or reverted stays `unknown`; no false reconciliation |
| `proposed`, conditional | metric source → metric facts → the growth loop's evaluation protocol | unassigned; the source owns the fact, the growth loop owns the declared evaluation | adopted or applied alone counting as effective | effectiveness stays `unknown` or pending |
| `decided` | target release contract → install, check, rollback request → helper mechanism | the target owns the release contract; the mechanism owner owns helper semantics | a helper reinterpreting domain semantics, or becoming a central controller | fail or roll back with a receipt; target state is not reinterpreted |
| `decided` | helper mechanism → receipt and health evidence → operator | the mechanism owner owns the evidence; the operator owns custody | a receipt counting as domain success, task completion, or schedule liveness | the operator sees degraded or `unknown`; no fabricated success |
| conditional | provider adapter → correlated remote status or cancel fact → harness | unassigned; the adapter owns the remote fact, the harness owns task-policy interpretation | a process exit or reply standing in for remote-provider truth | the caller keeps remote state `unknown` and applies harness policy |
| conditional | consumer or transport → correlated receipt → harness | unassigned; the receipt owner owns the delivery fact | a provider terminal, a local exit, or a Sitter reply counting as delivery | delivery stays `unknown` and stays owned by the contract |

---

<a id="forbidden"></a>

## Forbidden non-edges

These edges do not exist and may not be added. Each one, if drawn, would convert an observation into control.

- Family OS → any runtime module
- Family Dev Handbook → any runtime module
- a persona module → the harness or any ledger
- Sitter → memory-bus task status, or a harness task verdict
- the memory bus → a module's mutable state
- the growth loop → a target's internal state (only a future public request is permitted)
- repository separation → authority (splitting a repository grants nothing)

---

<a id="removal"></a>

## Removal invariants

- Removing Family OS removes coordination visibility, not runtime state.
- Removing the handbook removes governance guidance, not runtime operation.
- Removing the memory bus loses memory and check-in observation; each module's domain state remains.
- Removing Sitter disables optional external supervision; the harness keeps task semantics and uses its local failure posture.
- Removing the growth loop leaves harness tasks and evidence intact, and removes only growth governance.
- Removing a helper mechanism must not rewrite target or domain facts.

---

<a id="unknown"></a>

## The unknown posture

Every unassigned owner, consumer, schema, migration, rollback, and downgrade behaviour stays unassigned until its named authority records a public contract. This page cannot resolve those. Neither can the map.

That is deliberate. A map that resolves unknowns on the module's behalf is how a coordination plane quietly becomes a controller — and how a system starts reporting success it never observed.
