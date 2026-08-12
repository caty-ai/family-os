#!/usr/bin/env python3
"""Offline self-tests for the registry reality check."""

from __future__ import annotations

import urllib.error
from typing import Optional
from unittest import mock

from check_registry import check_reality, github_is_public


class Response:
    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None


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


if __name__ == "__main__":
    check_status_contract()
    check_unexpected_statuses_are_recorded_and_later_modules_continue()
    check_gone_statuses_hard_fail_published_modules()
    check_require_reality_escalates_unexpected_status()
    print("selftest_check_registry: ok")
