#!/usr/bin/env python3
"""Fail closed when publication sources expose private context or stale state.

The denylist is repository policy, not checker source.  Normal runs require an
account slug so personal-account URLs are always checked.  Registry-backed
label, SVG, allowlist, and whitelist-staleness checks are optional.

Python 3.9+, standard library only.
"""

import argparse
from contextlib import redirect_stdout
import html
import io
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.parse


EXCLUDED_DIRS = frozenset(
    (".git", ".omc", ".omx", ".venv", "venv", "node_modules", "__pycache__")
)
DENYLIST_NAME = ".publication-denylist"
WHITELIST_NAME = ".publication-label-whitelist"
ACCOUNT_SLUG = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37})$")
URL_CANDIDATE = re.compile(
    r"(?<![A-Za-z0-9@._-])(?:https?://(?:[A-Za-z0-9._~!$&'()*+,;=:%-]+@)?)?"
    r"(?:[A-Za-z0-9-]+\.)+[A-Za-z0-9-]+\.?(?::[0-9]+)?"
    r"(?:/[^\s<>'\"`()\[\]{}]*)?",
    re.IGNORECASE,
)
LANG_SUFFIX = re.compile(r"\.(?P<lang>[a-z]{2}(?:-[a-z]{2})?)\.md$")
SVG_TEXT_ELEMENT = re.compile(
    r"<(text|title|desc|metadata)\b[^>]*>(.*?)</\1\s*>", re.IGNORECASE | re.DOTALL
)
SVG_TEXT_ATTRIBUTE = re.compile(
    r"\b(?:title|aria-label|alt)\s*=\s*(?P<quote>['\"])(?P<value>.*?)(?P=quote)",
    re.IGNORECASE | re.DOTALL,
)
SVG_CDATA = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.DOTALL)


class GateConfigurationError(ValueError):
    """A fail-closed policy or command configuration error."""


def language_of(path):
    match = LANG_SUFFIX.search(path.name.lower())
    return match.group("lang") if match else "en"


def scan_views(text):
    """Return raw plus iterative percent/HTML-decoded views."""
    views = [text]
    current = text
    for _ in range(3):
        unquoted = urllib.parse.unquote(current)
        if unquoted not in views:
            views.append(unquoted)
        unescaped = html.unescape(unquoted)
        if unescaped not in views:
            views.append(unescaped)
        if unescaped == current:
            break
        current = unescaped
    return tuple(views)


def line_number(text, offset):
    return text.count("\n", 0, offset) + 1


def _read_utf8(path, display_name):
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise GateConfigurationError(
            "gate-error: %s could not be read as UTF-8: %s" % (display_name, exc)
        ) from exc


def _denylist_error_name(root, path):
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def denylist_path(root, denylist_argument=None):
    if denylist_argument is None:
        return root / DENYLIST_NAME
    path = Path(denylist_argument).expanduser()
    if not path.is_absolute():
        path = root / path
    return Path(os.path.abspath(str(path)))


def load_denylist(root, denylist_argument=None):
    """Load NAME<TAB>REGEX policy, failing closed on absence or zero rules."""
    path = denylist_path(root, denylist_argument)
    display_name = _denylist_error_name(root, path)
    if not path.is_file():
        raise GateConfigurationError(
            "gate-error: %s missing/empty — a publication gate with no denylist proves nothing (fail-closed)"
            % display_name
        )
    text = _read_utf8(path, display_name)
    if text.startswith("\ufeff"):
        text = text[1:]
    rules = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        if "\t" not in line:
            raise GateConfigurationError(
                "gate-error: %s:%d malformed rule: expected NAME<TAB>REGEX"
                % (display_name, number)
            )
        name, expression = line.split("\t", 1)
        if not name or name.isspace() or any(character.isspace() for character in name):
            raise GateConfigurationError(
                "gate-error: %s:%d malformed rule: NAME must be non-empty and contain no whitespace"
                % (display_name, number)
            )
        if not expression:
            raise GateConfigurationError(
                "gate-error: %s:%d malformed rule: REGEX must be non-empty"
                % (display_name, number)
            )
        if "\t" in expression:
            raise GateConfigurationError(
                "gate-error: %s:%d malformed rule: extra TAB fields are not allowed; write \\t explicitly in REGEX"
                % (display_name, number)
            )
        if expression != expression.strip():
            raise GateConfigurationError(
                "gate-error: %s:%d malformed rule: REGEX must not have leading/trailing whitespace; write \\s or [ ] explicitly"
                % (display_name, number)
            )
        try:
            pattern = re.compile(expression, re.IGNORECASE)
        except re.error as exc:
            raise GateConfigurationError(
                "gate-error: %s:%d invalid regex for %s: %s"
                % (display_name, number, name, exc)
            ) from exc
        rules.append((name, pattern))
    if not rules:
        raise GateConfigurationError(
            "gate-error: %s missing/empty — a publication gate with no denylist proves nothing (fail-closed)"
            % display_name
        )
    return tuple(rules)


def load_label_whitelist(root):
    """Load optional PATH<TAB>EXACT_LINE label exemptions."""
    path = root / WHITELIST_NAME
    if not path.exists():
        return frozenset()
    if not path.is_file():
        raise GateConfigurationError("gate-error: %s is not a regular file" % WHITELIST_NAME)
    text = _read_utf8(path, WHITELIST_NAME)
    entries = set()
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        if "\t" not in line:
            raise GateConfigurationError(
                "gate-error: %s:%d malformed entry: expected PATH<TAB>EXACT_LINE"
                % (WHITELIST_NAME, number)
            )
        path_text, exact_line = line.split("\t", 1)
        if not path_text or not exact_line:
            raise GateConfigurationError(
                "gate-error: %s:%d malformed entry: PATH and EXACT_LINE must be non-empty"
                % (WHITELIST_NAME, number)
            )
        entries.add((Path(path_text).as_posix(), exact_line))
    return frozenset(entries)


def _git_paths(root):
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise GateConfigurationError(
            "gate-error: git enumeration failed for a root containing .git: %s" % exc
        ) from exc
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise GateConfigurationError(
            "gate-error: git enumeration failed for a root containing .git: %s"
            % (detail or "git ls-files exited %d" % result.returncode)
        )
    paths = []
    for relative_bytes in filter(None, result.stdout.split(b"\0")):
        try:
            relative = relative_bytes.decode("utf-8")
        except UnicodeError as exc:
            raise GateConfigurationError(
                "gate-error: git enumeration returned a non-UTF-8 path: %s" % exc
            ) from exc
        paths.append(root / relative)
    return paths


def _contains_git_entry(root):
    return os.path.lexists(str(root / ".git"))


def iter_source_paths(root, excluded_policy_path):
    """Return (paths, mode); only the non-git fallback applies EXCLUDED_DIRS."""
    git_mode = _contains_git_entry(root)
    paths = _git_paths(root) if git_mode else root.rglob("*")
    policy_key = os.path.abspath(str(excluded_policy_path))
    selected = []
    for path in paths:
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if not git_mode and any(part in EXCLUDED_DIRS for part in relative.parts[:-1]):
            continue
        if os.path.abspath(str(path)) == policy_key:
            continue
        selected.append(path)
    ordered = sorted(selected, key=lambda candidate: candidate.relative_to(root).as_posix())
    return ordered, "git" if git_mode else "rglob-fallback"


def read_sources(root, failures, excluded_policy_path):
    documents = {}
    binary_skipped = 0
    symlinks_skipped = 0
    paths, enumeration_mode = iter_source_paths(root, excluded_policy_path)
    for path in paths:
        relative = path.relative_to(root).as_posix()
        try:
            if path.is_symlink():
                if enumeration_mode == "git":
                    documents[relative] = os.readlink(path)
                else:
                    symlinks_skipped += 1
                continue
            mode = os.lstat(path).st_mode
            if stat.S_ISDIR(mode):
                continue
            if not stat.S_ISREG(mode):
                failures.append("source-read: %s is not a regular file" % relative)
                continue
            try:
                documents[relative] = path.read_bytes().decode("utf-8")
            except UnicodeDecodeError:
                binary_skipped += 1
        except OSError as exc:
            failures.append("source-read: %s could not be read: %s" % (relative, exc))
    return documents, enumeration_mode, binary_skipped, symlinks_skipped


def check_denylist(documents, rules, failures):
    checked = 0
    for path, text in documents.items():
        reported = set()
        for view_index, view in enumerate(scan_views(text)):
            for description, pattern in rules:
                for match in pattern.finditer(view):
                    finding = (line_number(view, match.start()), description)
                    if finding in reported:
                        continue
                    reported.add(finding)
                    failures.append(
                        "denylist: %s:%d contains %s%s"
                        % (
                            path,
                            finding[0],
                            description,
                            "" if view_index == 0 else " (decoded view)",
                        )
                    )
                    checked += 1
    return checked


def _personal_url(candidate, account_slug):
    candidate = candidate.rstrip(".,;:!?")
    parsed = urllib.parse.urlsplit(candidate if "://" in candidate else "//" + candidate)
    host = (parsed.hostname or "").casefold()
    if host.endswith("."):
        host = host[:-1]
    if host.startswith("www."):
        host = host[4:]
    segments = [urllib.parse.unquote(segment) for segment in parsed.path.split("/") if segment]
    folded_slug = account_slug.casefold()
    if host == "github.com" and segments and segments[0].casefold() == folded_slug:
        return segments[1] if len(segments) > 1 else None
    if host == "gist.github.com" and segments and segments[0].casefold() == folded_slug:
        return None
    if host == folded_slug + ".github.io":
        return account_slug + ".github.io"
    return False


def registry_allowlist(registry):
    repos = {module["repo"] for module in registry["modules"]}
    repos.update(entry["repo"] for entry in registry.get("retired_repos", []))
    if not all(isinstance(repo, str) and "/" in repo for repo in repos):
        raise ValueError("module and retired repository names must be owner/repository strings")
    return {repo.casefold() for repo in repos}


def check_personal_urls(documents, account_slug, registry, failures):
    allowlist = registry_allowlist(registry) if registry is not None else None
    checked = 0
    for path, text in documents.items():
        reported = set()
        for view_index, view in enumerate(scan_views(text)):
            for match in URL_CANDIDATE.finditer(view):
                repo_name = _personal_url(match.group(0), account_slug)
                if repo_name is False:
                    continue
                number = line_number(view, match.start())
                repo = "%s/%s" % (account_slug, repo_name) if repo_name else account_slug
                finding = (number, repo.casefold())
                if finding in reported:
                    continue
                reported.add(finding)
                checked += 1
                view_marker = "" if view_index == 0 else " (decoded view)"
                if repo_name is None:
                    failures.append(
                        "personal-url: %s:%d references personal account profile %s%s"
                        % (path, number, account_slug, view_marker)
                    )
                elif allowlist is None:
                    failures.append(
                        "personal-url: %s:%d references personal account repository %s%s"
                        % (path, number, repo, view_marker)
                    )
                elif repo.casefold() not in allowlist:
                    failures.append(
                        "personal-url: %s:%d references unknown repository %s%s"
                        % (path, number, repo, view_marker)
                    )
    return checked


def check_corpus_floor(documents, anchor, failures):
    failed = 0
    if not documents:
        failures.append("corpus-floor: no publication source documents were scanned")
        failed += 1
    if anchor is not None and anchor not in documents:
        failures.append("corpus-floor: %s was not among scanned documents" % anchor)
        failed += 1
    return failed


def repo_home_pattern(repo):
    base = r"(?<![A-Za-z0-9.-])(?:https?://)?(?:www\.)?github\.com/" + re.escape(repo)
    terminator = r"(?:/(?=$|[^A-Za-z0-9_.~%-])|(?=$|[^/A-Za-z0-9_.-]|\.(?![A-Za-z0-9_-])))"
    return re.compile(base + terminator, re.IGNORECASE)


def check_whitelist_staleness(documents, whitelist, failures):
    stale = 0
    for path, expected_line in sorted(whitelist):
        source = documents.get(path)
        if source is not None and expected_line in source.split("\n"):
            continue
        failures.append("stale-whitelist: %s no longer contains the exact approved line" % path)
        stale += 1
    return stale


def check_missing_labels(markdown, registry, whitelist, failures):
    labels = registry["status_labels"]
    map_repo = registry.get("map_repo")
    checked = 0
    for path_text, text in markdown.items():
        language = language_of(Path(path_text))
        for module in registry["modules"]:
            if module["repo"] == map_repo:
                continue
            try:
                label = labels[module["status"]][language]
            except (KeyError, TypeError) as exc:
                failures.append(
                    "missing-label: registry has no label for %s status=%s language=%s (%s)"
                    % (module.get("repo", "<unknown>"), module.get("status", "<unknown>"), language, exc)
                )
                continue
            pattern = repo_home_pattern(module["repo"])
            for number, line in enumerate(text.splitlines(), 1):
                if not pattern.search(line):
                    continue
                checked += 1
                if label not in line and (path_text, line) not in whitelist:
                    failures.append(
                        "missing-label: %s:%d links to %s without '%s' on the same line"
                        % (path_text, number, module["repo"], label)
                    )
    return checked


def module_names(module):
    name = module["name"]
    if isinstance(name, str):
        names = {name}
    elif isinstance(name, dict) and all(isinstance(value, str) for value in name.values()):
        names = set(name.values())
    else:
        raise ValueError("modules[].name must be a string or language-to-string object")
    names.add(module["repo"].rsplit("/", 1)[-1])
    return {value for value in names if value}


def name_pattern(name):
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])", re.IGNORECASE)


def svg_visible_text(source):
    chunks = []
    for match in SVG_TEXT_ELEMENT.finditer(source):
        preserved = SVG_CDATA.sub(lambda item: item.group(1), match.group(2))
        chunks.append(html.unescape(re.sub(r"<[^>]+>", " ", preserved)))
    for match in SVG_TEXT_ATTRIBUTE.finditer(source):
        chunks.append(html.unescape(match.group("value")))
    return re.sub(r"\s+", " ", " ".join(chunks)).strip()


def markdown_status_evidence(markdown, registry):
    labels = registry["status_labels"]
    evidence = {module["repo"]: False for module in registry["modules"]}
    for path_text, text in markdown.items():
        language = language_of(Path(path_text))
        for module in registry["modules"]:
            try:
                label = labels[module["status"]][language]
            except (KeyError, TypeError):
                continue
            markers = module_names(module)
            markers.add("github.com/%s" % module["repo"])
            if any(
                label in line and any(name_pattern(marker).search(line) for marker in markers)
                for line in text.splitlines()
            ):
                evidence[module["repo"]] = True
    return evidence


def check_svg_state_sources(svg_documents, markdown, registry, failures):
    evidence = markdown_status_evidence(markdown, registry)
    checked = 0
    for path, source in svg_documents.items():
        visible = svg_visible_text(source)
        compact_visible = re.sub(r"\s+", "", visible).casefold()
        for module in registry["modules"]:
            for name in sorted(module_names(module)):
                matched = bool(name_pattern(name).search(visible))
                if not matched:
                    compact_name = re.sub(r"\s+", "", name).casefold()
                    matched = bool(compact_name) and compact_name in compact_visible
                if not matched:
                    continue
                checked += 1
                if not evidence[module["repo"]]:
                    failures.append(
                        "svg-state: %s contains '%s' for %s, but no Markdown line carries its name/link and status label"
                        % (path, name, module["repo"])
                    )
    return checked


def load_registry(path):
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GateConfigurationError(
            "gate-error: registry could not be read as UTF-8 JSON: %s" % exc
        ) from exc
    if not isinstance(registry, dict):
        raise GateConfigurationError("gate-error: registry must be a JSON object")
    if not isinstance(registry.get("modules"), list) or not registry["modules"]:
        raise GateConfigurationError("gate-error: registry modules must be a non-empty list")
    if not isinstance(registry.get("status_labels"), dict):
        raise GateConfigurationError("gate-error: registry status_labels must be an object")
    return registry


def partition_documents(documents):
    markdown = {path: text for path, text in documents.items() if path.lower().endswith(".md")}
    svg_documents = {path: text for path, text in documents.items() if path.lower().endswith(".svg")}
    return markdown, svg_documents


SKIP_NOTICES = (
    "notice: registry allowlist check skipped (--registry not provided)",
    "notice: missing-label check skipped (--registry not provided)",
    "notice: SVG-state check skipped (--registry not provided)",
    "notice: whitelist-staleness check skipped (--registry not provided)",
)


def run_gate(root, account_slug, registry_argument=None, denylist_argument=None):
    root = Path(root).expanduser().resolve()
    failures = []
    documents = {}
    rules = ()
    whitelist = frozenset()
    registry = None
    registry_relative = None
    corpus_anchor = "README.md"
    denylist_hits = 0
    personal_urls = 0
    root_links = 0
    svg_names = 0
    enumeration_mode = "git" if _contains_git_entry(root) else "rglob-fallback"
    binary_skipped = 0
    symlinks_skipped = 0
    policy_path = denylist_path(root, denylist_argument)

    normalized_slug = account_slug.strip() if account_slug is not None else ""
    if not normalized_slug:
        failures.append("gate-error: --account-slug is required for publication URL checks (fail-closed)")
    elif not ACCOUNT_SLUG.fullmatch(normalized_slug):
        failures.append(
            "gate-error: --account-slug must match ^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37})$ (fail-closed)"
        )
        normalized_slug = ""

    try:
        rules = load_denylist(root, denylist_argument)
    except GateConfigurationError as exc:
        failures.append(str(exc))
    try:
        whitelist = load_label_whitelist(root)
    except GateConfigurationError as exc:
        failures.append(str(exc))

    registry_path = None
    if registry_argument is not None:
        registry_path = Path(registry_argument).expanduser()
        if not registry_path.is_absolute():
            registry_path = root / registry_path
        registry_path = registry_path.resolve()
        try:
            registry_relative = registry_path.relative_to(root).as_posix()
        except ValueError:
            failures.append(
                "gate-error: --registry must resolve inside --root (fail-closed)"
            )
            corpus_anchor = None
        else:
            corpus_anchor = registry_relative
            try:
                registry = load_registry(registry_path)
            except GateConfigurationError as exc:
                failures.append(str(exc))

    try:
        documents, enumeration_mode, binary_skipped, symlinks_skipped = read_sources(
            root, failures, policy_path
        )
        check_corpus_floor(documents, corpus_anchor, failures)
        if rules:
            denylist_hits = check_denylist(documents, rules, failures)
        if normalized_slug:
            personal_urls = check_personal_urls(documents, normalized_slug, registry, failures)
        if registry is not None:
            markdown, svg_documents = partition_documents(documents)
            check_whitelist_staleness(documents, whitelist, failures)
            root_links = check_missing_labels(markdown, registry, whitelist, failures)
            svg_names = check_svg_state_sources(svg_documents, markdown, registry, failures)
    except GateConfigurationError as exc:
        failures.append(str(exc))
    except (KeyError, OSError, UnicodeError, ValueError) as exc:
        failures.append("gate-error: publication checks could not complete: %s" % exc)

    print("enumeration: %s" % enumeration_mode)
    print("source files scanned : %d" % len(documents))
    print("binary files skipped: %d" % binary_skipped)
    if enumeration_mode == "rglob-fallback":
        print("symlinks skipped: %d" % symlinks_skipped)
    print("denylist rules loaded : %d" % len(rules))
    print("denylist matches     : %d" % denylist_hits)
    print("personal URLs checked: %d" % personal_urls)
    print("module links checked : %d" % root_links)
    print("SVG names checked    : %d" % svg_names)
    print("label whitelist      : %d" % len(whitelist))
    if registry_argument is None:
        for notice in SKIP_NOTICES:
            print(notice)

    if failures:
        print("\nFAILED (%d):" % len(failures))
        for failure in failures:
            print("  - %s" % failure)
        return 1
    print("\nOK — publication gate passed with %d explicit label whitelist entries." % len(whitelist))
    return 0


SELFTEST_DENYLIST = (
    "# Embedded policy fixture.\n"
    "private-marker\tacme[-_ ]" "secret\n"
    "private-host\tprivate\\.example\\.invalid\n"
)
SELFTEST_CLEAN_README = "# Public project\n\nPublication-safe example content.\n"
SELFTEST_VIOLATING_README = (
    "# Internal project\n\nThis exposes an acme-" "secret marker.\n"
)
SELFTEST_ASSERTIONS = 0


def _selftest_check(condition, message):
    global SELFTEST_ASSERTIONS
    SELFTEST_ASSERTIONS += 1
    if not condition:
        raise RuntimeError("selftest failed: %s" % message)


def _fixture_registry(account_slug="neutral-owner"):
    return {
        "languages": ["en", "ja"],
        "map_repo": "example-org/map",
        "status_labels": {"published": {"en": "published, MIT", "ja": "公開・MIT"}},
        "modules": [
            {"name": "Example Module", "repo": "example-org/example-module", "status": "published"}
        ],
        "retired_repos": [{"repo": account_slug + "/public-archive"}],
    }


def _capture_main(arguments):
    output = io.StringIO()
    with redirect_stdout(output):
        status = main(arguments)
    return status, output.getvalue()


def _fixture_personal_url(account_slug, repository=None):
    url = "https://" + "github." + "com/" + account_slug
    return url + "/" + repository if repository else url


def _fixture_module_link(repo="example-org/example-module"):
    return "https://" + "github." + "com/" + repo


def _fixture_module_line(with_status=True):
    line = "[Example Module](" + _fixture_module_link() + ")"
    return line + " — published, MIT" if with_status else line


def _fixture_email(local_part, domain):
    return local_part + "@" + domain


def _fixture_userinfo_personal_url(account_slug, repository, username, host=None):
    target_host = host or ("github." + "com")
    return "https://" + username + "@" + target_host + "/" + account_slug + "/" + repository


def selftest_policy_parsers():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        try:
            load_denylist(root)
        except GateConfigurationError as exc:
            _selftest_check(
                str(exc)
                == "gate-error: .publication-denylist missing/empty — a publication gate with no denylist proves nothing (fail-closed)",
                "missing denylist",
            )
        else:
            raise RuntimeError("selftest failed: missing denylist accepted")
        (root / DENYLIST_NAME).write_text("# comment\n\n", encoding="utf-8")
        try:
            load_denylist(root)
        except GateConfigurationError as exc:
            _selftest_check("missing/empty" in str(exc), "zero-rule denylist")
        else:
            raise RuntimeError("selftest failed: zero-rule denylist accepted")
        malformed = (
            ("broken\n", ":1 malformed rule"),
            ("name\t[\n", ":1 invalid regex"),
            ("bad name\tmarker\n", ":1 malformed rule"),
            ("\tmarker\n", ":1 malformed rule"),
            ("bad\tname\tmarker\n", ":1 malformed rule"),
            ("name\t marker\n", "write \\s or [ ] explicitly"),
            ("name\tmarker \n", "write \\s or [ ] explicitly"),
        )
        for source, marker in malformed:
            (root / DENYLIST_NAME).write_text(source, encoding="utf-8")
            try:
                load_denylist(root)
            except GateConfigurationError as exc:
                _selftest_check(marker in str(exc), "line-numbered policy error")
            else:
                raise RuntimeError("selftest failed: malformed denylist accepted")
        (root / DENYLIST_NAME).write_text(
            "\ufeff# BOM-prefixed comment\nmarker\tprivate(?:\\t|[ ])+marker\n",
            encoding="utf-8",
        )
        _selftest_check(len(load_denylist(root)) == 1, "BOM comment and explicit whitespace regex")
        _selftest_check(load_label_whitelist(root) == frozenset(), "absent whitelist")
        (root / WHITELIST_NAME).write_text("README.md\tapproved exact line\n", encoding="utf-8")
        _selftest_check(("README.md", "approved exact line") in load_label_whitelist(root), "whitelist parser")
        registry_path = root / "registry.json"
        registry_path.write_text("[]\n", encoding="utf-8")
        try:
            load_registry(registry_path)
        except GateConfigurationError as exc:
            _selftest_check(
                str(exc) == "gate-error: registry must be a JSON object",
                "non-object registry error",
            )
        else:
            raise RuntimeError("selftest failed: non-object registry accepted")


def selftest_scanners():
    rules = (("private marker", re.compile("private" + "[- ]marker", re.IGNORECASE)),)
    failures = []
    documents = {"README.md": "private%2Dmarker\n"}
    _selftest_check(
        check_denylist(documents, rules, failures) == 1
        and "(decoded view)" in failures[0],
        "decoded denylist marker",
    )
    raw_line_failures = []
    _selftest_check(
        check_denylist(
            {"README.md": "safe\nprivate-marker\n"}, rules, raw_line_failures
        )
        == 1
        and "README.md:2" in raw_line_failures[0]
        and "(decoded view)" not in raw_line_failures[0],
        "raw-view line number",
    )
    decoded_line_failures = []
    _selftest_check(
        check_denylist(
            {"README.md": "safe%0Aprivate%2Dmarker\n"}, rules, decoded_line_failures
        )
        == 1
        and "README.md:2" in decoded_line_failures[0]
        and "(decoded view)" in decoded_line_failures[0],
        "decoded-view line number",
    )
    raw_failures = []
    account_rule = (("account marker", re.compile("neutral-owner", re.IGNORECASE)),)
    _selftest_check(check_denylist({"README.md": "neutral-owner"}, account_rule, raw_failures) == 1, "denylist raw account text")
    email_failures = []
    email_rule = (
        (
            "email address",
            re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.IGNORECASE),
        ),
    )
    _selftest_check(
        check_denylist(
            {"README.md": _fixture_email("bob", "neutral-owner." + "com")},
            email_rule,
            email_failures,
        )
        == 1
        and email_failures,
        "slug-domain email remains visible to raw denylist",
    )
    userinfo_failures = []
    _selftest_check(
        check_personal_urls(
            {
                "README.md": "See "
                + _fixture_userinfo_personal_url(
                    "neutral-owner", "private", "viewer"
                )
            },
            "neutral-owner",
            None,
            userinfo_failures,
        )
        == 1
        and "personal-url: README.md:1 references personal account repository neutral-owner/private"
        in userinfo_failures[0],
        "userinfo personal URL candidate",
    )
    clean_userinfo_failures = []
    _selftest_check(
        check_personal_urls(
            {
                "README.md": "See "
                + _fixture_userinfo_personal_url(
                    "neutral-owner",
                    "private",
                    "viewer",
                    host="github." + "com.evil.invalid",
                )
            },
            "neutral-owner",
            None,
            clean_userinfo_failures,
        )
        == 0
        and not clean_userinfo_failures,
        "userinfo clean host control",
    )

    normalized_failures = []
    normalized_documents = {
        "README.md": "\n".join(
            (
                "https://github." "com:443/neutral-owner/x",
                "https://github." "com./neutral-owner/x",
                "https://gist.github." "com/neutral-owner/x",
                "https://neutral-owner.github." "io/page",
                "https://not-neutral-owner.github." "io/page",
                "https://github." "com.evil.invalid/neutral-owner/x",
            )
        )
    }
    _selftest_check(
        check_personal_urls(
            normalized_documents, "neutral-owner", None, normalized_failures
        )
        == 4
        and len(normalized_failures) == 4,
        "normalized personal URL hosts and unrelated-host negatives",
    )

    no_registry_failures = []
    count = check_personal_urls(
        {"README.md": urllib.parse.quote(_fixture_personal_url("neutral-owner", "public-archive"))},
        "neutral-owner",
        None,
        no_registry_failures,
    )
    _selftest_check(count == 1 and no_registry_failures, "registry-free personal URL any-hit")
    registry = _fixture_registry()
    allowed_failures = []
    _selftest_check(
        check_personal_urls(
            {"README.md": _fixture_personal_url("neutral-owner", "public-archive") + "."},
            "neutral-owner",
            registry,
            allowed_failures,
        ) == 1 and not allowed_failures,
        "registry personal URL allowlist",
    )
    unknown_failures = []
    _selftest_check(
        check_personal_urls(
            {"README.md": _fixture_personal_url("neutral-owner", "unlisted")},
            "neutral-owner",
            registry,
            unknown_failures,
        ) == 1 and unknown_failures,
        "unknown personal repository",
    )


def selftest_registry_checks():
    registry = _fixture_registry()
    clean = {"README.md": _fixture_module_line() + "\n"}
    failures = []
    _selftest_check(check_missing_labels(clean, registry, frozenset(), failures) == 1 and not failures, "clean label")
    missing = []
    line = _fixture_module_line(with_status=False)
    _selftest_check(check_missing_labels({"README.md": line}, registry, frozenset(), missing) == 1 and missing, "missing label")
    exempt = []
    whitelist = frozenset((("README.md", line),))
    _selftest_check(check_missing_labels({"README.md": line}, registry, whitelist, exempt) == 1 and not exempt, "exact whitelist")
    stale = []
    _selftest_check(check_whitelist_staleness({"README.md": line + " changed"}, whitelist, stale) == 1 and stale, "stale whitelist")
    svg_failures = []
    svg = {"assets/map.svg": "<svg><text>Example Module</text></svg>"}
    _selftest_check(check_svg_state_sources(svg, clean, registry, svg_failures) >= 1 and not svg_failures, "clean SVG state")
    missing_svg = []
    _selftest_check(check_svg_state_sources(svg, {"README.md": line}, registry, missing_svg) >= 1 and missing_svg, "missing SVG state")


SELFTEST_SOURCE_SCAN_DENYLIST = (
    "email-address\t\\b[A-Z0-9._%+\\-]+@[A-Z0-9.\\-]+\\.[A-Z]{2,}\\b\n"
    "github-url-ish\thttps?://(?:[A-Za-z0-9._~!$&'()*+,;=:%-]+@)?"
    "(?:gist\\.)?github\\.(?:com|io)/[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)?\n"
)


def _materialize_fixture(root, readme=SELFTEST_CLEAN_README, denylist=SELFTEST_DENYLIST):
    (root / "README.md").write_text(readme, encoding="utf-8")
    (root / DENYLIST_NAME).write_text(denylist, encoding="utf-8")


def _git(arguments, root):
    result = subprocess.run(
        ["git"] + list(arguments),
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    _selftest_check(
        result.returncode == 0,
        "git %s: %s"
        % (" ".join(arguments), result.stderr.decode("utf-8", errors="replace")),
    )


def _initialize_git_fixture(root, paths):
    _git(["init", "-q"], root)
    _git(["add", "-f", "--"] + list(paths), root)


def selftest_end_to_end():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        _materialize_fixture(root)
        (root / ".env").write_text("PUBLIC_VALUE=example\n", encoding="utf-8")
        (root / "LICENSE").write_text("Example license\n", encoding="utf-8")
        (root / "Dockerfile").write_text("FROM scratch\n", encoding="utf-8")
        (root / "notes.txt").write_text("safe notes\n", encoding="utf-8")
        (root / "extensionless").write_text("safe\n", encoding="utf-8")
        (root / "image.bin").write_bytes(b"\xff\xfe\x00")
        (root / "node_modules").mkdir()
        (root / "node_modules" / "fallback-excluded.md").write_text(
            "acme-" "secret\n", encoding="utf-8"
        )
        os.symlink("README.md", root / "readme-link")
        status, output = _capture_main(["--root", str(root), "--account-slug", "neutral-owner"])
        _selftest_check(status == 0, "clean fixture main(): %r" % output)
        _selftest_check(all(notice in output for notice in SKIP_NOTICES), "four registry skip notices")
        _selftest_check("enumeration: rglob-fallback" in output, "fallback enumeration summary")
        _selftest_check("source files scanned : 6" in output, "all UTF-8 suffixes and extensionless files scanned")
        _selftest_check("binary files skipped: 1" in output, "binary summary")
        _selftest_check("symlinks skipped: 1" in output, "fallback symlink summary")
        _selftest_check("denylist rules loaded : 2" in output, "denylist rule summary")
        missing_slug_status, missing_slug_output = _capture_main(["--root", str(root)])
        _selftest_check(
            missing_slug_status == 1
            and "gate-error: --account-slug is required for publication URL checks (fail-closed)"
            in missing_slug_output,
            "missing account slug fails closed",
        )
        whitespace_status, whitespace_output = _capture_main(
            ["--root", str(root), "--account-slug", " "]
        )
        _selftest_check(
            whitespace_status == 1 and "gate-error: --account-slug" in whitespace_output,
            "whitespace account slug fails closed",
        )
        invalid_slug_status, invalid_slug_output = _capture_main(
            ["--root", str(root), "--account-slug", "foo/bar"]
        )
        _selftest_check(
            invalid_slug_status == 1
            and "gate-error: --account-slug must match ^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37})$ (fail-closed)"
            in invalid_slug_output,
            "invalid account slug fails closed",
        )

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        _materialize_fixture(root, SELFTEST_VIOLATING_README)
        status, output = _capture_main(["--root", str(root), "--account-slug", "neutral-owner"])
        _selftest_check(status == 1 and "denylist:" in output, "violating fixture main()")

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        _materialize_fixture(root)
        copied_gate = root / "tools" / "check_publication_gate.py"
        copied_gate.parent.mkdir(parents=True)
        shutil.copyfile(Path(__file__), copied_gate)
        status, output = _capture_main(["--root", str(root), "--account-slug", "neutral-owner"])
        _selftest_check(status == 0 and "source files scanned : 2" in output, "copied gate self-scan: %r" % output)
        (root / DENYLIST_NAME).write_text(SELFTEST_SOURCE_SCAN_DENYLIST, encoding="utf-8")
        source_scan_status, source_scan_output = _capture_main(
            ["--root", str(root), "--account-slug", "neutral-owner"]
        )
        _selftest_check(
            source_scan_status == 0
            and "denylist matches     : 0" in source_scan_output,
            "copied gate source scan denylist stays green: %r" % source_scan_output,
        )

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        _materialize_fixture(root)
        registry_path = root / "registry" / "modules.json"
        registry_path.parent.mkdir(parents=True)
        registry_path.write_text(json.dumps(_fixture_registry()), encoding="utf-8")
        (root / "README.md").write_text(
            _fixture_module_line() + "\n",
            encoding="utf-8",
        )
        status, output = _capture_main(
            ["--root", str(root), "--account-slug", "neutral-owner", "--registry", "registry/modules.json"]
        )
        _selftest_check(status == 0 and "notice:" not in output, "registry-backed main(): %r" % output)

    with tempfile.TemporaryDirectory() as temporary, tempfile.TemporaryDirectory() as external:
        root = Path(temporary)
        _materialize_fixture(root)
        external_registry = Path(external) / "modules.json"
        external_registry.write_text(json.dumps(_fixture_registry()), encoding="utf-8")
        status, output = _capture_main(
            [
                "--root",
                str(root),
                "--account-slug",
                "neutral-owner",
                "--registry",
                str(external_registry),
            ]
        )
        _selftest_check(
            status == 1
            and "gate-error: --registry must resolve inside --root (fail-closed)" in output,
            "external registry rejected without an empty corpus anchor",
        )

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        _materialize_fixture(root)
        (root / ".gitignore").write_text("node_modules/\n*.txt\n", encoding="utf-8")
        (root / "node_modules").mkdir()
        (root / "node_modules" / "x.md").write_text(
            "acme-" "secret\n", encoding="utf-8"
        )
        (root / "published.txt").write_text("acme-" "secret\n", encoding="utf-8")
        _initialize_git_fixture(
            root,
            ("README.md", DENYLIST_NAME, ".gitignore", "node_modules/x.md", "published.txt"),
        )
        status, output = _capture_main(
            ["--root", str(root), "--account-slug", "neutral-owner"]
        )
        _selftest_check(
            status == 1
            and "enumeration: git" in output
            and "denylist: node_modules/x.md:1" in output
            and "denylist: published.txt:1" in output,
            "git mode scans committed formerly-excluded and .txt files: %r" % output,
        )

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        _materialize_fixture(root)
        (root / "binary.dat").write_bytes(b"\x80\x81\x82")
        _initialize_git_fixture(root, ("README.md", DENYLIST_NAME, "binary.dat"))
        status, output = _capture_main(
            ["--root", str(root), "--account-slug", "neutral-owner"]
        )
        _selftest_check(
            status == 0
            and "enumeration: git" in output
            and "binary files skipped: 1" in output,
            "git binary is skipped once and counted: %r" % output,
        )

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        _materialize_fixture(root)
        os.symlink("https://github." "com/neutral-owner/private", root / "published-link")
        _initialize_git_fixture(root, ("README.md", DENYLIST_NAME, "published-link"))
        status, output = _capture_main(
            ["--root", str(root), "--account-slug", "neutral-owner"]
        )
        _selftest_check(
            status == 1
            and "personal-url: published-link:1" in output
            and "symlinks skipped:" not in output,
            "git symlink readlink text is scanned: %r" % output,
        )

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        _materialize_fixture(
            root,
            "Contact bob@" "neutral-owner.com\n",
            "email-address\t\\b[A-Z0-9._%+\\-]+@[A-Z0-9.\\-]+\\.[A-Z]{2,}\\b\n",
        )
        status, output = _capture_main(
            ["--root", str(root), "--account-slug", "neutral-owner"]
        )
        _selftest_check(
            status == 1 and "denylist: README.md:1 contains email-address" in output,
            "main-level slug-domain email denylist: %r" % output,
        )

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        _materialize_fixture(
            root, "See https://gist.github." "com/neutral-owner/example\n"
        )
        status, output = _capture_main(
            ["--root", str(root), "--account-slug", "neutral-owner"]
        )
        _selftest_check(
            status == 1 and "personal-url: README.md:1" in output,
            "main-level personal URL without registry: %r" % output,
        )

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        _materialize_fixture(root)
        (root / "README.md").unlink()
        (root / "safe.txt").write_text("safe\n", encoding="utf-8")
        status, output = _capture_main(
            ["--root", str(root), "--account-slug", "neutral-owner"]
        )
        _selftest_check(
            status == 1 and "corpus-floor: README.md was not among scanned documents" in output,
            "main-level corpus floor: %r" % output,
        )

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        _materialize_fixture(root)
        (root / ".git").mkdir()
        status, output = _capture_main(
            ["--root", str(root), "--account-slug", "neutral-owner"]
        )
        _selftest_check(
            status == 1
            and "enumeration: git" in output
            and "gate-error: git enumeration failed" in output
            and "denylist rules loaded : 2" in output,
            "broken .git fails closed without fallback: %r" % output,
        )

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / "policies").mkdir()
        explicit = root / "policies" / "secret-rules.txt"
        explicit.write_text(SELFTEST_DENYLIST, encoding="utf-8")
        (root / "README.md").write_text(SELFTEST_CLEAN_README, encoding="utf-8")
        status, output = _capture_main(
            [
                "--root",
                str(root),
                "--account-slug",
                "neutral-owner",
                "--denylist",
                "policies/secret-rules.txt",
            ]
        )
        _selftest_check(
            status == 0
            and "source files scanned : 1" in output
            and "denylist rules loaded : 2" in output,
            "explicit in-root denylist is path-excluded: %r" % output,
        )

    if not os.environ.get("PUBLICATION_GATE_SELFTEST_COPY_PROBE"):
        with tempfile.TemporaryDirectory() as temporary:
            copied_gate = Path(temporary) / "check_publication_gate.py"
            shutil.copyfile(Path(__file__), copied_gate)
            environment = dict(os.environ)
            environment["PUBLICATION_GATE_SELFTEST_COPY_PROBE"] = "1"
            result = subprocess.run(
                [sys.executable, "-B", str(copied_gate), "--selftest"],
                cwd=temporary,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=environment,
                check=False,
                text=True,
            )
            _selftest_check(
                result.returncode == 0 and "PASS (publication gate selftest" in result.stdout,
                "copied-single-file selftest: %r" % result.stdout,
            )


def run_selftests():
    global SELFTEST_ASSERTIONS
    SELFTEST_ASSERTIONS = 0
    tests = (selftest_policy_parsers, selftest_scanners, selftest_registry_checks, selftest_end_to_end)
    for test in tests:
        test()
        print("ok: %s" % test.__name__)
    print("PASS (publication gate selftest; assertions: %d)" % SELFTEST_ASSERTIONS)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true", help="run embedded gate fixtures")
    parser.add_argument("--root", type=Path, default=Path("."), help="repository checkout to inspect (default: .)")
    parser.add_argument("--account-slug", default=None, help="personal account slug (required for normal runs)")
    parser.add_argument("--registry", type=Path, default=None, help="optional publication registry JSON file")
    parser.add_argument(
        "--denylist",
        type=Path,
        default=None,
        help="denylist policy file (default: <root>/.publication-denylist)",
    )
    args = parser.parse_args(argv)
    if args.selftest:
        return run_selftests()
    return run_gate(args.root, args.account_slug, args.registry, args.denylist)


if __name__ == "__main__":
    sys.exit(main())
