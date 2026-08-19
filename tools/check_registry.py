#!/usr/bin/env python3
"""Check that what the documentation says about each module is still true.

Four checks, in order of how badly each one bites:

1. reality      — every module's declared status matches what GitHub actually
                  serves to an anonymous visitor. Catches the case where a repo
                  is published (or unpublished) and the map has not noticed.
2. orphan       — every public repository in the org is accounted for by the
                  registry. Catches the case where a repo was created (or
                  un-retired) on GitHub and nobody added it to the map.
3. retired      — no tracked text file links to a repository we have moved
                  away from. Publishing under a fresh repository forfeits
                  GitHub's automatic redirect, so an old URL is a hard 404.
4. status-text  — wherever a module link appears, the status wording next to it
                  matches the registry, in that file's language. Catches the
                  reverse of (1): a live link with a stale label beside it.

Run with --offline to skip the network checks (reality and orphan).

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
                    "retired_repos[] if it should stay retired)."
                    % (repo, org)
                )

    notes.extend(degraded.notes())
    return degraded.finalize(failures, require_reality, noun="organizations")


def check_retired(registry: dict, root: pathlib.Path, failures: list) -> None:
    retired = {entry["repo"]: entry for entry in registry.get("retired_repos", [])}
    if not retired:
        return
    for path in retired_scan_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for repo, entry in retired.items():
            for needle in ("github.com/%s" % repo, "github\\.com/%s" % repo):
                pattern = re.compile(re.escape(needle) + r"(?![A-Za-z0-9_-])")
                for match in pattern.finditer(text):
                    line = text[: match.start()].count("\n") + 1
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="skip the GitHub reality and orphan checks",
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

    skipped = 0
    orphan_skipped = 0
    if not args.offline:
        skipped = check_reality(registry, failures, notes, args.require_reality)
        orphan_skipped = check_orphan(registry, failures, notes, args.require_reality)
    check_retired(registry, root, failures)
    occurrences = check_status_text(registry, root, failures)

    print("modules in registry : %d" % len(registry["modules"]))
    print("retired repositories: %d" % len(registry.get("retired_repos", [])))
    print("link occurrences    : %d" % occurrences)
    print("reality check       : %s" % ("skipped" if args.offline else "on (anonymous)"))
    if not args.offline:
        reality_targets = len(registry["modules"]) + (1 if registry.get("map_repo") else 0)
        print("reality skipped    : %d of %d" % (skipped, reality_targets))
    print("orphan check        : %s" % ("skipped" if args.offline else "on (anonymous)"))
    if not args.offline:
        print("orphan skipped      : %d of 1" % orphan_skipped)

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
