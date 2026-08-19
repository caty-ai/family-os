#!/usr/bin/env python3
"""Offline self-tests for the registry reality, orphan, and retired checks."""

from __future__ import annotations

import http.client
import pathlib
import tempfile
import urllib.error
from typing import Optional
from unittest import mock

from check_registry import (
    check_orphan,
    check_reality,
    check_retired,
    fetch_org_repos,
    github_is_public,
)


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


if __name__ == "__main__":
    check_status_contract()
    check_fetch_org_repos_read_faults_degrade()
    check_unexpected_statuses_are_recorded_and_later_modules_continue()
    check_gone_statuses_hard_fail_published_modules()
    check_require_reality_escalates_unexpected_status()
    check_orphan_all_repos_accounted_for()
    check_orphan_accounts_for_retired_repos_case_insensitively()
    check_orphan_flags_unaccounted_public_repo()
    check_orphan_fetch_failure_degrades_instead_of_failing()
    check_orphan_require_reality_escalates_fetch_failure()
    check_retired_scans_beyond_markdown_but_exempts_the_registry()
    check_retired_reports_regex_escaped_github_spelling()
    print("selftest_check_registry: ok")
