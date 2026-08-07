#!/usr/bin/env python3
"""Render and verify family footer regions across sibling repositories.

Python 3.9+, standard library only.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from family_common import (
    DegradedReality,
    FamilyCommonError,
    MARKER_TOKEN,
    MarkerError,
    iter_marker_lines,
    language_of,
    line_ending,
)


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
REGISTRY = REPO_ROOT / "registry" / "modules.json"
BLOCK_ID = "family-footer"
START_MARKER = "<!-- family:generated:%s:start -->" % BLOCK_ID
END_MARKER = "<!-- family:generated:%s:end -->" % BLOCK_ID
REPO_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class FooterError(Exception):
    """A family-footer contract error."""


@dataclass
class FetchResult:
    status: str
    text: str = ""


def load_registry(path: pathlib.Path = REGISTRY) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FooterError("could not read %s: %s" % (path, exc))


def root_readme_name(name: str) -> bool:
    return name.startswith("README") and name.endswith(".md") and "/" not in name


def footer_enabled(module: dict) -> bool:
    return bool(module.get("footer", False))


def published_modules(registry: dict) -> List[dict]:
    return [module for module in registry["modules"] if module["status"] == "published"]


def validate_repo_name(label: str, value: str) -> None:
    if not isinstance(value, str) or not REPO_NAME.fullmatch(value):
        raise FooterError("%s must be an owner/name repository slug" % label)


def validate_footer_text_value(label: str, value: str) -> None:
    if not isinstance(value, str):
        raise FooterError("%s must be a string" % label)
    if "\n" in value or "\r" in value:
        raise FooterError("%s may not contain a newline" % label)
    if "]" in value:
        raise FooterError("%s may not contain ']'" % label)
    if MARKER_TOKEN in value.lower():
        raise FooterError("%s may not contain generated-marker text" % label)


def validate_table_cell_value(label: str, value: str) -> None:
    validate_footer_text_value(label, value)
    if "|" in value:
        raise FooterError("%s may not contain '|'" % label)


def validate_module_name(module: dict) -> None:
    name = module.get("name")
    if not isinstance(name, str):
        raise FooterError("name must be a string")
    if "\n" in name or "\r" in name:
        raise FooterError("name may not contain a newline")
    if "|" in name:
        raise FooterError("name may not contain '|'")
    if "]" in name:
        raise FooterError("name may not contain ']'")
    if MARKER_TOKEN in name.lower():
        raise FooterError("name may not contain generated-marker text")


def module_label(module: dict) -> str:
    return "registry/modules.json: module '%s'" % module.get("id", module.get("repo", "<unknown>"))


def resolve_declared_readmes(module: dict, languages: Sequence[str]) -> List[Tuple[str, str]]:
    overrides = module.get("readme_overrides", {}) or {}
    if not isinstance(overrides, dict):
        raise FooterError("%s: readme_overrides must be an object" % module_label(module))

    for filename, lang in overrides.items():
        if not isinstance(filename, str):
            raise FooterError("%s: readme_overrides keys must be strings" % module_label(module))
        if not root_readme_name(filename):
            raise FooterError(
                "%s: readme_overrides filename '%s' must be a repo-root README*.md"
                % (module_label(module), filename)
            )
        language_of(pathlib.Path(filename), languages, overrides)
        if lang not in languages:
            raise FooterError(
                "%s: readme_overrides for '%s' declares unknown language '%s'"
                % (module_label(module), filename, lang)
            )

    readme_files = module.get("readme_files")
    if readme_files is not None:
        if not isinstance(readme_files, list):
            raise FooterError("%s: readme_files must be a list" % module_label(module))
        if not readme_files:
            raise FooterError("%s: readme_files may not be empty" % module_label(module))
        results = []
        seen = set()
        for filename in readme_files:
            if not isinstance(filename, str):
                raise FooterError("%s: readme_files entries must be strings" % module_label(module))
            if not root_readme_name(filename):
                raise FooterError(
                    "%s: readme_files entry '%s' must be a repo-root README*.md"
                    % (module_label(module), filename)
                )
            if filename in seen:
                raise FooterError(
                    "%s: readme_files repeats '%s'" % (module_label(module), filename)
                )
            seen.add(filename)
            results.append((filename, language_of(pathlib.Path(filename), languages, overrides)))
        return results

    declared = [("README.md", "en")]
    for lang in languages:
        if lang == "en":
            continue
        declared.append(("README.%s.md" % lang, lang))

    by_language = {lang: filename for filename, lang in declared}
    seen_languages = set()
    for filename, lang in overrides.items():
        if lang in seen_languages:
            raise FooterError(
                "%s: readme_overrides declares language '%s' more than once"
                % (module_label(module), lang)
            )
        seen_languages.add(lang)
        by_language[lang] = filename

    ordered = []
    for lang in ["en"] + [lang for lang in languages if lang != "en"]:
        if lang not in by_language:
            raise FooterError(
                "%s: no README file resolves to language '%s'" % (module_label(module), lang)
            )
        ordered.append((by_language[lang], lang))
    return ordered


def lint_registry(registry: dict) -> List[str]:
    failures: List[str] = []
    languages = registry.get("languages")
    if not isinstance(languages, list) or not languages:
        return ["registry/modules.json: languages must be a non-empty list"]
    if any(not isinstance(lang, str) for lang in languages):
        failures.append("registry/modules.json: languages entries must all be strings")
    if "en" not in languages:
        failures.append("registry/modules.json: languages must include 'en'")

    map_repo = registry.get("map_repo")
    try:
        validate_repo_name("registry/modules.json: map_repo", map_repo)
    except FooterError as exc:
        failures.append(str(exc))

    footer_text = registry.get("footer_text")
    if not isinstance(footer_text, dict):
        failures.append("registry/modules.json: footer_text must be an object")
    else:
        for key in (
            "intro",
            "table_axis",
            "table_module",
            "table_what",
            "table_state",
            "map_name",
            "axis_map",
            "axis_rules",
            "axis_vertical",
            "axis_horizontal",
            "axis_foundation_suffix",
            "map_tagline",
        ):
            section = footer_text.get(key)
            if not isinstance(section, dict):
                failures.append("registry/modules.json: footer_text.%s must be an object" % key)
                continue
            for lang in languages:
                value = section.get(lang)
                label = "registry/modules.json: footer_text.%s.%s" % (key, lang)
                try:
                    if key == "intro":
                        validate_footer_text_value(label, value)
                    else:
                        validate_table_cell_value(label, value)
                except FooterError as exc:
                    failures.append(str(exc))
                    continue
                if key == "intro" and value.count("{map}") != 1:
                    failures.append("%s must contain exactly one {map} placeholder" % label)

    status_labels = registry.get("status_labels")
    if not isinstance(status_labels, dict):
        failures.append("registry/modules.json: status_labels must be an object")
        status_labels = {}
    else:
        for status, section in status_labels.items():
            if not isinstance(section, dict):
                failures.append(
                    "registry/modules.json: status_labels.%s must be an object" % status
                )
                continue
            for lang in languages:
                label = "registry/modules.json: status_labels.%s.%s" % (status, lang)
                try:
                    validate_table_cell_value(label, section.get(lang))
                except FooterError as exc:
                    failures.append(str(exc))

    modules = registry.get("modules")
    if not isinstance(modules, list):
        failures.append("registry/modules.json: modules must be a list")
        return failures

    for module in modules:
        label = module_label(module)
        try:
            validate_repo_name("%s repo" % label, module.get("repo"))
        except FooterError as exc:
            failures.append(str(exc))
        try:
            validate_module_name(module)
        except FooterError as exc:
            failures.append("%s: %s" % (label, exc))
        tagline = module.get("tagline")
        if not isinstance(tagline, dict):
            failures.append("%s: tagline must be an object" % label)
        else:
            for lang in languages:
                tagline_label = "%s: tagline.%s" % (label, lang)
                try:
                    validate_table_cell_value(tagline_label, tagline.get(lang))
                except FooterError as exc:
                    failures.append(str(exc))
        status = module.get("status")
        if status not in status_labels:
            failures.append("%s: status must name an entry in status_labels" % label)
        axis = module.get("axis")
        if not isinstance(axis, dict):
            failures.append("%s: axis must be an object" % label)
        else:
            if axis.get("group") not in {"rules", "vertical", "horizontal"}:
                failures.append(
                    "%s: axis.group must be one of rules, vertical, horizontal" % label
                )
            if not isinstance(axis.get("foundation"), bool):
                failures.append("%s: axis.foundation must be a boolean" % label)
        if "footer" in module and not isinstance(module["footer"], bool):
            failures.append("%s: footer must be a boolean when present" % label)
        if footer_enabled(module) and module.get("status") != "published":
            failures.append("%s: footer:true requires status 'published'" % label)
        try:
            resolve_declared_readmes(module, languages)
        except (FooterError, FamilyCommonError) as exc:
            failures.append(str(exc))

    return failures


def map_link(registry: dict, lang: str) -> str:
    return "[%s](https://github.com/%s)" % (
        registry["footer_text"]["map_name"][lang],
        registry["map_repo"],
    )


def module_axis(registry: dict, module: dict, lang: str) -> str:
    axis = module["axis"]
    value = registry["footer_text"]["axis_%s" % axis["group"]][lang]
    if axis["foundation"]:
        value += registry["footer_text"]["axis_foundation_suffix"][lang]
    validate_table_cell_value("%s axis.%s" % (module_label(module), lang), value)
    return value


def module_table(
    registry: dict,
    host_module: Optional[dict],
    lang: str,
    newline: str,
    *,
    bold_map: bool = False,
) -> str:
    footer_text = registry["footer_text"]
    headers = [
        ("table_axis", footer_text["table_axis"][lang]),
        ("table_module", footer_text["table_module"][lang]),
        ("table_what", footer_text["table_what"][lang]),
        ("table_state", footer_text["table_state"][lang]),
    ]
    for key, value in headers:
        validate_table_cell_value("footer_text.%s.%s" % (key, lang), value)

    rows = [
        "| %s | %s | %s | %s |" % tuple(value for _key, value in headers),
        "| --- | --- | --- | --- |",
    ]
    map_axis = footer_text["axis_map"][lang]
    map_name = footer_text["map_name"][lang]
    map_tagline = footer_text["map_tagline"][lang]
    map_status = registry["status_labels"]["published"][lang]
    validate_table_cell_value("footer_text.axis_map.%s" % lang, map_axis)
    validate_table_cell_value("footer_text.map_name.%s" % lang, map_name)
    validate_table_cell_value("footer_text.map_tagline.%s" % lang, map_tagline)
    validate_table_cell_value("status_labels.published.%s" % lang, map_status)
    rendered_map = "**%s**" % map_name if bold_map else map_link(registry, lang)
    rows.append("| %s | %s | %s | %s |" % (map_axis, rendered_map, map_tagline, map_status))
    for module in registry["modules"]:
        axis = module_axis(registry, module, lang)
        name = module["name"]
        tagline = module["tagline"][lang]
        status = registry["status_labels"][module["status"]][lang]
        validate_table_cell_value("%s name" % module_label(module), name)
        validate_table_cell_value("%s tagline.%s" % (module_label(module), lang), tagline)
        validate_table_cell_value(
            "status_labels.%s.%s" % (module["status"], lang), status
        )

        is_host = host_module is not None and module["repo"] == host_module["repo"]
        if is_host or module["status"] != "published":
            rendered_name = "**%s**" % name
        else:
            rendered_name = "[%s](https://github.com/%s)" % (name, module["repo"])
        rows.append("| %s | %s | %s | %s |" % (axis, rendered_name, tagline, status))
    return newline.join(rows)


def render_region(
    registry: dict, module: Optional[dict], lang: str, newline: str
) -> str:
    intro = registry["footer_text"]["intro"][lang].replace(
        "{map}", map_link(registry, lang)
    )
    table = module_table(registry, module, lang, newline)
    return (
        newline
        + "---"
        + newline * 2
        + intro
        + newline * 2
        + table
        + newline * 2
    )


def find_footer_regions(label: str, text: str) -> Dict[str, Tuple[int, int]]:
    regions: Dict[str, Tuple[int, int]] = {}
    open_marker: Optional[Tuple[str, int]] = None
    try:
        for index, block, edge in iter_marker_lines(text, {BLOCK_ID}):
            if block != BLOCK_ID:
                raise FooterError("%s:%d: unknown block-id '%s'" % (label, index + 1, block))
            if edge == "start":
                if block in regions:
                    raise FooterError(
                        "%s:%d: duplicated marker for block-id '%s'"
                        % (label, index + 1, block)
                    )
                if open_marker is not None:
                    raise FooterError(
                        "%s:%d: nested block '%s' inside '%s'"
                        % (label, index + 1, block, open_marker[0])
                    )
                open_marker = (block, index)
                continue
            if open_marker is None:
                raise FooterError(
                    "%s:%d: end marker for '%s' appears before its start"
                    % (label, index + 1, block)
                )
            if open_marker[0] != block:
                raise FooterError(
                    "%s:%d: end marker for '%s' appears inside block '%s'"
                    % (label, index + 1, block, open_marker[0])
                )
            regions[block] = (open_marker[1], index)
            open_marker = None
    except MarkerError as exc:
        raise FooterError("%s:%d: %s" % (label, exc.line_number, exc))

    if open_marker is not None:
        raise FooterError(
            "%s:%d: start marker for '%s' has no matching end marker"
            % (label, open_marker[1] + 1, open_marker[0])
        )
    return regions


def extract_region(text: str, region: Tuple[int, int]) -> str:
    lines = text.splitlines(keepends=True)
    start, end = region
    return "".join(lines[start + 1 : end])


def replace_region(text: str, region: Tuple[int, int], replacement: str) -> str:
    lines = text.splitlines(keepends=True)
    start, end = region
    lines[start + 1 : end] = [replacement]
    return "".join(lines)


def preferred_newline(text: str) -> str:
    if "\r\n" in text:
        return "\r\n"
    return "\n"


def insert_footer_region(text: str, region_text: str, newline: str) -> str:
    updated = text
    if updated and not updated.endswith(("\n", "\r\n")):
        updated += newline
    if updated and not updated.endswith(newline * 2):
        updated += newline
    updated += START_MARKER + newline + region_text + END_MARKER + newline
    return updated


def fetch_readme(repo: str, filename: str, timeout: float = 20.0) -> FetchResult:
    url = "https://raw.githubusercontent.com/%s/HEAD/%s" % (repo, filename)
    request = urllib.request.Request(
        url,
        method="GET",
        headers={"User-Agent": "family-os-registry-check"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200:
                return FetchResult("skip")
            return FetchResult("ok", response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return FetchResult("missing")
        if exc.code in (403, 429) or 500 <= exc.code <= 599:
            return FetchResult("skip")
        raise
    except (urllib.error.URLError, TimeoutError):
        return FetchResult("skip")


def check_registry_footers(
    registry: dict,
    require_reality: bool = False,
    fetcher: Callable[[str, str], FetchResult] = fetch_readme,
) -> Tuple[List[str], List[str]]:
    failures = lint_registry(registry)
    if failures:
        return failures, []

    notes: List[str] = []
    degraded = DegradedReality()
    languages = registry["languages"]

    for module in published_modules(registry):
        declared = resolve_declared_readmes(module, languages)
        saw_markers = False
        module_complete = True
        for filename, lang in declared:
            label = "%s:%s" % (module["repo"], filename)
            fetched = fetcher(module["repo"], filename)
            if fetched.status == "missing":
                failures.append("%s: declared README returned 404" % label)
                module_complete = False
                continue
            if fetched.status != "ok":
                degraded.skip(
                    module["repo"], "%s: could not reach GitHub, footer check skipped" % label
                )
                module_complete = False
                continue

            try:
                regions = find_footer_regions(label, fetched.text)
            except FooterError as exc:
                failures.append(str(exc))
                module_complete = False
                continue

            region = regions.get(BLOCK_ID)
            if region is None:
                if footer_enabled(module):
                    failures.append("%s: footer:true but markers are missing" % label)
                continue

            saw_markers = True
            if not footer_enabled(module):
                failures.append("%s: footer exists but is not enforced" % label)
                continue

            lines = fetched.text.splitlines(keepends=True)
            try:
                newline = line_ending(lines[region[0]])
            except (FamilyCommonError, IndexError) as exc:
                failures.append("%s: %s" % (label, exc))
                module_complete = False
                continue
            expected = render_region(registry, module, lang, newline)
            actual = extract_region(fetched.text, region)
            if actual != expected:
                failures.append("%s: footer content does not match the registry" % label)

        if module_complete and not saw_markers and not footer_enabled(module):
            failures.append("%s: published module has no footer" % module["repo"])

    notes.extend(degraded.notes())
    degraded.finalize(failures, require_reality)
    return failures, notes


def render_repo_to_target(
    registry: dict, target: pathlib.Path, repo: str
) -> Tuple[bool, List[str]]:
    failures = lint_registry(registry)
    if failures:
        raise FooterError("\n".join(failures))

    module = next((entry for entry in registry["modules"] if entry["repo"] == repo), None)
    if module is None:
        raise FooterError("registry/modules.json: --repo '%s' is not declared" % repo)
    if module["status"] != "published":
        raise FooterError("%s is not published and may not carry the family footer" % repo)

    declared = resolve_declared_readmes(module, registry["languages"])
    declared_names = {filename for filename, _lang in declared}
    for path in sorted(target.iterdir()):
        if not path.is_file() or not root_readme_name(path.name) or path.name in declared_names:
            continue
        text = path.read_bytes().decode("utf-8")
        if MARKER_TOKEN in text.lower():
            raise FooterError(
                "%s: marker-carrying %s is not in the declared README set"
                % (repo, path.name)
            )

    changed_files: List[str] = []
    for filename, lang in declared:
        path = target / filename
        if not path.exists():
            raise FooterError("%s: declared README is missing at %s" % (repo, filename))
        text = path.read_bytes().decode("utf-8")
        label = "%s:%s" % (repo, filename)
        regions = find_footer_regions(label, text)
        if BLOCK_ID in regions:
            lines = text.splitlines(keepends=True)
            try:
                newline = line_ending(lines[regions[BLOCK_ID][0]])
            except FamilyCommonError as exc:
                raise FooterError("%s: %s" % (label, exc))
            expected_region = render_region(registry, module, lang, newline)
            updated = replace_region(text, regions[BLOCK_ID], expected_region)
        else:
            newline = preferred_newline(text)
            expected_region = render_region(registry, module, lang, newline)
            updated = insert_footer_region(text, expected_region, newline)
        if updated != text:
            path.write_bytes(updated.encode("utf-8"))
            changed_files.append(filename)
    return bool(changed_files), changed_files


def command_lint(_args) -> int:
    try:
        failures = lint_registry(load_registry())
    except (FooterError, OSError, UnicodeDecodeError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 1
    if failures:
        for failure in failures:
            print("ERROR: %s" % failure, file=sys.stderr)
        return 1
    print("OK — family footer registry is self-consistent.")
    return 0


def command_check(args) -> int:
    try:
        failures, notes = check_registry_footers(load_registry(), args.require_reality)
    except (FooterError, OSError, UnicodeDecodeError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 1
    for note in notes:
        print("note: %s" % note)
    if failures:
        for failure in failures:
            print("ERROR: %s" % failure, file=sys.stderr)
        return 1
    print("OK — family footer content matches the registry.")
    return 0


def command_render(args) -> int:
    try:
        target = args.target.expanduser().resolve()
        if not target.is_dir():
            raise FooterError("--target must be an existing directory")
        changed, changed_files = render_repo_to_target(
            load_registry(), target, args.repo
        )
    except (FooterError, OSError, UnicodeDecodeError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 1
    if changed:
        for filename in changed_files:
            print("updated: %s" % filename)
    else:
        print("No footer content changed.")
    return 0


def command_render_all(args) -> int:
    try:
        registry = load_registry()
        failures = lint_registry(registry)
        if failures:
            for failure in failures:
                print("ERROR: %s" % failure, file=sys.stderr)
            return 1

        checkouts = args.checkouts.expanduser().resolve()
        missing = []
        for module in published_modules(registry):
            target = checkouts / module["repo"].rsplit("/", 1)[1]
            if not target.is_dir():
                missing.append("%s -> %s" % (module["repo"], target.name))
        if missing:
            print("ERROR: missing checkout(s):", file=sys.stderr)
            for item in missing:
                print("ERROR: %s" % item, file=sys.stderr)
            return 1

        for module in published_modules(registry):
            target = checkouts / module["repo"].rsplit("/", 1)[1]
            changed, _changed_files = render_repo_to_target(registry, target, module["repo"])
            print("%s: %s" % (module["repo"], "changed" if changed else "unchanged"))
        return 0
    except (FooterError, OSError, UnicodeDecodeError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    lint = subparsers.add_parser("lint", help="validate footer registry shape with no network")
    lint.set_defaults(func=command_lint)

    check = subparsers.add_parser("check", help="verify published footers against GitHub")
    check.add_argument(
        "--require-reality",
        action="store_true",
        help="fail if any published module could not be verified remotely",
    )
    check.set_defaults(func=command_check)

    render = subparsers.add_parser("render", help="render one repo checkout in place")
    render.add_argument("--target", type=pathlib.Path, required=True)
    render.add_argument("--repo", required=True)
    render.set_defaults(func=command_render)

    render_all = subparsers.add_parser(
        "render-all", help="render every published repo checkout under one directory"
    )
    render_all.add_argument("--checkouts", type=pathlib.Path, required=True)
    render_all.set_defaults(func=command_render_all)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
