# Family Footer Contract

The family footer is one generated region per declared root `README*.md` in sibling repositories. Literal generated marker lines may appear in documentation only inside fenced code blocks.

The v3.2 content amendment adds the Family OS map row and a leading axis column to the full-module table. The v3.3 amendment fixes the block's placement (below, trialled on sitter and owner-approved). The v3.4 amendment lets the map repository render the same table into its own README (the `family-table` block) with the map row bold and unlinked — member-repo footers are unchanged. The v3.5 amendment allows a repository with a hand-written family section to host the block inside that section — heading, member prose, generated table, then connecting prose (owner-approved, first applied on FMA); the byte-exact comparison is position-independent either way. The v3.6 amendment adds the separately enforced `org-profile-modules` block for the caty-ai organization profile. Existing member-footer rendering and enforcement remain unchanged.

## Markers

```html
<!-- family:generated:family-footer:start -->

---

{intro with {map} replaced by [Family OS](https://github.com/<map_repo>)}

| Axis | Module | What it does | State |
| --- | --- | --- | --- |
| Map | [Family OS](https://github.com/<map_repo>) | {map tagline for this language} | {published status label for this language} |
| Rules | **Host Module** | {tagline for this language} | {status label for this language} |
| Vertical · foundation | [Published Foundation](https://github.com/<repo>) | {tagline for this language} | {status label for this language} |
| Horizontal | **Preparing Module** | {tagline for this language} | {status label for this language} |

<!-- family:generated:family-footer:end -->
```

- The block id is `family-footer`.
- The content inside the region always has a leading blank line and a trailing blank line.
- The renderer preserves the start marker's newline bytes and compares only the bytes between the markers.
- Placement (v3.3): the block sits directly below the repository's learn-more section — the part that points readers deeper — and above any acknowledgements, hand-written family prose, and the License section. The byte-exact comparison itself is position-independent; this is the layout convention every family README follows, and the position new repositories adopt at publication. Exception (v3.5): a repository with a hand-written family section (e.g. FMA's "Part of Family OS") may host the block inside that section, after the member prose and before the connecting prose.

## Content

- The first data row is always the Family OS map. In member-repo footers its name is always linked to `https://github.com/<map_repo>`, including when there is no host module to exclude. Exception (v3.4): when the map repository renders this table into its own README via the `family-table` block, the map row is bold and unlinked — the same host-row convention the member repositories follow. Its axis label, localized tagline, and published state come from `footer_text.axis_map`, `footer_text.map_tagline`, and `status_labels.published`; its uniform display name comes from `footer_text.map_name`.
- The remaining rows contain every registry module in registry order, including modules still being prepared and the repository hosting the footer. Registry order is the display order: it encodes rules first, then the vertical axis with its foundation first, then the horizontal axis with its foundation first.
- Each module declares `axis.group` as `rules`, `vertical`, or `horizontal`, and `axis.foundation` as a boolean. The localized axis cell comes from `footer_text.axis_rules`, `footer_text.axis_vertical`, or `footer_text.axis_horizontal`; a true foundation flag appends `footer_text.axis_foundation_suffix`.
- The axis column mirrors the Family OS three-layer structure: rules sit above the vertical and horizontal axes beneath them. The map row represents the whole structure rather than one of those module layers.
- A published module name links to its repository, except that the host row is bold and unlinked. A preparing module name is also bold and unlinked, so the footer shows the full map without shipping an intentional `404` link.
- The localized description comes from the module's required `tagline` registry field. Every tagline must define every registry language.
- The localized state comes directly from `status_labels`; module `note` fields are not rendered.
- The four localized headers come from `footer_text.table_axis`, `footer_text.table_module`, `footer_text.table_what`, and `footer_text.table_state`.
- Every new `footer_text` section (`table_axis`, `map_name`, `axis_map`, `axis_rules`, `axis_vertical`, `axis_horizontal`, `axis_foundation_suffix`, and `map_tagline`) must define every registry language.
- Header, axis, map-name, module-name, tagline, and status-label cells fail validation if they contain a pipe or newline, rather than emitting a malformed Markdown table.

## Declared Files

- Default set: `README.md` for English, plus `README.<lang>.md` for every other declared language.
- `readme_overrides` replaces one default language file with an alias such as `README.zh-CN.md -> zh`.
- `readme_files` replaces the whole set. This is an explicit reviewed reduction for a repo that truly ships fewer README languages; it is never a convenience escape for a missing remote file.
- Filenames are repo-root `README*.md` only and must resolve to a declared language.

## Enforcement

The weekly content check reads every declared README of every published module, whether or not the footer flag is set.

1. Markers present and `footer: false`: fail with `footer exists but is not enforced`.
2. Markers present and `footer: true`: the generated bytes must match exactly.
3. Markers missing and `footer: true`: fail.
4. No markers anywhere and `footer: false`: fail with `published module has no footer`.

- A declared remote file returning `404` is a failure.
- Network failure, `403`, `429`, or `5xx` is a degraded skip; `--require-reality` rejects any degraded run with the shared degraded failure.
- A published module is retired by changing its status and setting `footer: false` in the same registry PR.

## Publication Runbook

1. Merge the family-os registry PR with the publication data and declared README set.
2. Run `python3 -B tools/family_footer.py render-all --checkouts <dir>`.
3. Open the mechanical sibling PRs with the generated footer updates.
4. After those PRs merge, run the workflow manually with `workflow_dispatch` so the scheduled content check goes green the same day.

- Sibling-first ordering is mandatory. Flip-first makes the scheduled check fail immediately on `footer:true` plus missing markers, while sibling-first is only stale until the flag PR closes the rollout.
- The rollout window is deliberately red after Epic #0 merges and before the flag flip PR lands. That red state is the reminder that the map and the published siblings are still being brought into sync.

## v3.6 Organization Profile Amendment

The org profile uses a second block id, `org-profile-modules`, owned by `tools/family_footer.py`. It renders the localized ecosystem intro and the complete bullet list from `registry/modules.json`: the Family OS map first, then every module in registry order. Published module names link to the module's declared `repo`; preparing names remain bold and unlinked. The open count is rendered as digits and is always the number of published modules plus one for the map.

```html
<!-- family:generated:org-profile-modules:start -->

{localized ecosystem intro with {count} replaced by digits}

- **[Family OS](https://github.com/<map_repo>)** — {localized map description}{localized published label}
- **[Published module](https://github.com/<module repo>)** — {localized description}{localized published label}
- **Preparing module** — {localized description}{localized preparing label}

<!-- family:generated:org-profile-modules:end -->
```

Like the member footer, the bytes inside the org region start and end with a blank line, and the start marker's newline style is preserved. Unlike the member footer, the region has no horizontal-rule separator. Each checking or rendering pass recognizes exactly one block id; a live marker for the other id in a checked file is a hard error.

### Declared org files and placement

The declared org-profile paths are a closed, ordered set. Both English files are independent verification targets and may not be collapsed:

1. `profile/README.md` → `en`
2. `README.md` → `en`
3. `README.ja.md` → `ja`
4. `README.zh.md` → `zh`
5. `README.th.md` → `th`

Every path must additionally pass `re.fullmatch(r'(?:profile/)?README(?:\.[A-Za-z0-9-]+)?\.md', path)`. Leading slashes, `..` segments, backslashes, percent encoding, and whitespace are rejected explicitly. The pattern validates shape; equality with the closed set validates identity. A local `render-org --stray-scan` walks the full checkout except `.git` and rejects any org marker outside these five paths.

The block sits inside the profile's collapsed `<details>` text version. Its intro sentence is inside the generated region. The whole region occupies the ecosystem-list position above the “With any agent…” paragraph; it is not appended to the file and is not placed outside the details element. `render-org` never inserts markers: all five marker pairs must already exist.

### Org enforcement rules R1–R4

The weekly check visits every declared org file in the order above and applies these rules independently:

1. **R1:** markers present and `enforced:false` fails with `org profile block exists but is not enforced`.
2. **R2:** markers present and `enforced:true` requires byte-exact registry output in every declared file; mismatches name the file.
3. **R3:** markers missing from any declared file fails regardless of `enforced`. The required section is the deployment declaration; the check may not silently narrow it.
4. **R4:** `org_profile` is required by lint. Missing `repo`, missing or empty `files`, or any incomplete localized content fails before remote checking.

A declared file returning `404` fails. Network errors, `403`, `429`, and `5xx` produce one degraded-skip note per file. Module and org passes share one degraded-reality ledger; `check --require-reality` rejects degradation in either pass.

The same org pass fetches the four committed visitor-facing artifacts `profile/assets/readme-terminal-{en,ja,zh,th}.svg`. After stripping tags, it asserts for each language that every module appears as an exact `⏺ <id>` line; the next non-empty line is exactly `repo ↗` for published modules and exactly the language-specific preparing badge (`coming soon`, `公開準備中`, `即将发布`, or `เร็ว ๆ นี้`) for preparing modules; and the published-plus-map count appears in the localized ecosystem-intro line. Assertions are per-language and name the failed artifact.

### Three-PR rollout

1. PR 1 in family-os adds this renderer, required `org_profile` with `enforced:false`, and contract v3.6.
2. PR 2 in `caty-ai/.github` adds all five marker pairs and content rendered with the merged PR 1 CLI. The v3.6 runbook uses the `render-all --org-target <dir>` path together with its required checkout root: `python3 -B tools/family_footer.py render-all --checkouts <dir> --org-target <dir>`.
3. PR 3 in family-os flips `enforced:true`, then runs `workflow_dispatch` with `check --require-reality`.

The weekly check is intentionally **RED from PR 1 through PR 3**: R3 fails before the sibling markers land, then R1 fails while the markers exist but enforcement remains false. R3 must not be weakened to shorten this rollout window.

### Rejected alternatives

- A check-only `check_status_text` variant was rejected as the primary mechanism. It can catch enumerated mistakes, but generation makes omission of a new module row structurally impossible; the SVG artifact assertion retains the useful check-only part.
- Collapsing the dual English files was rejected as out of scope. Both remain authoritative and independently checked.
- Full SVG generation from the family-os registry was rejected for this PR. SVG generation remains owned by `.github`; committed artifacts are asserted here.

## Known Limit

An undeclared remote root `README*.md` that already contains generated markers is only caught when `render` runs against a local checkout. The remote checker does not discover undeclared files.

The org-profile names, descriptions, intro templates, and status labels live outside every translation pipeline. Lint proves that each registry language is present and structurally safe, not that its prose is linguistically correct. The SVG check's hardcoded per-language ecosystem-intro fragments are intentionally coupled to wording in `.github/tools/gen_readme_svg.py`; missing-intro wording drift fails closed until the assertion and generator are updated together. The `.github` SVG generator source is otherwise asserted only transitively through the committed artifacts; a regenerate-and-diff gate remains a `.github` follow-up. The hand-written product bullets above the generated region (Caty Phone, ai-meet-participant) are not registry modules and stay outside every org-profile check.
