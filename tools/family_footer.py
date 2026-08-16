#!/usr/bin/env python3
"""Render and verify family footer regions across sibling repositories.

Python 3.9+, standard library only.
"""

from __future__ import annotations

import argparse
import html
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
ORG_BLOCK_ID = "org-profile-modules"
START_MARKER = "<!-- family:generated:%s:start -->" % BLOCK_ID
END_MARKER = "<!-- family:generated:%s:end -->" % BLOCK_ID
ORG_START_MARKER = "<!-- family:generated:%s:start -->" % ORG_BLOCK_ID
ORG_END_MARKER = "<!-- family:generated:%s:end -->" % ORG_BLOCK_ID
REPO_NAME = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
ORG_README_PATTERN = re.compile(r"(?:profile/)?README(?:\.[A-Za-z0-9-]+)?\.md")
ORG_DECLARED_FILES = (
    ("profile/README.md", "en"),
    ("README.md", "en"),
    ("README.ja.md", "ja"),
    ("README.zh.md", "zh"),
    ("README.th.md", "th"),
)
ORG_SVG_FILES = tuple(
    ("profile/assets/readme-terminal-%s.svg" % lang, lang)
    for lang in ("en", "ja", "zh", "th")
)
# Keep these badges coupled to the wording emitted by .github/tools/gen_readme_svg.py.
ORG_SVG_PREPARING_BADGES = {
    "en": "coming soon",
    "ja": "公開準備中",
    "zh": "即将发布",
    "th": "เร็ว ๆ นี้",
}


class FooterError(Exception):
    """A family-footer contract error."""


@dataclass
class FetchResult:
    status: str
    text: str = ""


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Expose redirects so moved footer targets cannot look current."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def load_registry(path: pathlib.Path = REGISTRY) -> dict:
    def reject_duplicate_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise FooterError("duplicate JSON key '%s'" % key)
            result[key] = value
        return result

    try:
        return json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys
        )
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


def validate_org_path(path: str) -> None:
    if not isinstance(path, str):
        raise FooterError("registry/modules.json: org_profile.files keys must be strings")
    if (
        path.startswith("/")
        or "\\" in path
        or "%" in path
        or any(part == ".." for part in path.split("/"))
        or any(character.isspace() for character in path)
        or re.fullmatch(ORG_README_PATTERN, path) is None
    ):
        raise FooterError(
            "registry/modules.json: org_profile file '%s' is not an allowed README path" % path
        )


def resolve_org_files(registry: dict) -> List[Tuple[str, str]]:
    profile = registry.get("org_profile")
    if not isinstance(profile, dict):
        raise FooterError("registry/modules.json: org_profile must be an object")
    files = profile.get("files")
    if not isinstance(files, dict) or not files:
        raise FooterError("registry/modules.json: org_profile.files must be a non-empty object")
    resolved = []
    for path, lang in files.items():
        validate_org_path(path)
        if lang not in registry.get("languages", []):
            raise FooterError(
                "registry/modules.json: org_profile.files.%s has unknown language '%s'"
                % (path, lang)
            )
        resolved.append((path, lang))
    if tuple(resolved) != ORG_DECLARED_FILES:
        raise FooterError(
            "registry/modules.json: org_profile.files must be exactly the closed declared set"
        )
    return resolved


def validate_org_text_value(label: str, value: str, leading_guard: bool = False) -> None:
    if not isinstance(value, str):
        raise FooterError("%s must be a string" % label)
    if "\n" in value or "\r" in value:
        raise FooterError("%s may not contain a newline" % label)
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        raise FooterError("%s may not contain control characters" % label)
    if MARKER_TOKEN in value.lower():
        raise FooterError("%s may not contain generated-marker text" % label)
    for character in ("[", "]", "|", "<", "`"):
        if character in value:
            raise FooterError("%s may not contain '%s'" % (label, character))
    if leading_guard and value.startswith(("-", "*", "#", ">")):
        raise FooterError("%s may not begin with Markdown bullet or heading syntax" % label)


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

    org_profile = registry.get("org_profile")
    if not isinstance(org_profile, dict):
        failures.append("registry/modules.json: org_profile must be an object")
        return failures
    try:
        validate_repo_name("registry/modules.json: org_profile.repo", org_profile.get("repo"))
    except FooterError as exc:
        failures.append(str(exc))
    if not isinstance(org_profile.get("enforced"), bool):
        failures.append("registry/modules.json: org_profile.enforced must be a boolean")
    try:
        resolve_org_files(registry)
    except FooterError as exc:
        failures.append(str(exc))

    module_repos = {module.get("repo") for module in modules}
    if map_repo in module_repos:
        failures.append("registry/modules.json: map_repo must not appear in modules[].repo")

    intro = org_profile.get("intro")
    if not isinstance(intro, dict):
        failures.append("registry/modules.json: org_profile.intro must be an object")
    else:
        for lang in languages:
            label = "registry/modules.json: org_profile.intro.%s" % lang
            try:
                validate_org_text_value(label, intro.get(lang))
            except FooterError as exc:
                failures.append(str(exc))
                continue
            if intro[lang].count("{count}") != 1:
                failures.append("%s must contain exactly one {count} placeholder" % label)

    org_status = org_profile.get("status_labels")
    if not isinstance(org_status, dict):
        failures.append("registry/modules.json: org_profile.status_labels must be an object")
        org_status = {}
    for status in ("published", "preparing"):
        section = org_status.get(status)
        if not isinstance(section, dict):
            failures.append(
                "registry/modules.json: org_profile.status_labels.%s must be an object" % status
            )
            continue
        for lang in languages:
            label = "registry/modules.json: org_profile.status_labels.%s.%s" % (
                status,
                lang,
            )
            try:
                validate_org_text_value(label, section.get(lang))
            except FooterError as exc:
                failures.append(str(exc))

    org_map = org_profile.get("map")
    if not isinstance(org_map, dict):
        failures.append("registry/modules.json: org_profile.map must be an object")
    else:
        try:
            validate_org_text_value(
                "registry/modules.json: org_profile.map.name",
                org_map.get("name"),
                leading_guard=True,
            )
        except FooterError as exc:
            failures.append(str(exc))
        desc = org_map.get("desc")
        if not isinstance(desc, dict):
            failures.append("registry/modules.json: org_profile.map.desc must be an object")
        else:
            for lang in languages:
                try:
                    validate_org_text_value(
                        "registry/modules.json: org_profile.map.desc.%s" % lang,
                        desc.get(lang),
                        leading_guard=True,
                    )
                except FooterError as exc:
                    failures.append(str(exc))

    org_modules = org_profile.get("modules")
    if not isinstance(org_modules, dict):
        failures.append("registry/modules.json: org_profile.modules must be an object")
        org_modules = {}
    module_ids = {module.get("id") for module in modules}
    org_ids = set(org_modules)
    if org_ids != module_ids:
        missing = sorted(module_ids - org_ids)
        extra = sorted(org_ids - module_ids)
        failures.append(
            "registry/modules.json: org_profile.modules keys must exactly match modules[].id"
            " (missing: %s; extra: %s)"
            % (", ".join(missing) or "none", ", ".join(extra) or "none")
        )
    for module_id, text in org_modules.items():
        label = "registry/modules.json: org_profile.modules.%s" % module_id
        if not isinstance(text, dict):
            failures.append("%s must be an object" % label)
            continue
        try:
            validate_org_text_value(
                "%s.name" % label, text.get("name"), leading_guard=True
            )
        except FooterError as exc:
            failures.append(str(exc))
        desc = text.get("desc")
        if not isinstance(desc, dict):
            failures.append("%s.desc must be an object" % label)
            continue
        for lang in languages:
            try:
                validate_org_text_value(
                    "%s.desc.%s" % (label, lang),
                    desc.get(lang),
                    leading_guard=True,
                )
            except FooterError as exc:
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


def render_org_block(registry: dict, lang: str) -> str:
    profile = registry["org_profile"]
    count = len(published_modules(registry)) + 1
    rows = [profile["intro"][lang].replace("{count}", str(count)), ""]
    rows.append(
        "- **[%s](https://github.com/%s)** — %s%s"
        % (
            profile["map"]["name"],
            registry["map_repo"],
            profile["map"]["desc"][lang],
            profile["status_labels"]["published"][lang],
        )
    )
    for module in registry["modules"]:
        try:
            org_module = profile["modules"][module["id"]]
        except KeyError:
            raise FooterError(
                "registry/modules.json: registry module '%s' is missing from "
                "org_profile.modules" % module["id"]
            )
        if module["status"] == "published":
            rendered_name = "[%s](https://github.com/%s)" % (
                org_module["name"],
                module["repo"],
            )
        else:
            rendered_name = org_module["name"]
        rows.append(
            "- **%s** — %s%s"
            % (
                rendered_name,
                org_module["desc"][lang],
                profile["status_labels"][module["status"]][lang],
            )
        )
    return "\n" + "\n".join(rows) + "\n\n"


def find_footer_regions(
    label: str, text: str, block_id: str = BLOCK_ID
) -> Dict[str, Tuple[int, int]]:
    regions: Dict[str, Tuple[int, int]] = {}
    open_marker: Optional[Tuple[str, int]] = None
    try:
        for index, block, edge in iter_marker_lines(text, {block_id}):
            if block != block_id:
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
    opener = urllib.request.build_opener(NoRedirectHandler())
    try:
        with opener.open(request, timeout=timeout) as response:
            if response.status != 200:
                return FetchResult("skip")
            return FetchResult("ok", response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if 300 <= exc.code <= 399:
            return FetchResult("moved", exc.headers.get("Location", ""))
        if exc.code == 404:
            return FetchResult("missing")
        if exc.code in (410, 451):
            return FetchResult("hard", "HTTP status %d" % exc.code)
        if exc.code in (403, 429) or 500 <= exc.code <= 599:
            return FetchResult("skip")
        return FetchResult("skip", "unexpected HTTP status %d" % exc.code)
    except (urllib.error.URLError, TimeoutError):
        return FetchResult("skip")


def record_fetch_problem(
    fetched: FetchResult,
    label: str,
    unit: str,
    skip_message: str,
    failures: List[str],
    degraded: DegradedReality,
) -> None:
    if fetched.status == "moved":
        destination = fetched.text or "(missing Location header)"
        failures.append("moved: %s -> %s" % (label, destination))
        return
    if fetched.status == "hard":
        failures.append("%s: %s" % (label, fetched.text))
        return
    detail = " (%s)" % fetched.text if fetched.text else ""
    degraded.skip(unit, skip_message + detail)


def assert_org_svg(registry: dict, lang: str, text: str, label: str) -> List[str]:
    failures = []
    visible = html.unescape(re.sub(r"<[^>]+>", "", text))
    lines = [line.strip() for line in visible.splitlines()]
    for module in registry["modules"]:
        needle = "⏺ " + module["id"]
        index = next((i for i, line in enumerate(lines) if line == needle), None)
        if index is None:
            failures.append("%s: %s SVG is missing module '%s'" % (label, lang, module["id"]))
            continue
        badge = next((line for line in lines[index + 1 :] if line), None)
        if badge is None or "⏺ " in badge:
            failures.append("%s: %s SVG has no badge after module '%s'" % (label, lang, module["id"]))
            continue
        expected_badge = (
            "repo ↗"
            if module["status"] == "published"
            else ORG_SVG_PREPARING_BADGES[lang]
        )
        if badge != expected_badge:
            failures.append(
                "%s: %s SVG module '%s' must have badge '%s'"
                % (label, lang, module["id"], expected_badge)
            )
    intro_needles = {
        "en": "open today",
        "ja": "このうち",
        "zh": "其中",
        "th": "ตัวในนี้",
    }
    intro_line = next((line for line in lines if intro_needles[lang] in line), None)
    count = str(len(published_modules(registry)) + 1)
    if intro_line is None:
        failures.append("%s: %s SVG is missing the ecosystem intro line" % (label, lang))
    elif re.search(r"(?<![0-9])%s(?![0-9])" % re.escape(count), intro_line) is None:
        failures.append(
            "%s: %s SVG ecosystem intro does not contain count %s" % (label, lang, count)
        )
    return failures


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
                record_fetch_problem(
                    fetched,
                    label,
                    module["repo"],
                    "%s: could not reach GitHub, footer check skipped" % label,
                    failures,
                    degraded,
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

    org_profile = registry["org_profile"]
    org_repo = org_profile["repo"]
    for filename, lang in resolve_org_files(registry):
        label = "%s:%s" % (org_repo, filename)
        fetched = fetcher(org_repo, filename)
        if fetched.status == "missing":
            failures.append("%s: declared org profile file returned 404" % label)
            continue
        if fetched.status != "ok":
            record_fetch_problem(
                fetched,
                label,
                label,
                "%s: could not reach GitHub, org profile check skipped" % label,
                failures,
                degraded,
            )
            continue
        try:
            regions = find_footer_regions(label, fetched.text, ORG_BLOCK_ID)
        except FooterError as exc:
            failures.append(str(exc))
            continue
        region = regions.get(ORG_BLOCK_ID)
        if region is None:
            failures.append("%s: org profile markers are missing" % label)
            continue
        if not org_profile["enforced"]:
            failures.append("%s: org profile block exists but is not enforced" % label)
            continue
        lines = fetched.text.splitlines(keepends=True)
        try:
            newline = line_ending(lines[region[0]])
        except (FamilyCommonError, IndexError) as exc:
            failures.append("%s: %s" % (label, exc))
            continue
        expected = render_org_block(registry, lang).replace("\n", newline)
        if extract_region(fetched.text, region) != expected:
            failures.append("%s: org profile content does not match the registry" % label)

    for filename, lang in ORG_SVG_FILES:
        label = "%s:%s" % (org_repo, filename)
        fetched = fetcher(org_repo, filename)
        if fetched.status == "missing":
            failures.append("%s: committed SVG artifact returned 404" % label)
            continue
        if fetched.status != "ok":
            record_fetch_problem(
                fetched,
                label,
                label,
                "%s: could not reach GitHub, SVG check skipped" % label,
                failures,
                degraded,
            )
            continue
        failures.extend(assert_org_svg(registry, lang, fetched.text, label))

    notes.extend(degraded.notes())
    degraded.finalize(failures, require_reality, noun="targets")
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


def render_org_to_target(
    registry: dict, target: pathlib.Path, stray_scan: bool = False
) -> List[Tuple[str, bool]]:
    failures = lint_registry(registry)
    if failures:
        raise FooterError("\n".join(failures))
    profile = registry["org_profile"]
    declared = resolve_org_files(registry)
    declared_names = {filename for filename, _lang in declared}

    if stray_scan:
        marker = ("family:generated:%s" % ORG_BLOCK_ID).encode("ascii")
        for path in sorted(target.rglob("*")):
            relative = path.relative_to(target)
            if ".git" in relative.parts or not path.is_file():
                continue
            if relative.as_posix() in declared_names:
                continue
            if marker in path.read_bytes().lower():
                raise FooterError(
                    "%s: org-profile-modules marker is outside the declared file set"
                    % relative.as_posix()
                )

    documents = []
    missing = []
    for filename, lang in declared:
        path = target / filename
        if not path.is_file():
            missing.append(filename)
            continue
        text = path.read_bytes().decode("utf-8")
        label = "%s:%s" % (profile["repo"], filename)
        regions = find_footer_regions(label, text, ORG_BLOCK_ID)
        region = regions.get(ORG_BLOCK_ID)
        if region is None:
            missing.append(filename)
            continue
        documents.append((filename, lang, path, text, region))
    if missing:
        raise FooterError("org profile markers are missing from: %s" % ", ".join(missing))

    results = []
    for filename, lang, path, text, region in documents:
        lines = text.splitlines(keepends=True)
        try:
            newline = line_ending(lines[region[0]])
        except (FamilyCommonError, IndexError) as exc:
            raise FooterError("%s:%s: %s" % (profile["repo"], filename, exc))
        expected = render_org_block(registry, lang).replace("\n", newline)
        updated = replace_region(text, region, expected)
        changed = updated != text
        if changed:
            path.write_bytes(updated.encode("utf-8"))
        results.append((filename, changed))
    return results


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


def command_render_org(args) -> int:
    try:
        target = args.target.expanduser().resolve()
        if not target.is_dir():
            raise FooterError("--target must be an existing directory")
        results = render_org_to_target(load_registry(), target, args.stray_scan)
    except (FooterError, OSError, UnicodeDecodeError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 1
    changed = False
    for filename, file_changed in results:
        print("%s: %s" % (filename, "changed" if file_changed else "unchanged"))
        changed = changed or file_changed
    if not changed:
        print("No org profile content changed.")
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
        if args.org_target is None:
            print("NOTE: the org profile was not rendered; pass --org-target to render it.")
        else:
            org_target = args.org_target.expanduser().resolve()
            if not org_target.is_dir():
                raise FooterError("--org-target must be an existing directory")
            results = render_org_to_target(registry, org_target)
            for filename, changed in results:
                print("%s:%s: %s" % (registry["org_profile"]["repo"], filename, "changed" if changed else "unchanged"))
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

    render_org = subparsers.add_parser(
        "render-org", help="render the declared org profile checkout in place"
    )
    render_org.add_argument("--target", type=pathlib.Path, required=True)
    render_org.add_argument(
        "--stray-scan",
        action="store_true",
        help="reject org-profile-modules markers outside the declared files",
    )
    render_org.set_defaults(func=command_render_org)

    render_all = subparsers.add_parser(
        "render-all", help="render every published repo checkout under one directory"
    )
    render_all.add_argument("--checkouts", type=pathlib.Path, required=True)
    render_all.add_argument("--org-target", type=pathlib.Path)
    render_all.set_defaults(func=command_render_all)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
