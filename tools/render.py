#!/usr/bin/env python3
"""Render registry-backed Markdown blocks and detect stale generated content.

Run without arguments to replace generated regions in place. Use --check to
print unified diffs and fail without changing any files.

Python 3.9+, standard library only.
"""

import argparse
import difflib
import json
import pathlib
import re
import sys


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
REGISTRY = REPO_ROOT / "registry" / "modules.json"

LANG_SUFFIX = re.compile(r"\.(?P<lang>[a-z]{2}(?:-[A-Z]{2})?)\.md$")
MARKER_PREFIX = "<!-- family:generated:"
MARKER = re.compile(
    r"^<!-- family:generated:(?P<block>[a-z0-9][a-z0-9-]*):"
    r"(?P<edge>start|end) -->$"
)

EXPECTED_BLOCKS = {
    pathlib.Path("docs/engineering.md"): ("module-inventory",),
    pathlib.Path("docs/engineering.ja.md"): ("module-inventory",),
    pathlib.Path("docs/readme-visual-system.md"): ("repository-links",),
}
KNOWN_BLOCKS = {block for blocks in EXPECTED_BLOCKS.values() for block in blocks}

INVENTORY_HEADERS = {
    "en": ("Module", "Class", "Owns", "State"),
    "ja": ("モジュール", "種別", "所有するもの", "状態"),
}


class RenderError(Exception):
    """A registry or generated-region error that should stop rendering."""


def language_of(path: pathlib.Path) -> str:
    match = LANG_SUFFIX.search(path.name)
    return match.group("lang") if match else "en"


def markdown_files(root: pathlib.Path):
    for path in sorted(root.rglob("*.md")):
        if ".git" not in path.parts:
            yield path


def marker_line(line: str):
    content = line.rstrip("\r\n")
    if MARKER_PREFIX not in content:
        return None
    match = MARKER.fullmatch(content)
    if not match:
        raise RenderError("malformed generated marker: %s" % content)
    return match.group("block"), match.group("edge")


def find_regions(path: pathlib.Path, text: str):
    """Return block regions as inclusive marker-line indexes."""
    regions = {}
    open_marker = None
    lines = text.splitlines(keepends=True)

    for index, line in enumerate(lines):
        try:
            marker = marker_line(line)
        except RenderError as exc:
            raise RenderError("%s:%d: %s" % (path, index + 1, exc))
        if marker is None:
            continue

        block, edge = marker
        if block not in KNOWN_BLOCKS:
            raise RenderError("%s:%d: unknown block-id '%s'" % (path, index + 1, block))

        if edge == "start":
            if block in regions:
                raise RenderError(
                    "%s:%d: duplicated marker for block-id '%s'"
                    % (path, index + 1, block)
                )
            if open_marker is not None:
                raise RenderError(
                    "%s:%d: nested block '%s' inside '%s'"
                    % (path, index + 1, block, open_marker[0])
                )
            open_marker = (block, index)
            continue

        if open_marker is None:
            raise RenderError(
                "%s:%d: end marker for '%s' appears before its start"
                % (path, index + 1, block)
            )
        if open_marker[0] != block:
            raise RenderError(
                "%s:%d: end marker for '%s' appears inside block '%s'"
                % (path, index + 1, block, open_marker[0])
            )
        regions[block] = (open_marker[1], index)
        open_marker = None

    if open_marker is not None:
        raise RenderError(
            "%s:%d: start marker for '%s' has no matching end marker"
            % (path, open_marker[1] + 1, open_marker[0])
        )

    return regions


def state_text(registry: dict, module: dict, lang: str) -> str:
    state = registry["status_labels"][module["status"]][lang]
    note = module.get("note", {}).get(lang)
    if note:
        try:
            separator = registry["note_separator"][lang]
        except KeyError:
            raise RenderError("note_separator is missing language '%s'" % lang)
        state += separator + note
    return state


def render_inventory(registry: dict, lang: str) -> str:
    try:
        headers = INVENTORY_HEADERS[lang]
    except KeyError:
        raise RenderError("module-inventory does not support language '%s'" % lang)

    rows = ["| %s | %s | %s | %s |" % headers, "| --- | --- | --- | --- |"]
    for module in registry["modules"]:
        rows.append(
            "| [%s](https://github.com/%s) | %s | %s | %s |"
            % (
                module["name"],
                module["repo"],
                module["class"][lang],
                module["owns"][lang],
                state_text(registry, module, lang),
            )
        )
    return "\n".join(rows)


def render_repository_links(registry: dict) -> str:
    rows = ["| Module | Link target | State |", "| --- | --- | --- |"]
    for module in registry["modules"]:
        rows.append(
            "| %s | `%s` | %s |"
            % (module["name"], module["repo"], state_text(registry, module, "en"))
        )
    return "\n".join(rows)


def render_block(block: str, registry: dict, path: pathlib.Path) -> str:
    if block == "module-inventory":
        return render_inventory(registry, language_of(path))
    if block == "repository-links":
        return render_repository_links(registry)
    raise RenderError("unknown block-id '%s'" % block)


def line_ending(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    raise RenderError("a start marker must occupy its own line")


def expected_text(path: pathlib.Path, text: str, regions: dict, registry: dict) -> str:
    lines = text.splitlines(keepends=True)
    for block, (start, end) in sorted(
        regions.items(), key=lambda item: item[1][0], reverse=True
    ):
        newline = line_ending(lines[start])
        rendered = render_block(block, registry, path).replace("\n", newline) + newline
        lines[start + 1 : end] = [rendered]
    return "".join(lines)


def collect_files(registry: dict):
    results = []
    found = {block: 0 for block in KNOWN_BLOCKS}
    regions_by_path = {}

    for path in markdown_files(REPO_ROOT):
        try:
            text = path.read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise RenderError("could not read %s: %s" % (path, exc))

        relative = path.relative_to(REPO_ROOT)
        regions = find_regions(relative, text)
        regions_by_path[relative] = regions
        if not regions:
            continue

        allowed = set(EXPECTED_BLOCKS.get(relative, ()))
        for block in regions:
            if block not in allowed:
                raise RenderError(
                    "%s: block-id '%s' has no renderer for this file" % (relative, block)
                )
            found[block] += 1
        results.append((path, text, expected_text(path, text, regions, registry)))

    for relative, blocks in EXPECTED_BLOCKS.items():
        path = REPO_ROOT / relative
        if not path.exists():
            raise RenderError("required Markdown file is missing: %s" % relative)
        present = set(regions_by_path.get(relative, {}))
        for block in blocks:
            if block not in present:
                raise RenderError("%s: required block-id '%s' is missing" % (relative, block))

    for block, count in found.items():
        if count == 0:
            raise RenderError("known block-id '%s' appears in none of the files" % block)

    return results


def load_registry() -> dict:
    try:
        return json.loads(REGISTRY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RenderError("could not read %s: %s" % (REGISTRY, exc))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="print diffs for stale blocks without changing files",
    )
    args = parser.parse_args()

    try:
        results = collect_files(load_registry())
    except (KeyError, TypeError, RenderError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 1

    changed = [
        (path, actual, expected)
        for path, actual, expected in results
        if actual != expected
    ]
    if args.check:
        if not changed:
            print("OK — generated content is up to date.")
            return 0
        print("FAILED — generated content is stale:")
        for path, actual, expected in changed:
            relative = path.relative_to(REPO_ROOT).as_posix()
            sys.stdout.writelines(
                difflib.unified_diff(
                    actual.splitlines(keepends=True),
                    expected.splitlines(keepends=True),
                    fromfile=relative,
                    tofile=relative + " (generated)",
                )
            )
        return 1

    try:
        for path, _actual, expected in changed:
            path.write_bytes(expected.encode("utf-8"))
            print("updated: %s" % path.relative_to(REPO_ROOT))
    except OSError as exc:
        print("ERROR: could not update generated content: %s" % exc, file=sys.stderr)
        return 1
    if not changed:
        print("No generated content changed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
