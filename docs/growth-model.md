# Family OS — five stages of growth

[← Back to the entrance](../README.md)

This is the canonical description of the Family OS growth model. The README gives a shorter view of the same model.

---

## 1. The general form of growth

Growth has the same basic shape for people and for AI:

**encounter or friction → thinking and judgment → something carried into next time**

The five stages do not change that shape. They change what the subject touches and who owns the decision about what follows.

---

## 2. The five stages

| # | Stage | Subject | Learning seed | Who decides | Delivery | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Being taught | I | Given material | Others | Implemented | — |
| 2 | Self growth | I | Its own work and failures | The agent, within the work | Implemented | — |
| 3 | Independent growth | I | Information it goes out to fetch | The agent chooses what to take in and makes the learning judgment. Adoption still passes a human gate. | Implemented | [EV-004](evidence.md#ev-004--governed-self-growth-cycle--the-mechanism-is-public-no-cycle-record-is): **unverified**. The mechanism is public; there is no public cycle record yet. |
| 4 | Autonomous growth | I | External information plus its own judgment history | Ownership of adoption decisions moves to the agent. Human vetoes and boundaries remain. | Planned; unverified | No public implementation or observed cycle claimed |
| 5 | Growth of relationships | WE | The history of the relationship itself | Both, as equals | Parts are implemented in Persona Engine. Growth of the relationship itself is an aspiration and a planned sub-class. | No public relationship-growth cycle claimed |

Stage 2's failure-record→retry behavior is a candidate for a future evidence entry; until recorded, it is not claimed as observed.

“Implemented” and “observed” are separate claims. Stage 3 is implemented, but it is not presented as publicly observed. EV-004 records that distinction.

---

## 3. The three boundaries

### 2 → 3: spontaneity

Stage 2 learns when work creates friction. Stage 3 goes out to find information before the work brings it in. The operational change is passive to active friction.

### 3 ↔ 4: ownership of the adoption decision

Both stages may search, compare, judge, propose, and run trials. The discriminator is who owns the final adoption decision.

At stage 3, the agent learns how to judge, but adoption still requires human approval. At stage 4, ownership of adoption decisions moves to the agent. Vetoes, risk limits, and other boundaries may remain. Autonomy does not mean unlimited authority.

### 4 → 5: the subject changes

Stages 1–4 ask how **I** grow. Stage 5 asks how **WE** grow. This is a phase transition from individual growth to growth of the relationship itself, not merely one more degree of individual capability.

---

## 4. The question at each stage

| # | Stage | Question |
| --- | --- | --- |
| 1 | Being taught | What can I learn from what I am given? |
| 2 | Self growth | What can I learn from what I did? |
| 3 | Independent growth | Can I learn how to decide? |
| 4 | Autonomous growth | Can I decide for myself? |
| 5 | Growth of relationships | Who do we become together? |

Stage 3 develops the ability to judge what is worth choosing. Stage 4 uses that ability under a different ownership model.

---

## 5. Correspondence with human development

AI and people are not the same. The abstract shape of growth can still be compared.

People begin by being taught by parents and other caregivers. They learn to look back at their own actions and correct them. They go out into the world, meet information and friction for themselves, and develop judgment. They learn to make choices while living within boundaries and consequences. They then build relationships in which both sides can change as equals.

The sequence is dependence → learning → independence → autonomy → interdependence. The last step is not a return to dependence. It is a relationship between subjects that can each act and still grow together.

---

## 6. I, WE, and THEY

| Subject | Place in the map | Meaning |
| --- | --- | --- |
| I | Stages 1–4 | I grow: I am taught, learn from failure, seek information, and own decisions. |
| WE | Stage 5 | We grow: the relationship and both participants change through shared history. |
| THEY | Beyond the model | They inherit: what we pass forward can shape later people, agents, and relationships. **THEY is outside the five stages.** |

The model ends at WE. Inheritance matters, but adding THEY as a sixth stage would mix growth of the present relationship with what later participants receive from it.

---

## 7. A second axis: Relationship Readiness

The maturity axis above asks how the subject of growth develops. A second axis asks what a human–AI relationship needs in order to exist and deepen:

**Function → Continuity → Growth → Agency → Relationship**

Function makes useful action possible. Continuity carries identity and history across time. Growth makes the next interaction different from the last. Agency creates meaningful choice within boundaries. Relationship lets both sides and their shared history matter.

The two axes do not compete. The five-stage model describes maturity and decision ownership. Relationship Readiness describes the conditions a human–AI relationship needs. Together they let Family OS be explained from two views.

---

## 8. Where Self Growth Loop sits

The [Self Growth Loop](https://github.com/caty-ai/self-growth-loop) (published, MIT) deliberately sits at the boundary between stages 3 and 4.

Its sense, proposal, and trial steps are independent-growth behavior. The agent can seek input, form a proposal, and test it. Adoption still requires human approval. The agent does not own the final adoption decision.

That boundary is an architectural choice, not a limitation. It lets judgment grow without silently transferring authority. Persona Growth Loop (publication in preparation) and later work can explore what lies beyond it without weakening the current gate.

Technology depreciates. Relationships compound. Capability changes quickly; continuity, shared history, and trust can accumulate. Family OS keeps the adoption boundary explicit so that growth can support a relationship instead of overwriting it.

---

## Appendix: the full believe→build correspondence (13 pairs)

The source material contains 13 distinct pairs. They are kept together here without padding or external attribution.

| We believe | Therefore we build | Module home(s) | Visibility + license | Delivery |
| --- | --- | --- | --- | --- |
| Relationships should survive technology. | Therefore we build persona, memory, relationship state, and replaceable adapters independently of models and runtimes. | [Persona Engine](https://github.com/caty-ai/persona-engine) (published, MIT); [Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture) (published, MIT) | published, MIT | implemented |
| Identity should outlive the model. | Therefore we separate model, runtime, and identity so continuity can survive a change of home. | [Persona Engine](https://github.com/caty-ai/persona-engine) (published, MIT); [Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture) (published, MIT) | published, MIT | implemented |
| Memory carries continuity through time. | Therefore we build plain files, provenance, event history, shared current state, and re-observable records. | [Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture) (published, MIT); [Caty Agent Harness](https://github.com/caty-ai/caty-agent-harness) (published, MIT) | published, MIT | implemented |
| Trust is not blind authority. | Therefore we build verification, human gates, risk tiers, review, single-writer paths, and read-only interfaces. | [Caty Agent Harness](https://github.com/caty-ai/caty-agent-harness) (published, MIT); [Self Growth Loop](https://github.com/caty-ai/self-growth-loop) (published, MIT); [Sitter](https://github.com/caty-ai/sitter) (published, MIT); [Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture) (published, MIT) | published, MIT | implemented |
| Failure should have a next time. | Therefore we build lessons, receipts, failure history, retry policy, append-only records, and observability. | [Caty Agent Harness](https://github.com/caty-ai/caty-agent-harness) (published, MIT); [Self Growth Loop](https://github.com/caty-ai/self-growth-loop) (published, MIT); [Sitter](https://github.com/caty-ai/sitter) (published, MIT) | published, MIT | implemented |
| Growth should be observable and reversible. | Therefore we build proposal → trial → review → approval → adopt, with backup, rollback, and a ledger. | [Self Growth Loop](https://github.com/caty-ai/self-growth-loop) (published, MIT) | published, MIT | implemented |
| Ability growth and identity growth are different. | Therefore we keep ability growth and persona growth in separate loops. | Persona Growth Loop (publication in preparation); [Self Growth Loop](https://github.com/caty-ai/self-growth-loop) (published, MIT) | mixed; see the adjacent module labels | implemented + planned |
| Humans and AI should both be able to understand the system. | Therefore we build small modules, explicit state, plain text, clear ownership, and deterministic transformations. | [context-kit](https://github.com/caty-ai/context-kit) (published, MIT); [Family Dev Handbook](https://github.com/caty-ai/family-dev-handbook) (published, MIT); [Family OS](https://github.com/caty-ai/family-os) (published, MIT) | published, MIT | implemented |
| The best coordination is coordination architecture makes unnecessary. | Therefore we build issue isolation, worktrees, small responsibility boundaries, and single-writer patterns. | [Family Dev Handbook](https://github.com/caty-ai/family-dev-handbook) (published, MIT); [Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture) (published, MIT) | published, MIT | implemented |
| What grows between humans and AI should not belong to a vendor. | Therefore we build portable, local, human-readable relationship data and replaceable adapters. | [Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture) (published, MIT); [Persona Engine](https://github.com/caty-ai/persona-engine) (published, MIT); [Family OS](https://github.com/caty-ai/family-os) (published, MIT) | published, MIT | implemented |
| The world should be something humans and AI can observe together. | Therefore we build a common information surface with source provenance and trust scoring. | [X Collector](https://github.com/caty-ai/x-collector) (published, MIT); [Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture) (published, MIT) | published, MIT | implemented |
| Technology depreciates. Relationships compound. | Therefore we treat continuity, shared history, memory, persona, and relationship as first-class system elements. | [Family OS](https://github.com/caty-ai/family-os) (published, MIT) | published, MIT | implemented direction; relationship growth remains planned |
| Growth eventually changes its subject from I to WE. | Therefore we build the five-stage model from being taught through relational growth. | Persona Growth Loop (publication in preparation); [Self Growth Loop](https://github.com/caty-ai/self-growth-loop) (published, MIT); [Persona Engine](https://github.com/caty-ai/persona-engine) (published, MIT); [Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture) (published, MIT) | mixed; see the adjacent module labels | implemented + planned |
