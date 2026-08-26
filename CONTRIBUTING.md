# Contributing

Thanks for your interest in improving Family OS.

## What belongs here

Family OS is a map, not a runtime. It ships no code and starts nothing. This repository holds the map itself and the documents that explain it.

- **Belongs here:** the map is wrong, out of date, or unclear. A boundary is described inaccurately. A link is broken or points somewhere unexpected. A newcomer took a wrong turn because of how something is worded.
- **Belongs in the module repository:** a bug, a feature request, or an installation problem in Caty Agent Harness, Persona Engine, Sitter, or any other module. Each module owns its own issues, and its README is the canonical source for its behavior.

If you are unsure which side a report falls on, open it here and we will move it.

## Ground rules

- **Issue first.** Open a GitHub issue before starting non-trivial work. State *why* the change is needed, *what "done" looks like* (checkable conditions), and *which files you expect to touch*. One-line fixes such as typos are exempt.
- **Do not invent numbers, results, or case studies.** Every claim about what a module does must be traceable to that module's own documentation or to something you actually ran. If you have not verified it, do not write it as fact.
- **Keep implemented and planned separate.** The map is useful only because a reader can tell what exists today from what is still ahead. Never blur that line to make a section read better.
- **Honest completion.** A change is done when its stated done-conditions pass with evidence, not when it looks done. Pull requests should list which conditions passed and how they were checked.

## Prerequisites

- `git`
- GNU `make` or BSD `make` (minimal Ubuntu images, including default WSL2, do not ship it — `sudo apt-get install make`)
- Python 3.9+ using only the standard library; do not install anything with `pip`
- Network access only if you intentionally run `python3 -B tools/check_registry.py` without `--offline`
- `actionlint` if your change edits files under `.github/workflows/` (optional, but recommended)

## Checking your change

The repository entry point is `make test`. It runs the documented stdlib-only checks for the registry, README footer contract, publication gate, and generated render output. `make lint` is currently a documented no-op, kept as a stable CI entry point while no lint tool is configured.

Before opening a pull request, run `make test`, optionally run `make lint`, and confirm these additional manual checks:

- Every relative link and in-page anchor resolves.
- Images referenced from the README exist and carry no embedded metadata.
- The document still follows [docs/readme-visual-system.md](docs/readme-visual-system.md) — heading marks, section rules, callout budget, and image rules are defined there.
- No personal paths, internal host names, IP addresses, credentials, or private repository names appear anywhere in the diff.

## Pull requests

- Keep one pull request per issue, and keep branches short-lived.
- List the files you changed and confirm they match what the issue predicted; explain any difference.
- English (`README.md`) is canonical. Please keep the Japanese, Chinese, and Thai translations aligned when you change user-facing text, or note in the pull request that translations need a follow-up.

## Style

- Write for someone who has not met this project before. Short sentences, concrete nouns, no jargon that the page has not already introduced.
- Prefer showing the boundary over promising the outcome. What a module refuses to do is as informative as what it does.
