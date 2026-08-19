# Family OS README visual system v5

[← Back to the entrance](../README.md)

Status: **canonical presentation contract for the Family OS README family**.
This document is derived from the frozen Epic #24 contract. When sources
disagree, the priority order is **frozen contract → visual system v5 →
artifacts**.

## v5 purpose and invariants

The brand Hero makes Family OS memorable as a map for growing AI families. It
does **not** encode an architecture graph. A globe is the ecosystem / map
metaphor, never a controller or authority; planets and satellites evoke
independent worlds and composed roles, never exact runtime edges.

- Family OS is a non-runtime map / pointer. A dotted guide edge from it is
  navigation only, never a runtime dependency.
- Figures are explanatory views. Their adjacent Markdown tables are the
  semantic source of truth for the figure; module facts always come from
  `registry/modules.json`.
- Figures must not transfer authority, turn optional observation into control,
  or blend implemented, planned, and unknown claims.
- Family OS is published at `caty-ai/family-os` as free MIT OSS.
- The v4 requirement for **three Mermaid maps in the README is explicitly
  superseded**. v5 adopts shared SVG figures with Markdown sources of truth.

## Brand Hero

| Item | Fixed rule |
| --- | --- |
| Canonical README asset | `assets/readme/hero.png`, `1600 × 900 px`, 16:9 PNG |
| README placement | Immediately after the one-sentence value copy, which follows the H1 entrance routes and language line |
| Composition | Left approximately 38% contains the exact brand copy; right contains the planetary ecosystem |
| Style | Warm monochrome 1950s–60s overseas educational TV / CRT / halftone illustration; calm, editorial, optimistic |
| Central globe | A large globe for the ecosystem / map metaphor, not a command centre, controller, authority, registry, or hub |
| Other bodies | Medium planets and small satellites are evocative only; they do not encode exact module labels or dependencies |
| Raster text | Exactly: `FAMILY OS`; `A MAP FOR GROWING AI FAMILIES`; `caty-ai/family-os`; `FREE & OPEN SOURCE · MIT LICENSE` |
| Exclusions | No module labels, arrows, pipes, dependency diagram, dashboard, code UI, cyberpunk, robots, or Persona Engine visual imitation |

### Hero alt-text rule

Alt text and nearby Markdown must say that the independent worlds and
satellites are metaphor only, then direct the reader to the aggregate map and
its table for exact relationships. It must not present the central globe as a
runtime hub.

## Adopted figures and sources of truth

| Figure | Placement | Semantic source of truth | Required check |
| --- | --- | --- | --- |
| `assets/readme/family-map.svg` | `README.md` and the three translated READMEs, in “Rules on top, two axes below” | the adjacent three-layer Markdown table; module facts are derived from `registry/modules.json` | publication gate, registry check, XML/render inspection |
| `assets/readme/growth-stages.svg` | `README.md` and the three translated READMEs, in the growth section | `docs/growth-model.md` and the adjacent stage table | publication gate, registry check, XML/render inspection |
| `assets/readme/timeline.svg` | `README.md` and the three translated READMEs, immediately after “Grow it, don't rebuild it” | the adjacent time-band table; its classes are narrative classes, not delivery states | publication gate, registry check, XML/render inspection |
| `assets/readme/vertical-axis.svg` | `docs/engineering.md` and `docs/engineering.ja.md` | the adjacent node / role / relations / state table | publication gate, registry check, XML/render inspection |
| `assets/readme/horizontal-axis.svg` | `docs/engineering.md` and `docs/engineering.ja.md` | the adjacent node / role / relations / state table | publication gate, registry check, XML/render inspection |

`structure-simple.svg` is retired. The aggregate family map replaces it.

### Shared legend semantics

- **Solid** = implemented / published.
- **Dashed** = planned / preparing, including an explicitly named aspiration.
- **Orange** = focus, **not a state**.

Delivery, visibility, evidence, and license remain separate claims in prose and
tables. A colour or line style never overrides a table label. Preparing module
homes remain plain text with their preparation label; published module links
carry their visibility and license label on the same Markdown line.

### Text equivalent requirement

Every figure requires a text equivalent. The minimum is the adjacent Markdown
table, placed immediately after the image. Where topology benefits from an
executable representation, a `<details>` block may additionally preserve the
retired Mermaid source. Alt text must identify the figure's purpose and point
to the table rather than duplicating every relation.

This replaces v2's incorrect rationale that SVG “cannot be text-diffed.” SVG
is text. The real goals of the shared-figure policy are **reproducibility,
four-language parity, and verifiability**. One language-neutral asset plus a
translated Markdown source of truth serves those goals without a generated SVG
per language.

## Figure-specific contracts

### Family map

The rules layer contains the premises for both axes and never drives them. The
vertical zone shows one agent's Harness foundation, context equipment, and
separate persona and ability growth branches. The horizontal zone shows
complete agent flows connected by FMA while Sitter watches delegated work and
family nudges from outside. Persona Engine and X Collector remain independent
surfaces; drawing them near a shared boundary must not turn them into FMA
dependencies.

### Timeline

The four bands are deliberate readings, not predictions:

| Band | Narrative class |
| --- | --- |
| TODAY | an observed design choice |
| 2–5 years | a policy in effect |
| 20 years | a direction and aspiration |
| 100 years | a hypothesis |

The figure must include “narrative map — not an implementation-state display,”
and the adjacent table must carry an `as of` date.

### Growth figure

`growth-stages.svg` shows five stages and the I → WE boundary between stages 4
and 5. Stage 3 and stage 4 receive the orange focus treatment because they are
the current build focus; orange does not claim delivery. Stage 4 is dashed
because it is planned. Stage 5 is dashed because relationship growth remains
an aspiration even though some supporting parts exist.

The alt text must name the five-stage progression and the I → WE boundary,
state that delivery and evidence live in the adjacent table, and avoid inferring
status from colour alone.

### Detailed axis figures

The vertical figure preserves the implemented Harness ↔ Self Growth trial/result
seam, the current X Collector → morning agents → Self Growth input path, the
attributable alternative input, and the planned Persona Growth governance path.
The horizontal figure preserves complete per-agent flows, FMA's non-authority
connection, and Sitter's verdict-free observation of handoffs.

## Repository links

The table below is generated from [`registry/modules.json`](../registry/modules.json),
the canonical source for a module's home, visibility, and license. Do not edit
the generated block directly.

<!-- family:generated:repository-links:start -->
| Module | Link target | State |
| --- | --- | --- |
| Family Dev Handbook | `caty-ai/family-dev-handbook` | published, MIT |
| Caty Agent Harness | `caty-ai/caty-agent-harness` | published, MIT |
| context-kit | `caty-ai/context-kit` | published, MIT |
| Persona Engine | `caty-ai/persona-engine` | published, MIT |
| Persona Growth Loop | `caty-ai/persona-growth-loop` | published, MIT |
| X Collector | `caty-ai/x-collector` | published, MIT |
| Self Growth Loop | `caty-ai/self-growth-loop` | published, MIT |
| Family Memory Architecture | `caty-ai/family-memory-architecture` | published, MIT |
| Sitter | `caty-ai/sitter` | published, MIT |
<!-- family:generated:repository-links:end -->

## Deliberate palette split

Organisation terminal SVGs use a dark terminal palette. Repository diagrams
use the light `#f6f8fa` background, `#57606a` strokes, `#24292f` text, and
`#d97706` focus orange. This is a role distinction—organisation identity versus
repository explanation—not visual drift.

Repo diagrams must remain GitHub-safe: valid XML, no metadata blocks, no
scripts or embedded remote resources, language-neutral minimal English, and no
personal names. Module state words belong in adjacent Markdown tables, not in
per-node SVG labels.

## Social preview

| Item | Rule |
| --- | --- |
| Canonical social asset | `assets/readme/social-preview.jpg` |
| Exact export | Scale the `1600 × 900 px` master proportionally to `1280 × 720 px`, then remove `40 px` from both the top and bottom to make a `1280 × 640 px` vertical centre crop; solid background, under 1 MB |
| Copy safety | Keep the full four-line brand-copy block and the central globe inside the resulting cover export; crop decorative top/bottom outskirts only |
| Intended use | Set it in GitHub Settings → Social preview after public release. This platform setting is separate from the README's `hero.png`. |

## Derived child heroes

Derived child heroes preserve the title treatment, planetary system, warm
retro-TV style, and social-crop safe area. They may swap the repository
identifier and headline/subtitle for the child, and add one restrained halo to
orient the child within the family. That halo must not imply a dependency,
authority, implementation state, or required install.

## Accessibility and verification

- Every SVG has a meaningful `<title>` and `<desc>` referenced by
  `aria-labelledby`.
- Meaning survives at narrow widths and without colour; line style and the
  adjacent table carry semantics.
- The Hero is inspected at `1600 px`, `800 px`, and `320 px`; each repo diagram
  is rendered and inspected at its native viewBox and a narrow README width.
- Alt text names the diagram's purpose and directs the reader to its source-of-
  truth table.
- Each figure's node and relation set is compared against the adjacent table.

### Verification checklist

- [ ] `python3 -B tools/check_publication_gate.py`
- [ ] `python3 -B tools/check_registry.py --offline`
- [ ] `python3 -B tools/render.py --check`
- [ ] Parse every adopted SVG as XML and render it for visual inspection.
- [ ] Confirm every module name in an SVG has adjacent Markdown evidence with
      the registry-derived visibility and license label.
- [ ] Confirm each figure placement and source-of-truth table matches the
      adopted-figure matrix above.
- [ ] Confirm all four README languages use the same shared asset paths and the
      same structural figure order.

## Superseded contracts and known limits

v5 supersedes v4's three-Mermaid requirement, v3's two-part axis map, v2's
symmetric dependency map and SVG-diff rationale, and v1's fixed raster node
layout. The brand Hero and social-preview crop remain in force unless this
document changes them explicitly.

The planetary system remains a brand metaphor. The timeline remains a
narrative map. Shared SVGs do not claim that every planned module is published,
that every runtime supports every module, or that a future relationship outcome
will occur.
