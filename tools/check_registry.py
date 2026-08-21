#!/usr/bin/env python3
"""Check that what the documentation says about each module is still true.

Nine checks, in order of how badly each one bites:

1. reality      — every module's declared status matches what GitHub actually
                  serves to an anonymous visitor. Catches the case where a repo
                  is published (or unpublished) and the map has not noticed.
2. orphan       — every public repository in the org is accounted for by the
                  registry. Catches the case where a repo was created (or
                  un-retired) on GitHub and nobody added it to the map.
3. pin-freshness — every declared dependency pin still names the newest tag,
                  unless a recorded decision explains why it is intentionally
                  held back.
4. ci-existence  — every required CI workflow actually exists on the module's
                  default branch.
5. retired      — no tracked text file links to a repository we have moved
                  away from. Publishing under a fresh repository forfeits
                  GitHub's automatic redirect, so an old URL is a hard 404.
6. alias        — no tracked text file uses an alternative or former module
                  path when the canonical path is declared in the registry.
7. status-text  — wherever a module link appears, the status wording next to it
                  matches the registry, in that file's language. Catches the
                  reverse of (1): a live link with a stale label beside it.
8. tour         — the FOR-AGENTS.md repository tour lists exactly the published
                  registry modules. Catches documentation drift in either
                  direction without relying on the network.
9. support      — the four README support tables declare one owner-approved set
                  of agent environments in real use. Catches translation drift
                  and stale planned-environment rows without relying on the
                  network.

Run with --offline to skip the network checks (reality, orphan, pin-freshness,
and ci-existence).

Python 3.9+, standard library only.
"""

import argparse
import http.client
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ElementTree

from family_common import DegradedReality


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent

# README.ja.md -> ja, docs/engineering.ja.md -> ja, README.md -> en
LANG_SUFFIX = re.compile(r"\.(?P<lang>[a-z]{2}(?:-[A-Z]{2})?)\.md$")

# Never attribute status wording beyond the link's own local claim.
MAX_STATUS_SPAN = 200

# Every tracked text suffix the retired-repo check scans, not just Markdown —
# a stray reference can hide in a workflow file just as easily as in a doc.
RETIRED_SCAN_SUFFIXES = (".md", ".yml", ".yaml", ".py", ".json", ".toml", ".txt", ".sh")

# The registry legitimately names retired repos inside retired_repos[]; that
# is the one file the retired-reverse-reference check must never flag.
RETIRED_SCAN_EXEMPT = pathlib.Path("registry/modules.json")

# Contract A-8 (Epic #24): the FOR-AGENTS §5 tour table must list every
# published module. Adding an exemption here requires owner approval —
# do not edit this set in an implementation lane.
FOR_AGENTS_TOUR_EXEMPT = frozenset()

# Support-table declaration (issue #44): the README "in real use"
# environments, one canonical set for all four languages. Changing this
# set requires owner approval — do not edit it in an implementation lane.
SUPPORT_IN_USE_ENVIRONMENTS = (
    "Claude Code",
    "Hermes Agent",
    "OpenClaw",
    "Kimi Code",
    "Codex",
)

# Contract #62: maturity is the single required registry-contract field for
# every module. Changing this closed vocabulary requires owner approval — do
# not edit it in an implementation lane.
MODULE_MATURITIES = ("product", "reference")

FOR_AGENTS_TOUR_HEADING = re.compile(r"^## 5\.")
FOR_AGENTS_NEXT_HEADING = re.compile(r"^## ")
FOR_AGENTS_TOUR_REPO = re.compile(
    r"github\.com/(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"
)

REPOSITORY_PATH = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
WORKFLOW_NAME = re.compile(r"^[^/]+\.yml$")

# GitHub's Link header, e.g. '<https://...&page=2>; rel="next", <...>; rel="last"'.
LINK_NEXT = re.compile(r'<(?P<url>[^>]+)>\s*;\s*rel="next"')


def language_of(path: pathlib.Path) -> str:
    match = LANG_SUFFIX.search(path.name)
    return match.group("lang") if match else "en"


def markdown_files(root: pathlib.Path):
    for path in sorted(root.rglob("*.md")):
        if ".git" in path.parts:
            continue
        yield path


def retired_scan_files(root: pathlib.Path):
    """Every tracked text file the retired-reverse-reference check scans.

    Broader than markdown_files: a retired link can hide in a workflow file
    (the family-links.yml:111 class of bug) just as easily as in a doc.
    registry/modules.json is excluded — it legitimately names retired repos
    inside retired_repos[].
    """
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if ".git" in path.parts:
            continue
        if path.suffix not in RETIRED_SCAN_SUFFIXES:
            continue
        if path.relative_to(root) == RETIRED_SCAN_EXEMPT:
            continue
        yield path


def scan_repository_references(root: pathlib.Path, entries: dict, report) -> None:
    """Find normal and regex-escaped GitHub paths in tracked text files."""
    for path in retired_scan_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for repo, entry in entries.items():
            for needle in ("github.com/%s" % repo, "github\\.com/%s" % repo):
                pattern = re.compile(re.escape(needle) + r"(?![A-Za-z0-9_-])")
                for match in pattern.finditer(text):
                    line = text[: match.start()].count("\n") + 1
                    report(path, line, repo, entry)


def status_span(text: str, start: int) -> str:
    """Return the text that can describe the link ending at ``start``."""
    end = min(len(text), start + MAX_STATUS_SPAN)
    for boundary in ("\n", "]("):
        boundary_index = text.find(boundary, start, end)
        if boundary_index != -1:
            end = min(end, boundary_index)
    return text[start:end]


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Expose repository renames instead of following them."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def github_is_public(repo: str, timeout: float = 20.0):
    """Anonymous check, deliberately unauthenticated.

    A token would see private repositories and report them as fine — which is
    exactly the blindness this check exists to remove. The web endpoint keeps
    that anonymity while sidestepping the anonymous API's 60-request-per-hour
    quota, which made skips common on shared CI runner IPs. Redirects are not
    followed so repository renames become detectable drift.

    Returns True for a public repository; False for private, absent, or
    unavailable repositories (404/410/451); a ``("moved", location)`` tuple
    for any redirect; an ``("unexpected", status)`` tuple for any other HTTP
    status; and None when GitHub could not be reached. Push and pull-request runs intentionally leave
    that last case non-fatal, so a flaky network never reads as a confirmed
    mismatch.
    """
    request = urllib.request.Request(
        "https://github.com/%s" % repo,
        method="HEAD",
        headers={"User-Agent": "family-os-registry-check"},
    )
    opener = urllib.request.build_opener(NoRedirectHandler())
    try:
        with opener.open(request, timeout=timeout) as response:
            if response.status == 200:
                return True
            return None
    except urllib.error.HTTPError as exc:
        if 300 <= exc.code <= 399:
            return "moved", exc.headers.get("Location")
        if exc.code == 404:
            return False
        if exc.code in (410, 451):
            return False
        if exc.code == 403 or exc.code == 429 or 500 <= exc.code < 600:
            return None
        return "unexpected", exc.code
    except (urllib.error.URLError, TimeoutError):
        return None


def _append_reality_result(
    repo: str,
    expected_public: bool,
    failures: list,
    degraded: DegradedReality,
    note_suffix: str,
) -> None:
    public = github_is_public(repo)
    if public is None:
        degraded.skip(repo, "%s: could not reach GitHub, reality check skipped" % repo)
        return
    if isinstance(public, tuple) and public[0] == "moved":
        failures.append(
            "moved: %s redirects to %s. Update registry/modules.json with "
            "the current repository name and re-run tools/render.py."
            % (repo, public[1] or "an unspecified location")
        )
        return
    if isinstance(public, tuple) and public[0] == "unexpected":
        degraded.skip(
            repo,
            "degraded: %s: unexpected HTTP status %s, reality check skipped"
            % (repo, public[1]),
        )
        return
    if public != expected_public:
        failures.append(note_suffix % ("PUBLIC" if public else "PRIVATE/absent"))


def check_reality(
    registry: dict, failures: list, notes: list, require_reality: bool = False
) -> int:
    degraded = DegradedReality()
    for module in registry["modules"]:
        repo = module["repo"]
        _append_reality_result(
            repo,
            module["status"] == "published",
            failures,
            degraded,
            (
                "reality: %s is declared '%s' but GitHub serves it as %%s to an "
                "anonymous visitor. Update registry/modules.json and re-run "
                "tools/render.py."
            )
            % (repo, module["status"]),
        )

    map_repo = registry.get("map_repo")
    if map_repo:
        _append_reality_result(
            map_repo,
            True,
            failures,
            degraded,
            (
                "reality: map_repo %s must be public to an anonymous visitor. "
                "Update registry/modules.json if the family map moved."
            )
            % map_repo,
        )

    notes.extend(degraded.notes())
    return degraded.finalize(failures, require_reality)


def fetch_org_repos(org: str, timeout: float = 20.0):
    """Fetch every public repository's full name ("org/name") in an org.

    Anonymous on purpose, same rationale as github_is_public: a token would
    see private repositories too and could leak them into this list. Follows
    the Link: rel="next" header to walk every page rather than trusting the
    org to stay under one page forever.

    Returns the list of full names on success, or None if GitHub could not
    be reached, returned a non-200 status, or the response could not be read
    or parsed (including anonymous rate-limiting) — the caller treats None as
    a non-fatal degraded skip, never a confirmed empty org.
    """
    names = []
    url = "https://api.github.com/orgs/%s/repos?per_page=100&type=public" % org
    opener = urllib.request.build_opener()
    while url:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "family-os-registry-check",
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            with opener.open(request, timeout=timeout) as response:
                if response.status != 200:
                    return None
                payload = json.loads(response.read().decode("utf-8"))
                link_header = response.headers.get("Link")
        except (OSError, http.client.HTTPException, json.JSONDecodeError, UnicodeDecodeError):
            return None
        if not isinstance(payload, list):
            return None
        for entry in payload:
            full_name = entry.get("full_name")
            if full_name:
                names.append(full_name)
        match = LINK_NEXT.search(link_header) if link_header else None
        url = match.group("url") if match else None
    return names


def check_orphan(
    registry: dict, failures: list, notes: list, require_reality: bool = False
) -> int:
    degraded = DegradedReality()
    map_repo = registry.get("map_repo")
    if not map_repo or "/" not in map_repo:
        return 0
    org = map_repo.split("/", 1)[0]

    accounted = {module["repo"].casefold() for module in registry["modules"]}
    accounted.add(map_repo.casefold())
    org_profile_repo = registry.get("org_profile", {}).get("repo")
    if org_profile_repo:
        accounted.add(org_profile_repo.casefold())
    adjacent = registry.get("adjacent")
    if isinstance(adjacent, list):
        for entry in adjacent:
            if isinstance(entry, dict) and _is_repository_path(entry.get("repo")):
                accounted.add(entry["repo"].casefold())
    accounted.update(
        entry["repo"].casefold() for entry in registry.get("retired_repos", [])
    )

    org_repos = fetch_org_repos(org)
    if org_repos is None:
        degraded.skip(
            "org:%s" % org,
            "org:%s: could not reach GitHub, orphan check skipped" % org,
        )
    else:
        for repo in org_repos:
            if repo.casefold() not in accounted:
                failures.append(
                    "orphan: %s is a public repository in %s but is not listed "
                    "in registry/modules.json. Add it to modules[] (or "
                    "adjacent[] if it belongs to the family but is not a module, "
                    "or retired_repos[] if it should stay retired)."
                    % (repo, org)
                )

    notes.extend(degraded.notes())
    return degraded.finalize(failures, require_reality, noun="organizations")


def check_retired(registry: dict, root: pathlib.Path, failures: list) -> None:
    retired = {entry["repo"]: entry for entry in registry.get("retired_repos", [])}
    if not retired:
        return
    def report(path: pathlib.Path, line: int, repo: str, entry: dict) -> None:
        failures.append(
            "retired: %s:%d links to %s, which has moved to %s (%s)"
            % (
                path.relative_to(root),
                line,
                repo,
                entry["superseded_by"],
                entry["reason"],
            )
        )

    scan_repository_references(root, retired, report)


def _is_repository_path(value) -> bool:
    return isinstance(value, str) and REPOSITORY_PATH.fullmatch(value) is not None


def _is_non_empty_string(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_localized_strings(
    *,
    owner: str,
    field: str,
    value,
    languages,
    failures: list,
) -> None:
    if not isinstance(value, dict):
        failures.append(
            "schema: %s: %s must be an object with every declared language" % (owner, field)
        )
        return

    keys = set(value)
    expected = set(languages)
    unknown = sorted(keys - expected)
    if unknown:
        failures.append(
            "schema: %s: %s has unknown languages: %s"
            % (owner, field, ", ".join(unknown))
        )
    for language in languages:
        text = value.get(language)
        if not _is_non_empty_string(text):
            failures.append(
                "schema: %s: %s.%s must be a non-empty string"
                % (owner, field, language)
            )


def _validate_adjacent_text(registry: dict, failures: list) -> None:
    languages = registry.get("languages", [])
    adjacent_text = registry.get("adjacent_text")
    if not isinstance(adjacent_text, dict):
        failures.append("schema: adjacent_text must be an object")
        return

    for label in (
        "heading",
        "intro",
        "table_module",
        "table_what",
        "table_relation",
    ):
        if label not in adjacent_text:
            failures.append("schema: adjacent_text.%s is required" % label)
            continue
        _validate_localized_strings(
            owner="adjacent_text",
            field=label,
            value=adjacent_text[label],
            languages=languages,
            failures=failures,
        )


def check_schema(registry: dict, failures: list) -> int:
    """Fail closed for required maturity and present optional contract fields."""
    checked = 0
    for module in registry.get("modules", []):
        module_id = module.get("id", "<unnamed>") if isinstance(module, dict) else "<unnamed>"
        if not isinstance(module, dict):
            failures.append("schema: %s: module entry must be an object" % module_id)
            continue
        checked += 1

        if module.get("maturity") not in MODULE_MATURITIES:
            failures.append(
                "schema: %s: maturity must be 'product' or 'reference'" % module_id
            )

        if "aliases" in module:
            aliases = module["aliases"]
            if not isinstance(aliases, list) or not all(
                _is_repository_path(alias) for alias in aliases
            ):
                failures.append(
                    "schema: %s: aliases must be a list of owner/name strings"
                    % module_id
                )

        if "depends_on" in module:
            dependencies = module["depends_on"]
            valid = isinstance(dependencies, list)
            if valid:
                for dependency in dependencies:
                    if not isinstance(dependency, dict):
                        valid = False
                        break
                    if set(dependency) - {"repo", "pin", "pin_reason"}:
                        valid = False
                        break
                    if not _is_repository_path(dependency.get("repo")):
                        valid = False
                        break
                    if not isinstance(dependency.get("pin"), str) or not dependency["pin"]:
                        valid = False
                        break
                    if "pin_reason" in dependency and not isinstance(
                        dependency["pin_reason"], str
                    ):
                        valid = False
                        break
            if not valid:
                failures.append(
                    "schema: %s: depends_on must be a list of {repo, pin} entries"
                    % module_id
                )

        if "ci" in module:
            ci = module["ci"]
            if (
                not isinstance(ci, dict)
                or set(ci) != {"required", "workflow"}
                or ci.get("required") is not True
                or not isinstance(ci.get("workflow"), str)
                or WORKFLOW_NAME.fullmatch(ci["workflow"]) is None
            ):
                failures.append(
                    "schema: %s: ci must be {required: true, workflow: '<file>.yml'}"
                    % module_id
                )

    adjacent_repos = set()
    adjacent_present = "adjacent" in registry
    adjacent = registry.get("adjacent")
    if adjacent_present and not isinstance(adjacent, list):
        failures.append("schema: adjacent must be a list")
        adjacent = []

    languages = registry.get("languages", [])
    if isinstance(adjacent, list):
        module_repos = {
            module["repo"].casefold()
            for module in registry.get("modules", [])
            if isinstance(module, dict) and _is_repository_path(module.get("repo"))
        }
        allowed_keys = {"id", "name", "repo", "license", "tagline", "relation"}
        for index, entry in enumerate(adjacent):
            owner = "adjacent[%d]" % index
            if not isinstance(entry, dict):
                failures.append("schema: %s: entry must be an object" % owner)
                continue
            entry_id = entry.get("id")
            if _is_non_empty_string(entry_id):
                owner = "adjacent[%d] (%s)" % (index, entry_id)
            unknown = sorted(set(entry) - allowed_keys)
            if unknown:
                failures.append(
                    "schema: %s: unknown keys: %s" % (owner, ", ".join(unknown))
                )
            if not _is_non_empty_string(entry.get("id")):
                failures.append("schema: %s: id must be a non-empty string" % owner)
            if not _is_non_empty_string(entry.get("name")):
                failures.append("schema: %s: name must be a non-empty string" % owner)
            repo = entry.get("repo")
            if not _is_repository_path(repo):
                failures.append(
                    "schema: %s: repo must be a non-empty owner/name string" % owner
                )
            else:
                repo_folded = repo.casefold()
                if repo_folded in module_repos:
                    failures.append(
                        "schema: %s: repo %s may not appear in both modules[] and adjacent[]"
                        % (owner, repo)
                    )
                if repo_folded in adjacent_repos:
                    failures.append(
                        "schema: %s: repo %s appears more than once in adjacent[]"
                        % (owner, repo)
                    )
                adjacent_repos.add(repo_folded)
            if not _is_non_empty_string(entry.get("license")):
                failures.append("schema: %s: license must be a non-empty string" % owner)
            _validate_localized_strings(
                owner=owner,
                field="tagline",
                value=entry.get("tagline"),
                languages=languages,
                failures=failures,
            )
            _validate_localized_strings(
                owner=owner,
                field="relation",
                value=entry.get("relation"),
                languages=languages,
                failures=failures,
            )

    if adjacent_present or "adjacent_text" in registry:
        _validate_adjacent_text(registry, failures)
    return checked


def check_aliases(registry: dict, root: pathlib.Path, failures: list) -> int:
    aliases = {}
    for module in registry.get("modules", []):
        if not isinstance(module, dict) or not isinstance(module.get("aliases"), list):
            continue
        for alias in module["aliases"]:
            if isinstance(alias, str):
                aliases[alias] = module.get("repo", "<unknown>")
    if not aliases:
        return 0

    def report(path: pathlib.Path, line: int, alias: str, canonical: str) -> None:
        failures.append(
            "alias: %s:%d references %s, an alias of %s — use the canonical path"
            % (path.relative_to(root), line, alias, canonical)
        )

    scan_repository_references(root, aliases, report)
    return len(aliases)


def fetch_newest_tag(repo: str, timeout: float = 20.0):
    """Return GitHub's newest tag according to the tags Atom feed, or None.

    GitHub orders this feed by tag creation date, newest first. The contract is
    therefore the newest tag, rather than the largest semantic version.
    """
    request = urllib.request.Request(
        "https://github.com/%s/tags.atom" % repo,
        headers={"User-Agent": "family-os-registry-check"},
    )
    try:
        with urllib.request.build_opener().open(request, timeout=timeout) as response:
            if response.status != 200:
                return None
            payload = response.read()
        root = ElementTree.fromstring(payload)
    except (
        OSError,
        http.client.HTTPException,
        LookupError,
        UnicodeError,
        ElementTree.ParseError,
    ):
        return None

    # GitHub orders Atom entries by tag creation date, newest first.
    entry = next(
        (element for element in root.iter() if element.tag.rsplit("}", 1)[-1] == "entry"),
        None,
    )
    if entry is None:
        return None
    entry_id = next(
        (
            (element.text or "").strip()
            for element in entry
            if element.tag.rsplit("}", 1)[-1] == "id"
        ),
        "",
    )
    if entry_id:
        return entry_id.rsplit("/", 1)[-1]

    title = next(
        (
            (element.text or "").strip()
            for element in entry
            if element.tag.rsplit("}", 1)[-1] == "title"
        ),
        "",
    )
    if title:
        return title.split(None, 1)[0]
    return None


def check_pin_freshness(
    registry: dict, failures: list, notes: list, require_reality: bool = False
) -> int:
    degraded = DegradedReality()
    for module in registry.get("modules", []):
        if not isinstance(module, dict) or not isinstance(module.get("depends_on"), list):
            continue
        for dependency in module["depends_on"]:
            if not isinstance(dependency, dict):
                continue
            repo = dependency.get("repo")
            pin = dependency.get("pin")
            if not _is_repository_path(repo) or not isinstance(pin, str):
                continue
            newest = fetch_newest_tag(repo)
            if newest is None:
                degraded.skip(
                    "pin:%s" % repo,
                    "pin:%s: could not fetch newest tag, pin freshness check skipped"
                    % repo,
                )
                continue
            if newest == pin:
                continue
            module_id = module.get("id", module.get("repo", "<unnamed>"))
            if "pin_reason" in dependency:
                reason = dependency["pin_reason"]
                notes.append(
                    "pin-freshness: %s pins %s@%s but the newest tag is %s; "
                    "pin_reason: %s" % (module_id, repo, pin, newest, reason)
                )
                continue
            failures.append(
                "pin-freshness: %s pins %s@%s but the newest tag is %s. "
                "Update the pin or record pin_reason in registry/modules.json."
                % (module_id, repo, pin, newest)
            )

    notes.extend(degraded.notes())
    return degraded.finalize(failures, require_reality, noun="dependency pins")


def github_ci_workflow_exists(repo: str, workflow: str, timeout: float = 20.0):
    """Anonymous no-redirect HEAD request for a workflow on a default branch."""
    request = urllib.request.Request(
        "https://raw.githubusercontent.com/%s/HEAD/.github/workflows/%s"
        % (repo, workflow),
        method="HEAD",
        headers={"User-Agent": "family-os-registry-check"},
    )
    opener = urllib.request.build_opener(NoRedirectHandler())
    try:
        with opener.open(request, timeout=timeout) as response:
            if response.status == 200:
                return True
            return False if response.status == 404 else None
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        return None
    except (OSError, http.client.HTTPException):
        return None


def check_ci_existence(
    registry: dict, failures: list, notes: list, require_reality: bool = False
) -> int:
    degraded = DegradedReality()
    for module in registry.get("modules", []):
        if not isinstance(module, dict) or not isinstance(module.get("ci"), dict):
            continue
        ci = module["ci"]
        if ci.get("required") is not True:
            continue
        repo = module.get("repo")
        workflow = ci.get("workflow")
        if not _is_repository_path(repo) or not isinstance(workflow, str):
            continue
        exists = github_ci_workflow_exists(repo, workflow)
        if exists is None:
            degraded.skip(
                "ci:%s" % repo,
                "ci:%s: could not verify %s, ci existence check skipped"
                % (repo, workflow),
            )
        elif not exists:
            failures.append(
                "ci-existence: %s declares ci.required but %s does not exist on "
                "%s's default branch."
                % (module.get("id", repo), workflow, repo)
            )

    notes.extend(degraded.notes())
    return degraded.finalize(failures, require_reality, noun="CI workflows")


def check_status_text(registry: dict, root: pathlib.Path, failures: list) -> int:
    labels = registry["status_labels"]
    statuses = list(labels)
    checked = 0

    for path in markdown_files(root):
        lang = language_of(path)
        text = path.read_text(encoding="utf-8")

        for module in registry["modules"]:
            url = "https://github.com/%s" % module["repo"]
            pattern = re.compile(re.escape(url) + r"(?![A-Za-z0-9_-])")
            correct = module["status"]
            wrong = [status for status in statuses if status != correct]

            for match in pattern.finditer(text):
                index = match.start()
                start = match.end()
                window = status_span(text, start)

                for status in wrong:
                    label = labels[status].get(lang)
                    if label and label in window:
                        line = text[:index].count("\n") + 1
                        failures.append(
                            "status-text: %s:%d says '%s' next to %s, but the "
                            "registry declares it '%s'"
                            % (
                                path.relative_to(root),
                                line,
                                label,
                                module["name"],
                                correct,
                            )
                        )
                checked += 1

    return checked


def check_for_agents_tour(
    registry: dict, root: pathlib.Path, failures: list
) -> int:
    path = root / "FOR-AGENTS.md"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        failures.append("tour: could not read FOR-AGENTS.md: %s" % exc)
        return 0

    section_found = False
    in_section = False
    tour_repos = set()
    for line in text.splitlines():
        if not in_section:
            if FOR_AGENTS_TOUR_HEADING.match(line):
                section_found = True
                in_section = True
            continue
        if FOR_AGENTS_NEXT_HEADING.match(line):
            break
        if not line.lstrip(" \t").startswith("|"):
            continue
        match = FOR_AGENTS_TOUR_REPO.search(line)
        if match:
            tour_repos.add(match.group("repo"))

    if not section_found:
        failures.append(
            "tour: FOR-AGENTS.md §5 section not found (contract A-8; "
            "refusing to pass without parsing the tour table)"
        )
        return 0
    if not tour_repos:
        failures.append(
            "tour: FOR-AGENTS.md §5 contains zero parsed tour rows "
            "(contract A-8; refusing to pass without parsing the tour table)"
        )
        return 0

    published = {
        module["repo"]
        for module in registry["modules"]
        if module["status"] == "published"
    }
    for repo in sorted(published - tour_repos - FOR_AGENTS_TOUR_EXEMPT):
        failures.append(
            "tour: %s is published in the registry but missing from "
            "FOR-AGENTS.md §5 (contract A-8; add a tour row or get owner "
            "approval for an exemption)" % repo
        )
    for repo in sorted(tour_repos - published):
        failures.append(
            "tour: FOR-AGENTS.md §5 lists %s, which is not a published "
            "module in the registry (remove the row or fix the registry)" % repo
        )

    return len(tour_repos)


def check_support(root: pathlib.Path, failures: list) -> int:
    expected = " ／ ".join("✅ %s" % env for env in SUPPORT_IN_USE_ENVIRONMENTS)
    checked = 0

    for filename in ("README.md", "README.ja.md", "README.zh.md", "README.th.md"):
        path = root / filename
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            failures.append(
                "support: %s: row=<unreadable: %s>; expected %s"
                % (filename, exc, expected)
            )
            continue

        anchor_index = next(
            (
                index
                for index, line in enumerate(lines)
                if line.strip() == '<a id="environments"></a>'
            ),
            None,
        )
        if anchor_index is None:
            failures.append(
                "support: %s: row=<missing environments anchor>; expected %s"
                % (filename, expected)
            )
            continue

        section = []
        for line in lines[anchor_index + 1 :]:
            stripped = line.strip()
            if stripped == "---" or stripped.startswith("<a id="):
                break
            section.append(line)

        rows = [
            line.strip()
            for line in section
            if line.lstrip(" \t").startswith("|")
        ]
        in_use_index = next(
            (index for index, row in enumerate(rows) if "Claude Code" in row),
            None,
        )
        if in_use_index is None:
            failures.append(
                "support: %s: row=<no table row containing Claude Code>; "
                "expected %s" % (filename, expected)
            )
            continue

        checked += 1
        in_use_row = rows[in_use_index]
        declared = []
        for cell in in_use_row.split("|"):
            for item in cell.split("／"):
                match = re.fullmatch(r"\s*✅\s+(.+?)\s*", item)
                if match:
                    declared.append(match.group(1))

        if tuple(declared) != SUPPORT_IN_USE_ENVIRONMENTS or "⚠️" in in_use_row:
            failures.append(
                "support: %s: row=%r; expected exactly %s with no ⚠️"
                % (filename, in_use_row, expected)
            )

        for index, row in enumerate(rows):
            if index == in_use_index:
                continue
            if any(env in row for env in SUPPORT_IN_USE_ENVIRONMENTS):
                failures.append(
                    "support: %s: row=%r; expected declared environments only "
                    "in the in-use row %r" % (filename, row, in_use_row)
                )

    return checked


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="skip the GitHub reality, orphan, pin-freshness, and CI checks",
    )
    parser.add_argument(
        "--require-reality",
        action="store_true",
        help="fail if any module or the orphan check cannot be verified against GitHub",
    )
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=REPO_ROOT,
        help="repository checkout to inspect (default: the checkout containing this script)",
    )
    args = parser.parse_args()
    if args.offline and args.require_reality:
        parser.error("--require-reality cannot be combined with --offline")

    root = args.root.expanduser().resolve()
    registry_path = root / "registry" / "modules.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print("ERROR: could not read %s: %s" % (registry_path, exc), file=sys.stderr)
        return 1

    failures: list = []
    notes: list = []

    schema_modules = check_schema(registry, failures)

    skipped = 0
    orphan_skipped = 0
    pin_skipped = 0
    ci_skipped = 0
    if not args.offline:
        skipped = check_reality(registry, failures, notes, args.require_reality)
        orphan_skipped = check_orphan(registry, failures, notes, args.require_reality)
        pin_skipped = check_pin_freshness(
            registry, failures, notes, args.require_reality
        )
        ci_skipped = check_ci_existence(
            registry, failures, notes, args.require_reality
        )
    check_retired(registry, root, failures)
    aliases = check_aliases(registry, root, failures)
    occurrences = check_status_text(registry, root, failures)
    tour_rows = check_for_agents_tour(registry, root, failures)
    support_tables = check_support(root, failures)

    adjacent = registry.get("adjacent")
    adjacent_count = len(adjacent) if isinstance(adjacent, list) else 0
    print("modules in registry : %d" % len(registry["modules"]))
    print("adjacent entries    : %d" % adjacent_count)
    print("schema check        : %d modules" % schema_modules)
    print("alias check         : %d aliases" % aliases)
    print("retired repositories: %d" % len(registry.get("retired_repos", [])))
    print("link occurrences    : %d" % occurrences)
    print("tour rows           : %d" % tour_rows)
    print("support tables      : %d" % support_tables)
    print("reality check       : %s" % ("skipped" if args.offline else "on (anonymous)"))
    if not args.offline:
        reality_targets = len(registry["modules"]) + (1 if registry.get("map_repo") else 0)
        print("reality skipped    : %d of %d" % (skipped, reality_targets))
    print("orphan check        : %s" % ("skipped" if args.offline else "on (anonymous)"))
    if not args.offline:
        print("orphan skipped      : %d of 1" % orphan_skipped)
    print(
        "pin freshness check : %s" % ("skipped" if args.offline else "on (anonymous)")
    )
    if not args.offline:
        pin_targets = sum(
            len(module.get("depends_on", []))
            for module in registry["modules"]
            if isinstance(module, dict) and isinstance(module.get("depends_on"), list)
        )
        print("pin freshness skipped: %d of %d" % (pin_skipped, pin_targets))
    print(
        "ci existence check  : %s" % ("skipped" if args.offline else "on (anonymous)")
    )
    if not args.offline:
        ci_targets = sum(
            1
            for module in registry["modules"]
            if isinstance(module, dict)
            and isinstance(module.get("ci"), dict)
            and module["ci"].get("required") is True
        )
        print("ci existence skipped: %d of %d" % (ci_skipped, ci_targets))

    for note in notes:
        print("  note: %s" % note)

    if failures:
        print("\nFAILED (%d):" % len(failures))
        for failure in failures:
            print("  - %s" % failure)
        return 1

    print("\nOK — every module claim matches the registry.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
