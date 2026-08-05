# Family OS README visual system v4

Status: **canonical visual contract for the Family OS README family**. This is
a presentation contract, not an architecture or runtime contract. Exact
dependency meaning belongs in the README's adjacent Mermaid map and the text
next to it.

## v4 purpose and invariants

The brand Hero makes Family OS memorable as a map for growing AI families. It
does **not** encode an architecture graph. A globe is the ecosystem / map
metaphor, never a controller or authority; planets and satellites evoke
independent worlds and composed roles, never exact runtime edges.

- Family OS is a non-runtime map / pointer. Any dotted guide edge from it is
  navigation only, never a runtime dependency.
- Exact dependency truth appears in accessible Mermaid, nearby text, and the
  canonical technical documents—not in raster art.
- The Hero must not label modules, claim implementation status, or turn
  optional observation into functional authority.
- Family OS is published at `caty-ai/family-os` as free MIT OSS.

## Brand Hero

| Item | Fixed rule |
| --- | --- |
| Canonical README asset | `assets/readme/hero.png`, `1600 × 900 px`, 16:9 PNG |
| README placement | Immediately below the H1 and the line `AIを使い捨てず、ともに育つ家族へ。`, before the one-sentence value copy |
| Composition | Left approximately 38% contains the exact brand copy; right contains the planetary ecosystem |
| Style | Warm monochrome 1950s–60s overseas educational TV / CRT / halftone illustration; calm, editorial, optimistic |
| Central globe | A large globe for the ecosystem / map metaphor, not a command centre, controller, authority, registry, or hub |
| Other bodies | Medium planets and small satellites are evocative only; they do not encode exact module labels or dependencies |
| Raster text | Exactly: `FAMILY OS`; `A MAP FOR GROWING AI FAMILIES`; `caty-ai/family-os`; `FREE & OPEN SOURCE · MIT LICENSE` |
| Exclusions | No module labels, arrows, pipes, dependency diagram, dashboard, code UI, cyberpunk, robots, or Persona Engine visual imitation |

### Alt-text template

> Family OSのブランドHero。左に「FAMILY OS」「A MAP FOR GROWING AI FAMILIES」「caty-ai/family-os」「FREE & OPEN SOURCE · MIT LICENSE」の文字、右に温かいレトロTV風の惑星系がある。中央の大きな地球はAI家族を見渡す地図の比喩であり、周囲の独立した世界と組み合わせる衛星は役割の比喩である。画像だけで接続関係は示さず、正確な関係は後述のMermaid図と本文で説明する。

Alt text and nearby Markdown must explain that independent worlds and composed
satellites are metaphor only, then direct the reader to the later Mermaid map
for exact dependencies.

## Exact axis map

The README must place three accessible Mermaid maps, each in its own `##`
section so that no section carries more than one diagram. The Hero stays at the
top of the README; raster art is not the architecture map.

### First map — the three layers

Family Dev Handbook is **not a peer of the two axes**. It carries the shared
premises and rules that apply to everything below it, so it must be drawn as a
layer that **contains** the vertical and horizontal axes, never as a sibling
node and never with an arrow into them.

- containment expresses precedence; an arrow would read as the Handbook
  executing or driving the axes, which is false — it is a document, not a
  runtime;
- Family OS keeps a dotted navigation-only link to that layer and starts
  nothing.

### Second map — one agent's vertical axis

- every agent has its own Caty Agent Harness execution boundary, and that
  boundary is the **foundation of the vertical axis**: on its own it adds
  and accelerates a work-driven self-growth loop, which is why it is worth
  attaching to an existing runtime such as Hermes Agent or OpenClaw;
- two kinds of growth attach on top of that foundation and must stay visually
  separated: **persona growth** (Persona Engine adds the persona layer and its
  emotional gradation; Persona Growth Loop drives independent persona growth)
  and **ability growth** (X Collector gathers outside information; Self Growth
  Loop drives independent ability growth);
- Persona Engine and X Collector remain independently usable foundations;
- the Self Growth trial/result seam with Caty is implemented;
- Persona Growth's full-pipeline attachment remains planned, with Self Growth
  governance between it and Caty rather than a current direct Caty seam;
- X Collector supplies the current/default sense path through `family-feed`
  and morning agents, not a direct engine command, and remains replaceable;
- attributable human/evaluator input remains another possible Self Growth
  input.

### Third map — the family's horizontal axis

- each agent remains a complete vertical flow;
- FMA connects agents by carrying **information sharing and the means of
  coordination between family members**, without gaining member execution
  authority;
- Sitter watches **delegated sub-agent work and family-to-family nudges
  (message exchanges)** from the outside so that a handoff is not left stalled;
  it does not decide domain success or relay task authority;
- the Handbook must **not** appear in this map. Its rules are expressed by the
  first map's containing layer;
- Family OS has dotted navigation-only links and starts nothing.

The maps must preserve these facts:

| Subject | Required truth |
| --- | --- |
| Layer precedence | Family Dev Handbook sits above both axes as shared premises and rules, drawn by containment. It is never a third peer pillar and never drives the axes. |
| Vertical foundation | Caty Agent Harness is the foundation of the vertical axis. Standalone it adds a work-driven self-growth loop; persona growth and ability growth attach on top of it as separate branches. |
| Per-agent vertical axis | Caty Agent Harness is not one central family runtime. Each agent can have its own independent vertical execution/growth flow. |
| Family horizontal axis | FMA connects the independent agent flows through memory and information sharing; it does not own their mutable state or completion. |
| Standalone foundations | Caty Agent Harness, Family Memory Architecture, Sitter, Family Dev Handbook, X Collector, and Persona Engine each have an independently usable role. |
| X Collector | It is standalone public MIT OSS. It is the current/default Self Growth sense input through `family-feed` / morning agents, but is replaceable. |
| Persona Engine | It is standalone public MIT OSS. |
| Self Growth | The full trial loop has an implemented required dependency on Caty Agent Harness for trial execution. Attributable human/evaluator input is also possible. |
| Persona Growth | It is planned. The current sensor-only stage has no Caty engine seam. A future full loop depends on Self Growth governance and Persona Engine as persona source/target; Caty is transitive through Self Growth, not a current direct dependency. |
| Family Dev Handbook | It is the shared development-governance contract and the containing layer above both axes. Only mechanized rules may be described as enforced; the document is not a runtime. |
| Sitter | It independently supervises delegated sub-agent work and expected family nudges. A direct supervision contract with the Harness remains proposed, so the README must not draw it as an implemented dependency. |

### Repository links

Every module named in the README must link to its repository, including the
ones not yet published. Unpublished links carry an explicit `公開準備中`
marker in the adjacent text or table cell, and the README states once that
those links cannot be opened yet. Do not invent future organisation URLs for
repositories that have not moved.

| Module | Link target | State |
| --- | --- | --- |
| Caty Agent Harness | `caty-ai/caty-agent-harness` | published, MIT |
| Persona Engine | `caty-ai/persona-engine` | published, MIT |
| Sitter | `caty-ai/sitter` | published, MIT |
| Persona Growth Loop | `shojikumaru/persona-growth-loop` | 公開準備中 |
| Self Growth Loop | `shojikumaru/self-growth-loop` | 公開準備中 |
| X Collector | `caty-ai/x-collector` | published, MIT |
| Family Memory Architecture | `shojikumaru/family-memory-architecture` | 公開準備中 |
| Family Dev Handbook | `caty-ai/family-dev-handbook` | published, MIT |

### Superseded v3 map rules

The v3 two-part axis map is superseded. v3 drew Family Dev Handbook inside the
horizontal axis as one of the collaboration safeguards, which placed a rule
document at the same level as the runtime axes it governs. v4 lifts it into a
containing layer above both axes, names the Harness explicitly as the vertical
**foundation** with persona and ability growth attaching on top, sharpens
Sitter to delegated sub-agent work and family nudges, and requires repository
links for every named module.

### Superseded v2 map rules

The v2 symmetric node map and its single dependency Mermaid are superseded.
The brand Hero and social-preview assets are unchanged from v2 through v4.

## Social preview

| Item | Rule |
| --- | --- |
| Canonical social asset | `assets/readme/social-preview.jpg` |
| Exact export | Scale the `1600 × 900 px` master proportionally to `1280 × 720 px`, then remove `40 px` from both the top and bottom to make a `1280 × 640 px` vertical centre crop; solid background, under 1 MB |
| Copy safety | Keep the full four-line brand-copy block and the central globe inside the resulting cover export; crop decorative top/bottom outskirts only |
| Intended use | Set it in GitHub Settings → Social preview after public release. This platform setting is separate from the README's `hero.png`. |

The social-preview asset may be versioned at the canonical path above. Applying
it in GitHub Settings → Social preview is separate platform configuration and
remains deferred until public release.

## Derived child heroes

Derived child heroes preserve the title treatment, planetary system, warm
retro-TV style, and social-crop safe area. They may swap the repository
identifier and headline/subtitle for the child, and add one restrained halo to
orient the child within the family.

That halo must not imply a direct dependency, authority, implementation state,
or required install. Do not add a text annotation or label that could be read
as dependency meaning. Exact meaning stays in Mermaid and body text.

### Superseded v1 rules

The v1 seven fixed node coordinates, per-node palette, and raster node-label
rules are **superseded**. The raster Hero has no exact module labels,
positions, or dependency semantics. The brand Hero (unchanged since v2), the
v3 two-part axis map, and this document are canonical.

## Accessibility and verification

- The Hero has a solid, self-contained background and must remain distinct on
  light and dark surrounding surfaces.
- Inspect at `1600 px`, `800 px`, and `320 px`; meaning must survive without
  reading raster text because the alt text and Mermaid explain it.
- Inspect in grayscale: the globe, planets, satellite accents, and outer
  boundary must remain distinguishable by tone and shape.
- Verify that the Mermaid legend, plain-language table, and technical-document
  links express all dependency truth without relying on the illustration.
- Future regeneration must verify the four exact raster text strings and the
  social crop safe area.

## Accepted v2 asset verification (2026-07-27)

- [x] `assets/readme/hero.png` is an opaque `1600 × 900 px` master.
- [x] `assets/readme/social-preview.jpg` is the canonical `1280 × 640 px`
  social export and is under 1 MB.
- [x] The four exact strings are visually present in the master; OCR confirms
  the repository identifier and license line: `FAMILY OS`; `A MAP FOR GROWING
  AI FAMILIES`; `caty-ai/family-os`; `FREE & OPEN SOURCE · MIT LICENSE`.
- [x] The `0.8×` cover export and `40 px` top/bottom crop retain the title,
  central globe, repository identifier, and license line.
- [x] The master remains recognizable at `320 px` width.
- [x] The README's alt text, Mermaid map, and body copy preserve meaning when
  the image is unavailable.
- [x] GitHub Settings configuration, organisation transfer, and public
  visibility remain unperformed; this asset verification does not claim them.

## Accepted v4 map verification (2026-08-04)

- [x] The Hero and the tagline placement are unchanged from v2/v3.
- [x] Three Mermaid maps exist, each alone in its own `##` section.
- [x] The layer map draws Family Dev Handbook as a subgraph containing the two
  axes, with no arrow from the Handbook into either axis.
- [x] The vertical map labels Caty Agent Harness as the foundation carrying
  work-driven self-growth, with persona growth and ability growth as separate
  subgraphs above it.
- [x] The horizontal map no longer contains Family Dev Handbook, and shows
  Sitter watching delegated sub-agent work and family nudges.
- [x] All eight named modules link to their repositories; the five unpublished
  ones are marked `公開準備中` and the README says once that those links
  cannot be opened yet.
- [x] Implemented versus planned state is unchanged: Self Growth trial/result
  seam implemented, Persona Growth planned.

## Accepted v3 map verification (2026-07-28)

- [x] The Hero appears immediately below the title and tagline.
- [x] The vertical map states `1エージェントにつき1つ` on Caty Agent
  Harness and distinguishes the implemented Self Growth seam from the planned
  Persona Growth path through Self Growth governance.
- [x] The vertical map preserves X Collector as a replaceable current/default
  sense path and shows attributable human/evaluator input as another possible
  Self Growth input.
- [x] The horizontal map shows multiple complete agent flows connected by FMA
  without turning FMA into execution authority.
- [x] Handbook and Sitter are shown as collaboration safeguards, not Caty
  dependencies or domain-success authorities.
- [x] Both Mermaid blocks render successfully as PNG with the intended
  top-to-bottom and family-axis hierarchy.

## Known limitations

- The planetary system is a brand metaphor, not an architecture diagram.
- The current visual contract does not assert present public GitHub visibility,
  organisation transfer, or platform configuration for Family OS or X
  Collector.
- X Collector public release and Persona Growth full-loop implementation remain
  future work; their display must not imply otherwise.
