#!/usr/bin/env python3
"""Offline self-tests for the family footer contract."""

from __future__ import annotations

import copy
import pathlib
import tempfile

from family_common import FamilyCommonError, MarkerError, iter_marker_lines, language_of
from family_footer import (
    BLOCK_ID,
    END_MARKER,
    START_MARKER,
    FetchResult,
    check_registry_footers,
    render_region,
    render_repo_to_target,
    resolve_declared_readmes,
)


def base_registry():
    return {
        "languages": ["en", "ja", "zh", "th"],
        "map_repo": "caty-ai/family-os",
        "footer_text": {
            "intro": {
                "en": "Intro {map}.",
                "ja": "Intro {map}.",
                "zh": "Intro {map}.",
                "th": "Intro {map}.",
            },
            "siblings_label": {
                "en": "Siblings",
                "ja": "Siblings",
                "zh": "Siblings",
                "th": "Siblings",
            },
        },
        "modules": [
            {
                "id": "alpha",
                "name": "Alpha",
                "repo": "caty-ai/alpha",
                "status": "published",
            },
            {
                "id": "beta",
                "name": "Beta",
                "repo": "caty-ai/beta",
                "status": "published",
                "readme_overrides": {"README.zh-CN.md": "zh"},
            },
            {
                "id": "gamma",
                "name": "Gamma",
                "repo": "caty-ai/gamma",
                "status": "preparing",
            },
        ],
        "retired_repos": [],
    }


def document_with_region(region: str, newline: str) -> str:
    return START_MARKER + newline + region + END_MARKER + newline


def test_fence_exemption_rules():
    assert list(
        iter_marker_lines(
            "```html\n<!-- family:generated:foreign-block:start -->\n```\n", {BLOCK_ID}
        )
    ) == []

    try:
        list(iter_marker_lines("```html\n%s\n```\n" % START_MARKER, {BLOCK_ID}))
    except MarkerError as exc:
        assert "fenced code block" in str(exc)
    else:
        raise AssertionError("live marker inside a fence must fail")

    try:
        list(
            iter_marker_lines(
                "```html\n<!-- family:generated:foreign-block:starts -->\n```\n",
                {BLOCK_ID},
            )
        )
    except MarkerError as exc:
        assert "malformed generated marker" in str(exc)
    else:
        raise AssertionError("near-miss marker inside a fence must fail")

    try:
        list(iter_marker_lines("<!-- family:generated:foreign-block:starts -->\n", {BLOCK_ID}))
    except MarkerError as exc:
        assert "malformed generated marker" in str(exc)
    else:
        raise AssertionError("near-miss marker outside a fence must fail")


def test_fence_tracker_edges():
    yielded = list(
        iter_marker_lines(
            "```html\n<!-- family:generated:foreign-block:start -->\n````\n%s\n"
            % START_MARKER,
            {BLOCK_ID},
        )
    )
    assert yielded == [(3, BLOCK_ID, "start")]

    try:
        list(
            iter_marker_lines(
                "````html\n<!-- family:generated:foreign-block:start -->\n```\n%s\n"
                % START_MARKER,
                {BLOCK_ID},
            )
        )
    except MarkerError as exc:
        assert "fenced code block" in str(exc)
    else:
        raise AssertionError("shorter close must not end the fence")

    try:
        list(
            iter_marker_lines(
                "```html\n<!-- family:generated:foreign-block:start -->\n~~~\n%s\n```\n"
                % START_MARKER,
                {BLOCK_ID},
            )
        )
    except MarkerError as exc:
        assert "fenced code block" in str(exc)
    else:
        raise AssertionError("mixed fence styles must not end the fence")

    try:
        list(iter_marker_lines("```html\n%s\n" % START_MARKER, {BLOCK_ID}))
    except MarkerError as exc:
        assert "fenced code block" in str(exc)
    else:
        raise AssertionError("unbalanced fence must still reject a live marker inside it")


def test_language_resolution():
    languages = ["en", "ja", "zh", "th"]
    assert language_of(pathlib.Path("README.zh-CN.md"), languages, {}) == "zh"
    assert (
        language_of(pathlib.Path("README.zh-cn.md"), languages, {"README.zh-cn.md": "zh"})
        == "zh"
    )
    try:
        language_of(pathlib.Path("README.ko.md"), languages, {})
    except FamilyCommonError as exc:
        assert "unknown primary" in str(exc)
    else:
        raise AssertionError("unknown primary language must fail")


def test_declared_set_resolution():
    registry = base_registry()
    default_files = resolve_declared_readmes(registry["modules"][0], registry["languages"])
    assert default_files == [
        ("README.md", "en"),
        ("README.ja.md", "ja"),
        ("README.zh.md", "zh"),
        ("README.th.md", "th"),
    ]

    override_files = resolve_declared_readmes(registry["modules"][1], registry["languages"])
    assert override_files == [
        ("README.md", "en"),
        ("README.ja.md", "ja"),
        ("README.zh-CN.md", "zh"),
        ("README.th.md", "th"),
    ]

    reduced = copy.deepcopy(registry["modules"][0])
    reduced["readme_files"] = ["README.md", "README.zh.md"]
    reduced_files = resolve_declared_readmes(reduced, registry["languages"])
    assert reduced_files == [("README.md", "en"), ("README.zh.md", "zh")]


def test_check_rules():
    registry = base_registry()

    mismatch_registry = copy.deepcopy(registry)
    mismatch_registry["modules"][0]["footer"] = True
    good_region = render_region(mismatch_registry, mismatch_registry["modules"][0], "en", "\n")
    bad_doc = document_with_region(good_region.replace("Siblings", "Siblingz", 1), "\n")
    mismatch_fetch = lambda repo, filename: FetchResult("ok", bad_doc)
    failures, notes = check_registry_footers(mismatch_registry, fetcher=mismatch_fetch)
    assert any("footer content does not match the registry" in failure for failure in failures)
    assert notes == []

    unflagged_fetch = lambda repo, filename: FetchResult("ok", document_with_region(good_region, "\n"))
    failures, _notes = check_registry_footers(registry, fetcher=unflagged_fetch)
    assert any("footer exists but is not enforced" in failure for failure in failures)

    no_footer_fetch = lambda repo, filename: FetchResult("ok", "# README\n")
    failures, _notes = check_registry_footers(registry, fetcher=no_footer_fetch)
    assert "caty-ai/alpha: published module has no footer" in failures

    missing_fetch = lambda repo, filename: FetchResult("missing")
    failures, _notes = check_registry_footers(registry, fetcher=missing_fetch)
    assert any("declared README returned 404" in failure for failure in failures)

    missing_markers_registry = copy.deepcopy(registry)
    missing_markers_registry["modules"][0]["footer"] = True
    failures, _notes = check_registry_footers(
        missing_markers_registry, fetcher=lambda repo, filename: FetchResult("ok", "# README\n")
    )
    assert any("footer:true but markers are missing" in failure for failure in failures)

    skip_fetch = lambda repo, filename: FetchResult("skip")
    failures, notes = check_registry_footers(
        registry, require_reality=True, fetcher=skip_fetch
    )
    assert any("degraded: could not verify" in failure for failure in failures)
    assert any("footer check skipped" in note for note in notes)


def test_render_idempotency_and_listing():
    registry = base_registry()
    target_module = registry["modules"][0]
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        for filename in ("README.md", "README.ja.md", "README.zh.md", "README.th.md"):
            (root / filename).write_text("# Title\r\n\r\nBody\r\n", encoding="utf-8", newline="")

        changed, changed_files = render_repo_to_target(registry, root, target_module["repo"])
        assert changed is True
        assert set(changed_files) == {"README.md", "README.ja.md", "README.zh.md", "README.th.md"}

        readme = (root / "README.md").read_bytes().decode("utf-8")
        assert "\r\n" in readme
        assert "[Beta](https://github.com/caty-ai/beta)" in readme
        assert "[Alpha](https://github.com/caty-ai/alpha)" not in readme
        assert "Gamma" not in readme

        changed_again, changed_files_again = render_repo_to_target(
            registry, root, target_module["repo"]
        )
        assert changed_again is False
        assert changed_files_again == []


def main() -> int:
    tests = [
        test_fence_exemption_rules,
        test_fence_tracker_edges,
        test_language_resolution,
        test_declared_set_resolution,
        test_check_rules,
        test_render_idempotency_and_listing,
    ]
    for test in tests:
        test()
    print("OK — family footer selftest passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
