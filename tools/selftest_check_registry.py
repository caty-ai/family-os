#!/usr/bin/env python3
"""Offline self-tests for the registry checks."""

from __future__ import annotations

import http.client
import pathlib
import tempfile
import urllib.error
from typing import Optional
from unittest import mock

from check_registry import (
    check_aliases,
    check_ci_existence,
    check_for_agents_tour,
    check_orphan,
    check_pin_freshness,
    check_reality,
    check_retired,
    check_schema,
    check_support,
    fetch_newest_tag,
    fetch_org_repos,
    github_ci_workflow_exists,
    github_is_public,
    NoRedirectHandler,
)


SUPPORT_READMES = ("README.md", "README.ja.md", "README.zh.md", "README.th.md")


def _support_document(in_use: str, extra_rows: str = "") -> str:
    return (
        "# Family OS\n\n"
        '<a id="environments"></a>\n\n'
        "## What you need\n\n"
        "| Aspect | Support |\n"
        "| --- | --- |\n"
        "| Agent environments in real use | %s |\n"
        "%s"
        "\n---\n\n"
        '<a id="later"></a>\n' % (in_use, extra_rows)
    )


def _run_support_check(overrides=None):
    in_use = (
        "✅ Claude Code ／ ✅ Hermes Agent ／ ✅ OpenClaw ／ "
        "✅ Kimi Code ／ ✅ Codex"
    )
    documents = {
        filename: _support_document(in_use) for filename in SUPPORT_READMES
    }
    documents.update(overrides or {})

    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        for filename, document in documents.items():
            (root / filename).write_text(document, encoding="utf-8")
        failures: list = []
        checked = check_support(root, failures)
    return checked, failures


def check_support_accepts_four_consistent_readmes() -> None:
    checked, failures = _run_support_check()
    assert checked == 4, checked
    assert failures == [], failures


def check_support_flags_environment_in_planned_row() -> None:
    in_use = (
        "✅ Claude Code ／ ✅ Hermes Agent ／ ✅ OpenClaw ／ "
        "✅ Kimi Code ／ ✅ Codex"
    )
    document = _support_document(
        in_use,
        "| Agent environments planned for verification | ⚠️ Kimi Code |\n",
    )
    checked, failures = _run_support_check({"README.th.md": document})
    assert checked == 4, checked
    assert len(failures) == 1, failures
    assert failures[0].startswith("support: README.th.md:"), failures
    assert "planned for verification" in failures[0], failures


def check_support_flags_missing_in_use_environment() -> None:
    document = _support_document(
        "✅ Claude Code ／ ✅ Hermes Agent ／ ✅ OpenClaw ／ ✅ Kimi Code"
    )
    checked, failures = _run_support_check({"README.zh.md": document})
    assert checked == 4, checked
    assert len(failures) == 1, failures
    assert failures[0].startswith("support: README.zh.md:"), failures
    assert "✅ Codex" in failures[0], failures


def check_support_missing_anchor_fails_closed() -> None:
    document = _support_document(
        "✅ Claude Code ／ ✅ Hermes Agent ／ ✅ OpenClaw ／ "
        "✅ Kimi Code ／ ✅ Codex"
    ).replace('<a id="environments"></a>\n\n', "", 1)
    checked, failures = _run_support_check({"README.ja.md": document})
    assert checked == 3, checked
    assert len(failures) == 1, failures
    assert failures[0].startswith("support: README.ja.md:"), failures
    assert "missing environments anchor" in failures[0], failures


def check_support_flags_warning_mark_in_in_use_row() -> None:
    document = _support_document(
        "✅ Claude Code ／ ✅ Hermes Agent ／ ✅ OpenClaw ／ "
        "✅ Kimi Code ／ ⚠️ Codex"
    )
    checked, failures = _run_support_check({"README.md": document})
    assert checked == 4, checked
    assert len(failures) == 1, failures
    assert failures[0].startswith("support: README.md:"), failures
    assert "with no ⚠️" in failures[0], failures


def _tour_registry() -> dict:
    return {
        "modules": [
            {"repo": "example-org/alpha", "status": "published"},
            {"repo": "example-org/beta", "status": "published"},
            {"repo": "example-org/preparing", "status": "preparing"},
        ]
    }


def _tour_document(repos: list) -> str:
    rows = "".join(
        "| [%s](https://github.com/%s) (published, MIT) | role | verify |\n"
        % (repo.split("/", 1)[1], repo)
        for repo in repos
    )
    return (
        "## 4. Before the tour\n\n"
        "| [outside](https://github.com/example-org/outside) | ignored |\n\n"
        "## 5. Repository tour table (all published modules)\n\n"
        "A prose URL https://github.com/example-org/prose is ignored.\n\n"
        "| repository | role | what to verify |\n"
        "|---|---|---|\n"
        "%s\n"
        "## 6. After the tour\n\n"
        "| [later](https://github.com/example-org/later) | ignored |\n" % rows
    )


def _run_tour_check(document: str):
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "FOR-AGENTS.md").write_text(document, encoding="utf-8")
        failures: list = []
        rows = check_for_agents_tour(_tour_registry(), root, failures)
    return rows, failures


def check_for_agents_tour_matches_published_set() -> None:
    rows, failures = _run_tour_check(
        _tour_document(["example-org/alpha", "example-org/beta"])
    )
    assert rows == 2, rows
    assert failures == [], failures


def check_for_agents_tour_flags_missing_published_module() -> None:
    rows, failures = _run_tour_check(_tour_document(["example-org/alpha"]))
    assert rows == 1, rows
    assert len(failures) == 1, failures
    assert failures[0].startswith("tour: example-org/beta is published"), failures


def check_for_agents_tour_flags_non_published_row() -> None:
    rows, failures = _run_tour_check(
        _tour_document(
            ["example-org/alpha", "example-org/beta", "example-org/preparing"]
        )
    )
    assert rows == 3, rows
    assert len(failures) == 1, failures
    assert "lists example-org/preparing" in failures[0], failures


def check_for_agents_tour_flags_indented_non_published_row() -> None:
    document = _tour_document(["example-org/alpha", "example-org/beta"]).replace(
        "\n## 6. After the tour",
        "\n   | [ghost](https://github.com/example-org/ghost) | role | verify |\n"
        "\n## 6. After the tour",
        1,
    )
    rows, failures = _run_tour_check(document)
    assert rows == 3, rows
    assert len(failures) == 1, failures
    assert failures[0].startswith("tour:") and "lists example-org/ghost" in failures[0]


def check_for_agents_tour_missing_section_fails_closed() -> None:
    document = (
        "## 4. Before the missing tour\n\n"
        "| [alpha](https://github.com/example-org/alpha) | ignored |\n\n"
        "## 6. After the missing tour\n"
    )
    rows, failures = _run_tour_check(document)
    assert rows == 0, rows
    assert len(failures) == 1, failures
    assert failures[0].startswith("tour:") and "section not found" in failures[0]


def check_for_agents_tour_empty_section_fails_closed() -> None:
    rows, failures = _run_tour_check(_tour_document([]))
    assert rows == 0, rows
    assert len(failures) == 1, failures
    assert failures[0].startswith("tour:") and "zero parsed tour rows" in failures[0]


def check_for_agents_tour_allows_approved_exemption() -> None:
    with mock.patch(
        "check_registry.FOR_AGENTS_TOUR_EXEMPT", frozenset({"example-org/beta"})
    ):
        rows, failures = _run_tour_check(_tour_document(["example-org/alpha"]))
    assert rows == 1, rows
    assert failures == [], failures


class Response:
    def __init__(self, status: int, read_result=b"[]") -> None:
        self.status = status
        self.read_result = read_result
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def read(self):
        if isinstance(self.read_result, BaseException):
            raise self.read_result
        return self.read_result


class Opener:
    def __init__(self, result) -> None:
        self.result = result

    def open(self, request, timeout):
        if isinstance(self.result, BaseException):
            raise self.result
        return self.result


def http_error(code: int, location: Optional[str] = None) -> urllib.error.HTTPError:
    headers = {"Location": location} if location else {}
    return urllib.error.HTTPError(
        "https://github.com/caty-ai/example", code, "test", headers, None
    )


def check_status_contract() -> None:
    cases = [
        (Response(200), True),
        (
            http_error(301, "https://github.com/caty-ai/moved"),
            ("moved", "https://github.com/caty-ai/moved"),
        ),
        (
            http_error(303, "https://github.com/caty-ai/moved"),
            ("moved", "https://github.com/caty-ai/moved"),
        ),
        (
            http_error(399, "https://github.com/caty-ai/moved"),
            ("moved", "https://github.com/caty-ai/moved"),
        ),
        (http_error(404), False),
        (http_error(403), None),
        (http_error(429), None),
        (http_error(500), None),
        (http_error(599), None),
        (http_error(401), ("unexpected", 401)),
        (http_error(405), ("unexpected", 405)),
        (http_error(410), False),
        (http_error(451), False),
    ]
    for result, expected in cases:
        with mock.patch(
            "check_registry.urllib.request.build_opener", return_value=Opener(result)
        ):
            actual = github_is_public("caty-ai/example")
        assert actual == expected, (result, expected, actual)


def check_fetch_org_repos_read_faults_degrade() -> None:
    faults = [
        http.client.IncompleteRead(b""),
        ConnectionResetError("connection reset during response read"),
    ]
    for fault in faults:
        with mock.patch(
            "check_registry.urllib.request.build_opener",
            return_value=Opener(Response(200, fault)),
        ):
            actual = fetch_org_repos("caty-ai")
        assert actual is None, (fault, actual)


def check_unexpected_statuses_are_recorded_and_later_modules_continue() -> None:
    statuses = [303, 401, 405]
    registry = {
        "modules": [
            {"repo": "caty-ai/status-%d" % status, "status": "published"}
            for status in statuses
        ]
        + [{"repo": "caty-ai/after", "status": "published"}]
    }
    results = [
        ("moved", "https://github.com/caty-ai/renamed"),
        ("unexpected", 401),
        ("unexpected", 405),
        True,
    ]
    failures = []
    notes = []
    with mock.patch("check_registry.github_is_public", side_effect=results) as probe:
        skipped = check_reality(registry, failures, notes)

    assert probe.call_count == len(registry["modules"]), probe.call_count
    assert probe.call_args_list[-1] == mock.call("caty-ai/after")
    assert skipped == 2, skipped
    assert len(failures) == 1 and failures[0].startswith("moved: caty-ai/status-303")
    for status in statuses[1:]:
        assert any(
            note.startswith("degraded: caty-ai/status-%d:" % status)
            and "unexpected HTTP status %d" % status in note
            for note in notes
        ), (status, notes)


def check_gone_statuses_hard_fail_published_modules() -> None:
    registry = {
        "modules": [
            {"repo": "caty-ai/gone", "status": "published"},
            {"repo": "caty-ai/legal", "status": "published"},
        ]
    }
    failures = []
    notes = []
    with mock.patch("check_registry.github_is_public", side_effect=[False, False]):
        skipped = check_reality(registry, failures, notes)

    assert skipped == 0, skipped
    assert len(failures) == 2, failures
    assert all("PRIVATE/absent" in failure for failure in failures), failures


def check_require_reality_escalates_unexpected_status() -> None:
    registry = {"modules": [{"repo": "caty-ai/unexpected", "status": "published"}]}
    failures = []
    notes = []
    with mock.patch(
        "check_registry.github_is_public", return_value=("unexpected", 401)
    ):
        skipped = check_reality(registry, failures, notes, require_reality=True)

    assert skipped == 1, skipped
    assert len(failures) == 1, failures
    assert "--require-reality rejects this degraded run" in failures[0], failures
    assert any("unexpected HTTP status 401" in note for note in notes), notes


def _orphan_registry() -> dict:
    return {
        "map_repo": "caty-ai/family-os",
        "modules": [
            {"repo": "caty-ai/alpha"},
            {"repo": "caty-ai/beta"},
        ],
        "org_profile": {"repo": "caty-ai/.github"},
    }


def _adjacent_localized(en: str) -> dict:
    return {
        "en": en,
        "ja": "テスト文言",
        "zh": "测试文案",
        "th": "ข้อความทดสอบ",
    }


def _adjacent_text() -> dict:
    return {
        "heading": _adjacent_localized("Connecting to the family"),
        "intro": _adjacent_localized(
            "These are not Family OS modules. They carry an existing family agent elsewhere."
        ),
        "table_module": _adjacent_localized("Module"),
        "table_what": _adjacent_localized("What it does"),
        "table_relation": _adjacent_localized("Relation to the family"),
    }


def _adjacent_registry() -> dict:
    return {
        "languages": ["en", "ja", "zh", "th"],
        "modules": [
            {
                "id": "alpha",
                "repo": "example-org/alpha",
                "maturity": "product",
            }
        ],
        "adjacent": [
            {
                "id": "meetmate",
                "name": "Meetmate",
                "repo": "example-org/meetmate",
                "license": "MIT",
                "tagline": _adjacent_localized("Meeting presence"),
                "relation": _adjacent_localized("Carries an existing family agent"),
            }
        ],
        "adjacent_text": _adjacent_text(),
    }


def check_orphan_all_repos_accounted_for() -> None:
    registry = _orphan_registry()
    org_repos = [
        "caty-ai/family-os",
        "caty-ai/alpha",
        "caty-ai/beta",
        "caty-ai/.github",
    ]
    failures = []
    notes = []
    with mock.patch(
        "check_registry.fetch_org_repos", return_value=org_repos
    ) as probe:
        skipped = check_orphan(registry, failures, notes)

    assert probe.call_args == mock.call("caty-ai"), probe.call_args
    assert skipped == 0, skipped
    assert failures == [], failures


def check_orphan_accounts_for_retired_repos_case_insensitively() -> None:
    registry = _orphan_registry()
    registry["retired_repos"] = [{"repo": "caty-ai/retired-example"}]
    org_repos = [
        "Caty-AI/Family-OS",
        "Caty-AI/Alpha",
        "Caty-AI/Beta",
        "Caty-AI/.GitHub",
        "Caty-AI/Retired-Example",
    ]
    failures = []
    notes = []
    with mock.patch("check_registry.fetch_org_repos", return_value=org_repos):
        skipped = check_orphan(registry, failures, notes)

    assert skipped == 0, skipped
    assert failures == [], failures


def check_orphan_accounts_for_adjacent_repos() -> None:
    registry = _orphan_registry()
    registry["adjacent"] = [{"repo": "caty-ai/meetmate"}]
    org_repos = [
        "Caty-AI/Family-OS",
        "Caty-AI/Alpha",
        "Caty-AI/Beta",
        "Caty-AI/.GitHub",
        "Caty-AI/MeetMate",
    ]
    failures = []
    notes = []
    with mock.patch("check_registry.fetch_org_repos", return_value=org_repos):
        skipped = check_orphan(registry, failures, notes)

    assert skipped == 0, skipped
    assert failures == [], failures


def check_orphan_flags_unaccounted_public_repo() -> None:
    registry = _orphan_registry()
    org_repos = [
        "caty-ai/family-os",
        "caty-ai/alpha",
        "caty-ai/beta",
        "caty-ai/.github",
        "Caty-AI/Mystery-Repo",
    ]
    failures = []
    notes = []
    with mock.patch("check_registry.fetch_org_repos", return_value=org_repos):
        skipped = check_orphan(registry, failures, notes)

    assert skipped == 0, skipped
    assert len(failures) == 1, failures
    assert failures[0].startswith("orphan: Caty-AI/Mystery-Repo"), failures


def check_orphan_fetch_failure_degrades_instead_of_failing() -> None:
    registry = _orphan_registry()
    failures = []
    notes = []
    with mock.patch("check_registry.fetch_org_repos", return_value=None):
        skipped = check_orphan(registry, failures, notes)

    assert skipped == 1, skipped
    assert failures == [], failures
    assert any(note.startswith("org:caty-ai:") for note in notes), notes


def check_orphan_require_reality_escalates_fetch_failure() -> None:
    registry = _orphan_registry()
    failures = []
    notes = []
    with mock.patch("check_registry.fetch_org_repos", return_value=None):
        skipped = check_orphan(registry, failures, notes, require_reality=True)

    assert skipped == 1, skipped
    assert len(failures) == 1, failures
    assert "--require-reality rejects this degraded run" in failures[0], failures


def check_retired_scans_beyond_markdown_but_exempts_the_registry() -> None:
    """Regression proof for the family-links.yml:111 blind spot: red before
    this fix (retired scan limited to *.md), green after.

    Uses a synthetic retired repo name (not a real registry entry) so this
    fixture's own on-disk source text never collides with the retired-scan
    regex it is exercising."""
    retired_owner = "example-org"
    retired_name = "retired-" + "example-repo"
    retired_repo = "%s/%s" % (retired_owner, retired_name)
    registry = {
        "retired_repos": [
            {
                "repo": retired_repo,
                "superseded_by": "example-org/current-example-repo",
                "reason": "republished under example-org as a fresh repository, "
                "so GitHub does not redirect",
            }
        ]
    }
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / ".github" / "workflows").mkdir(parents=True)
        (root / "docs").mkdir()
        (root / "registry").mkdir()

        yml_path = root / ".github" / "workflows" / "family-links.yml"
        yml_path.write_text(
            "args: >-\n"
            "  --exclude 'https://github.com/%s'\n" % retired_repo,
            encoding="utf-8",
        )
        md_path = root / "docs" / "note.md"
        md_path.write_text(
            "See https://github.com/%s for history.\n" % retired_repo,
            encoding="utf-8",
        )
        registry_path = root / "registry" / "modules.json"
        registry_path.write_text(
            '{"retired_repos": [{"repo": "%s"}]}\n' % retired_repo,
            encoding="utf-8",
        )

        failures: list = []
        check_retired(registry, root, failures)

    assert len(failures) == 2, failures
    assert any("family-links.yml" in failure for failure in failures), failures
    assert any("note.md" in failure for failure in failures), failures
    assert not any("modules.json" in failure for failure in failures), failures


def check_retired_reports_regex_escaped_github_spelling() -> None:
    retired_owner = "example-org"
    retired_name = "retired-" + "escaped-example"
    retired_repo = "%s/%s" % (retired_owner, retired_name)
    registry = {
        "retired_repos": [
            {
                "repo": retired_repo,
                "superseded_by": "example-org/current-escaped-example",
                "reason": "synthetic self-test fixture",
            }
        ]
    }
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        yml_path = root / "family-links.yml"
        yml_path.write_text(
            "args: >-\n"
            "  --exclude 'github\\.com/%s'\n" % retired_repo,
            encoding="utf-8",
        )

        failures: list = []
        check_retired(registry, root, failures)

    assert len(failures) == 1, failures
    assert failures[0].startswith("retired: family-links.yml:2 "), failures


def check_alias_flags_yaml_reference_but_exempts_registry() -> None:
    alias = "example-org/former-module"
    canonical = "example-org/current-module"
    registry = {
        "modules": [{"repo": canonical, "aliases": [alias]}],
    }
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "registry").mkdir()
        (root / "registry" / "modules.json").write_text(
            '{"aliases": ["%s"]}\n' % alias, encoding="utf-8"
        )
        (root / "links.yml").write_text(
            "source: https://github.com/%s\n" % alias, encoding="utf-8"
        )
        failures = []
        checked = check_aliases(registry, root, failures)

    assert checked == 1, checked
    assert failures == [
        "alias: links.yml:1 references %s, an alias of %s — use the canonical path"
        % (alias, canonical)
    ], failures


def check_alias_no_aliases_produces_no_scan_output() -> None:
    registry = {"modules": [{"repo": "example-org/current-module"}]}
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        (root / "links.yml").write_text(
            "source: https://github.com/example-org/former-module\n",
            encoding="utf-8",
        )
        failures = []
        checked = check_aliases(registry, root, failures)

    assert checked == 0, checked
    assert failures == [], failures


def _pin_registry(pin="v0.2.0", pin_reason=None) -> dict:
    dependency = {"repo": "example-org/dependency", "pin": pin}
    if pin_reason is not None:
        dependency["pin_reason"] = pin_reason
    return {
        "modules": [
            {"id": "example-module", "depends_on": [dependency]},
        ]
    }


def check_pin_freshness_accepts_matching_newest_tag() -> None:
    failures = []
    notes = []
    with mock.patch("check_registry.fetch_newest_tag", return_value="v0.2.0"):
        skipped = check_pin_freshness(_pin_registry(), failures, notes)

    assert skipped == 0, skipped
    assert failures == [], failures
    assert notes == [], notes


def check_pin_freshness_accepts_bare_tag_from_message_bearing_entry() -> None:
    payload = (
        b'<feed xmlns="http://www.w3.org/2005/Atom">'
        b"<entry>"
        b"<title>v0.9.0 \xe2\x80\x94 some message</title>"
        b"<id>tag:github.com,2008:Repository/1/v0.9.0</id>"
        b"</entry></feed>"
    )
    failures = []
    notes = []
    with mock.patch(
        "check_registry.urllib.request.build_opener",
        return_value=Opener(Response(200, payload)),
    ):
        skipped = check_pin_freshness(_pin_registry(pin="v0.9.0"), failures, notes)

    assert skipped == 0, skipped
    assert failures == [], failures
    assert notes == [], notes


def check_pin_freshness_flags_stale_pin_once() -> None:
    failures = []
    notes = []
    with mock.patch("check_registry.fetch_newest_tag", return_value="v0.3.0"):
        skipped = check_pin_freshness(_pin_registry(), failures, notes)

    assert skipped == 0, skipped
    assert failures == [
        "pin-freshness: example-module pins example-org/dependency@v0.2.0 but "
        "the newest tag is v0.3.0. Update the pin or record pin_reason in "
        "registry/modules.json."
    ], failures
    assert notes == [], notes


def check_pin_freshness_flags_stale_pin_with_bare_newest_tag() -> None:
    payload = (
        b'<feed xmlns="http://www.w3.org/2005/Atom">'
        b"<entry>"
        b"<title>v0.9.0 \xe2\x80\x94 some message</title>"
        b"<id>tag:github.com,2008:Repository/1/v0.9.0</id>"
        b"</entry></feed>"
    )
    failures = []
    notes = []
    with mock.patch(
        "check_registry.urllib.request.build_opener",
        return_value=Opener(Response(200, payload)),
    ):
        skipped = check_pin_freshness(_pin_registry(pin="v0.2.0"), failures, notes)

    assert skipped == 0, skipped
    assert failures == [
        "pin-freshness: example-module pins example-org/dependency@v0.2.0 but "
        "the newest tag is v0.9.0. Update the pin or record pin_reason in "
        "registry/modules.json."
    ], failures
    assert notes == [], notes


def check_pin_freshness_honours_pin_reason() -> None:
    failures = []
    notes = []
    with mock.patch("check_registry.fetch_newest_tag", return_value="v0.3.0"):
        skipped = check_pin_freshness(
            _pin_registry(pin_reason="tracked in example-module#14"), failures, notes
        )

    assert skipped == 0, skipped
    assert failures == [], failures
    assert len(notes) == 1 and "tracked in example-module#14" in notes[0], notes


def check_pin_freshness_fetch_failure_degrades_and_escalates() -> None:
    failures = []
    notes = []
    with mock.patch("check_registry.fetch_newest_tag", return_value=None):
        skipped = check_pin_freshness(_pin_registry(), failures, notes)

    assert skipped == 1, skipped
    assert failures == [], failures
    assert any(note.startswith("pin:example-org/dependency:") for note in notes), notes

    failures = []
    notes = []
    with mock.patch("check_registry.fetch_newest_tag", return_value=None):
        skipped = check_pin_freshness(
            _pin_registry(), failures, notes, require_reality=True
        )

    assert skipped == 1, skipped
    assert len(failures) == 1, failures
    assert "--require-reality rejects this degraded run" in failures[0], failures


def check_fetch_newest_tag_read_faults_degrade() -> None:
    faults = [
        http.client.IncompleteRead(b""),
        ConnectionResetError("connection reset during response read"),
    ]
    for fault in faults:
        with mock.patch(
            "check_registry.urllib.request.build_opener",
            return_value=Opener(Response(200, fault)),
        ):
            actual = fetch_newest_tag("example-org/dependency")
        assert actual is None, (fault, actual)


def check_fetch_newest_tag_unsupported_encoding_degrades() -> None:
    payload = b'<?xml version="1.0" encoding="BOGUS"?><feed/>'
    with mock.patch(
        "check_registry.urllib.request.build_opener",
        return_value=Opener(Response(200, payload)),
    ):
        actual = fetch_newest_tag("example-org/dependency")
    assert actual is None, actual


def check_fetch_newest_tag_prefers_entry_id_over_title_message() -> None:
    payload = (
        b'<feed xmlns="http://www.w3.org/2005/Atom">'
        b"<entry>"
        b"<title>v0.9.0 \xe2\x80\x94 some message</title>"
        b"<id>tag:github.com,2008:Repository/1/v0.9.0</id>"
        b"</entry>"
        b'</feed>'
    )
    with mock.patch(
        "check_registry.urllib.request.build_opener",
        return_value=Opener(Response(200, payload)),
    ):
        actual = fetch_newest_tag("example-org/dependency")
    assert actual == "v0.9.0", actual


def check_fetch_newest_tag_falls_back_to_first_title_token_when_id_missing() -> None:
    payload = (
        b'<feed xmlns="http://www.w3.org/2005/Atom">'
        b"<entry><title>v0.9.0 \xe2\x80\x94 some message</title></entry>"
        b'</feed>'
    )
    with mock.patch(
        "check_registry.urllib.request.build_opener",
        return_value=Opener(Response(200, payload)),
    ):
        actual = fetch_newest_tag("example-org/dependency")
    assert actual == "v0.9.0", actual


def _ci_registry() -> dict:
    return {
        "modules": [
            {
                "id": "example-module",
                "repo": "example-org/current-module",
                "ci": {"required": True, "workflow": "test-lint.yml"},
            }
        ]
    }


def check_ci_existence_accepts_200_and_flags_404() -> None:
    failures = []
    notes = []
    with mock.patch("check_registry.github_ci_workflow_exists", return_value=True):
        skipped = check_ci_existence(_ci_registry(), failures, notes)
    assert skipped == 0, skipped
    assert failures == [], failures

    failures = []
    notes = []
    with mock.patch("check_registry.github_ci_workflow_exists", return_value=False):
        skipped = check_ci_existence(_ci_registry(), failures, notes)
    assert skipped == 0, skipped
    assert failures == [
        "ci-existence: example-module declares ci.required but test-lint.yml "
        "does not exist on example-org/current-module's default branch."
    ], failures


def check_ci_existence_network_error_degrades() -> None:
    failures = []
    notes = []
    with mock.patch("check_registry.github_ci_workflow_exists", return_value=None):
        skipped = check_ci_existence(_ci_registry(), failures, notes)

    assert skipped == 1, skipped
    assert failures == [], failures
    assert any(note.startswith("ci:example-org/current-module:") for note in notes), notes


def check_ci_existence_require_reality_escalates_network_error() -> None:
    failures = []
    notes = []
    with mock.patch("check_registry.github_ci_workflow_exists", return_value=None):
        skipped = check_ci_existence(
            _ci_registry(), failures, notes, require_reality=True
        )

    assert skipped == 1, skipped
    assert len(failures) == 1, failures
    assert "--require-reality rejects this degraded run" in failures[0], failures
    assert any(note.startswith("ci:example-org/current-module:") for note in notes), notes


def check_ci_workflow_helper_treats_404_as_absent() -> None:
    with mock.patch(
        "check_registry.urllib.request.build_opener", return_value=Opener(Response(404))
    ):
        actual = github_ci_workflow_exists("example-org/current-module", "test.yml")
    assert actual is False, actual


def check_ci_workflow_helper_does_not_follow_redirects() -> None:
    with mock.patch(
        "check_registry.urllib.request.build_opener",
        return_value=Opener(http_error(302, "https://example.invalid/redirect")),
    ) as build_opener:
        actual = github_ci_workflow_exists("example-org/current-module", "test.yml")

    assert actual is None, actual
    assert isinstance(build_opener.call_args.args[0], NoRedirectHandler)


def check_ci_workflow_helper_network_faults_degrade() -> None:
    faults = [
        http.client.IncompleteRead(b""),
        ConnectionResetError("connection reset during response read"),
    ]
    for fault in faults:
        with mock.patch(
            "check_registry.urllib.request.build_opener", return_value=Opener(fault)
        ):
            actual = github_ci_workflow_exists("example-org/current-module", "test.yml")
        assert actual is None, (fault, actual)


def check_schema_rejects_bad_contract_fields() -> None:
    registry = {
        "modules": [
            {
                "id": "missing-maturity",
            },
            {
                "id": "bad-maturity",
                "maturity": "prototype",
            },
            {
                "id": "bad-dependency",
                "maturity": "product",
                "depends_on": [
                    {
                        "repo": "example-org/dependency",
                        "pin": "v0.2.0",
                        "unexpected": True,
                    }
                ],
            },
            {
                "id": "bad-ci",
                "maturity": "product",
                "ci": {
                    "required": True,
                    "workflow": "test-lint.yml",
                    "unexpected": True,
                },
            },
        ]
    }
    failures = []
    checked = check_schema(registry, failures)

    assert checked == 4, checked
    assert failures == [
        "schema: missing-maturity: maturity must be 'product', 'public preview', or 'reference'",
        "schema: bad-maturity: maturity must be 'product', 'public preview', or 'reference'",
        "schema: bad-dependency: depends_on must be a list of {repo, pin} entries",
        "schema: bad-ci: ci must be {required: true, workflow: '<file>.yml'}",
    ], failures


def check_schema_accepts_public_preview_maturity() -> None:
    registry = {
        "modules": [
            {
                "id": "preview-module",
                "maturity": "public preview",
            }
        ]
    }
    failures = []
    checked = check_schema(registry, failures)

    assert checked == 1, checked
    assert failures == [], failures


def check_schema_accepts_missing_adjacent_key() -> None:
    registry = _adjacent_registry()
    registry.pop("adjacent")
    registry.pop("adjacent_text")
    failures = []
    checked = check_schema(registry, failures)

    assert checked == 1, checked
    assert failures == [], failures


def check_schema_rejects_bad_adjacent_entries() -> None:
    registry = _adjacent_registry()
    registry["adjacent"] = [
        {
            "id": "missing-tagline-lang",
            "name": "Missing tagline lang",
            "repo": "example-org/missing-tagline-lang",
            "license": "MIT",
            "tagline": {
                "en": "ok",
                "ja": "ok",
                "zh": "ok",
            },
            "relation": _adjacent_localized("Relation"),
        },
        {
            "id": "missing-repo",
            "name": "Missing repo",
            "license": "MIT",
            "tagline": _adjacent_localized("Tagline"),
            "relation": _adjacent_localized("Relation"),
        },
        {
            "id": "bad-slug",
            "name": "Bad slug",
            "repo": "not a slug",
            "license": "MIT",
            "tagline": _adjacent_localized("Tagline"),
            "relation": _adjacent_localized("Relation"),
        },
        {
            "id": "unknown-key",
            "name": "Unknown key",
            "repo": "example-org/unknown-key",
            "license": "MIT",
            "tagline": _adjacent_localized("Tagline"),
            "relation": _adjacent_localized("Relation"),
            "unexpected": True,
        },
        {
            "id": "same-as-module",
            "name": "Same as module",
            "repo": "example-org/alpha",
            "license": "MIT",
            "tagline": _adjacent_localized("Tagline"),
            "relation": _adjacent_localized("Relation"),
        },
    ]
    failures = []
    checked = check_schema(registry, failures)

    assert checked == 1, checked
    assert len(failures) == 5, failures
    assert "tagline.th must be a non-empty string" in failures[0], failures
    assert any("missing-repo" in failure and "repo must be a non-empty owner/name string" in failure for failure in failures), failures
    assert any("bad-slug" in failure and "repo must be a non-empty owner/name string" in failure for failure in failures), failures
    assert any("unknown-key" in failure and "unknown keys: unexpected" in failure for failure in failures), failures
    assert any(
        "same-as-module" in failure
        and "may not appear in both modules[] and adjacent[]" in failure
        for failure in failures
    ), failures


def check_schema_rejects_missing_adjacent_text_when_adjacent_exists() -> None:
    registry = _adjacent_registry()
    registry.pop("adjacent_text")
    failures = []
    checked = check_schema(registry, failures)

    assert checked == 1, checked
    assert failures == ["schema: adjacent_text must be an object"], failures


def check_schema_rejects_present_null_or_non_list_adjacent() -> None:
    for bad_value in (None, "not-a-list", {"repo": "example-org/meetmate"}):
        registry = _adjacent_registry()
        registry["adjacent"] = bad_value
        failures = []
        checked = check_schema(registry, failures)

        assert checked == 1, checked
        assert failures == ["schema: adjacent must be a list"], (bad_value, failures)


if __name__ == "__main__":
    check_support_accepts_four_consistent_readmes()
    check_support_flags_environment_in_planned_row()
    check_support_flags_missing_in_use_environment()
    check_support_missing_anchor_fails_closed()
    check_support_flags_warning_mark_in_in_use_row()
    check_for_agents_tour_matches_published_set()
    check_for_agents_tour_flags_missing_published_module()
    check_for_agents_tour_flags_non_published_row()
    check_for_agents_tour_flags_indented_non_published_row()
    check_for_agents_tour_missing_section_fails_closed()
    check_for_agents_tour_empty_section_fails_closed()
    check_for_agents_tour_allows_approved_exemption()
    check_status_contract()
    check_fetch_org_repos_read_faults_degrade()
    check_unexpected_statuses_are_recorded_and_later_modules_continue()
    check_gone_statuses_hard_fail_published_modules()
    check_require_reality_escalates_unexpected_status()
    check_orphan_all_repos_accounted_for()
    check_orphan_accounts_for_retired_repos_case_insensitively()
    check_orphan_accounts_for_adjacent_repos()
    check_orphan_flags_unaccounted_public_repo()
    check_orphan_fetch_failure_degrades_instead_of_failing()
    check_orphan_require_reality_escalates_fetch_failure()
    check_retired_scans_beyond_markdown_but_exempts_the_registry()
    check_retired_reports_regex_escaped_github_spelling()
    check_alias_flags_yaml_reference_but_exempts_registry()
    check_alias_no_aliases_produces_no_scan_output()
    check_pin_freshness_accepts_matching_newest_tag()
    check_pin_freshness_accepts_bare_tag_from_message_bearing_entry()
    check_pin_freshness_flags_stale_pin_once()
    check_pin_freshness_flags_stale_pin_with_bare_newest_tag()
    check_pin_freshness_honours_pin_reason()
    check_pin_freshness_fetch_failure_degrades_and_escalates()
    check_fetch_newest_tag_read_faults_degrade()
    check_fetch_newest_tag_unsupported_encoding_degrades()
    check_fetch_newest_tag_prefers_entry_id_over_title_message()
    check_fetch_newest_tag_falls_back_to_first_title_token_when_id_missing()
    check_ci_existence_accepts_200_and_flags_404()
    check_ci_existence_network_error_degrades()
    check_ci_existence_require_reality_escalates_network_error()
    check_ci_workflow_helper_treats_404_as_absent()
    check_ci_workflow_helper_does_not_follow_redirects()
    check_ci_workflow_helper_network_faults_degrade()
    check_schema_rejects_bad_contract_fields()
    check_schema_accepts_public_preview_maturity()
    check_schema_accepts_missing_adjacent_key()
    check_schema_rejects_bad_adjacent_entries()
    check_schema_rejects_missing_adjacent_text_when_adjacent_exists()
    check_schema_rejects_present_null_or_non_list_adjacent()
    print("selftest_check_registry: ok")
