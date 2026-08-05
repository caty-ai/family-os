# Family OS brand Hero v2 — reproducible image-generation brief

This file is the source prompt for `assets/readme/hero.png`. Follow the
canonical [visual contract](../../docs/readme-visual-system.md); the contract
wins if any wording differs.

## Output

- Generate an opaque `1600 × 900 px`, 16:9 PNG at
  `assets/readme/hero.png`.
- Keep the central composition safe for the existing canonical
  `assets/readme/social-preview.jpg`: scale the master proportionally to
  `1280 × 720 px`, then remove `40 px` from both the top and bottom for a
  `1280 × 640 px` vertical centre crop with a solid background, under 1 MB.
- This prompt freezes the crop requirements. GitHub Settings → Social preview
  configuration remains deferred until public-release work.

## Prompt

> Create a warm monochrome 1950s–60s overseas educational television illustration for a free, open-source project named Family OS. Use a calm CRT/halftone print texture, soft sepia-cream-charcoal palette, subtle film grain, rounded retro geometry, and an editorial, optimistic mood. Avoid cyberpunk, glossy SaaS dashboards, robots, humanoid characters, terminal/code windows, spacecraft bridges, and Persona Engine's visual style.
>
> Compose a `1600 × 900` hero with the left approximately 38% reserved for a clean, large four-line copy block, exactly and only: `FAMILY OS`; `A MAP FOR GROWING AI FAMILIES`; `caty-ai/family-os`; `FREE & OPEN SOURCE · MIT LICENSE`. Set the typography with a period-appropriate, highly legible condensed educational-TV title treatment. Do not add any other words, module names, labels, legends, URLs, status tags, or pseudo-text.
>
> On the right, show a planetary ecosystem: one large central globe, several medium independent planets, and a few small composed satellites. The globe represents an ecosystem map, never a central controller, authority, registry, hub, or runtime. The bodies are evocative metaphor only, not an exact dependency graph: no arrows, cables, pipes, orbit lines that look like data flow, module labels, or hierarchy. Keep the central globe and all four copy lines safe after the master is scaled to `1280 × 720` and cropped by `40 px` at both the top and bottom; only decorative outer texture may be cropped.
>
> The finished image must read equally well as a GitHub README hero on light or dark page backgrounds and as a social-preview crop. Use a solid image background, high tonal separation, and simple shapes that remain understandable at `320 px` wide.

## Negative prompt / exclusions

- No module names, dependency labels, extra text, legends, tags, or tiny
  explanatory copy beyond the exact four required text strings.
- No arrows, lines suggesting data flow, required connections, control beams,
  hub-and-spoke wiring, installer flow, or architecture diagram.
- No cyberpunk neon, control room, dashboard, code editor, robot, humanoid,
  photographic character, space battle, or Persona Engine visual imitation.
- No implication that `caty-ai/family-os` is already public; the printed
  identifier and license are an approved public target.

## Acceptance checklist

- [ ] `hero.png` is exactly `1600 × 900 px` and has a solid background.
- [ ] The raster contains exactly the four required copy strings and no module
  labels or explanatory text.
- [ ] The left copy block occupies roughly 38%; the planetary ecosystem is on
  the right and reads as a map metaphor, not a controller.
- [ ] Scaling the master to `1280 × 720 px` and cropping `40 px` from both the
  top and bottom retains the four-line copy block and central globe, has a
  solid background, and exports under 1 MB as `social-preview.jpg`.
- [ ] The image remains recognizable at `320 px`, in grayscale, and against
  light/dark surrounding backgrounds.
- [ ] README alt text, adjacent Mermaid, and body copy explain exact
  dependency truth without relying on the raster.
