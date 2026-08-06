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
    FooterError,
    check_registry_footers,
    lint_registry,
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
            "table_axis": {
                "en": "Axis",
                "ja": "軸",
                "zh": "轴",
                "th": "แกน",
            },
            "table_module": {
                "en": "Module",
                "ja": "モジュール",
                "zh": "模块",
                "th": "โมดูล",
            },
            "table_what": {
                "en": "What it does",
                "ja": "何をするもの",
                "zh": "做什么",
                "th": "ทำอะไร",
            },
            "table_state": {
                "en": "State",
                "ja": "状態",
                "zh": "状态",
                "th": "สถานะ",
            },
            "map_name": {
                "en": "Family OS",
                "ja": "Family OS",
                "zh": "Family OS",
                "th": "Family OS",
            },
            "axis_map": {
                "en": "Map",
                "ja": "地図",
                "zh": "地图",
                "th": "แผนที่",
            },
            "axis_rules": {
                "en": "Rules",
                "ja": "掟",
                "zh": "规则",
                "th": "กติกา",
            },
            "axis_vertical": {
                "en": "Vertical",
                "ja": "縦軸",
                "zh": "纵轴",
                "th": "แกนตั้ง",
            },
            "axis_horizontal": {
                "en": "Horizontal",
                "ja": "横軸",
                "zh": "横轴",
                "th": "แกนนอน",
            },
            "axis_foundation_suffix": {
                "en": " · foundation",
                "ja": "・基盤",
                "zh": "・基座",
                "th": " · รากฐาน",
            },
            "map_tagline": {
                "en": "The family map",
                "ja": "ファミリーの地図",
                "zh": "家族地图",
                "th": "แผนที่ครอบครัว",
            },
        },
        "status_labels": {
            "published": {
                "en": "published",
                "ja": "公開",
                "zh": "已公开",
                "th": "เปิดแล้ว",
            },
            "preparing": {
                "en": "preparing",
                "ja": "準備中",
                "zh": "准备中",
                "th": "กำลังเตรียม",
            },
        },
        "modules": [
            {
                "id": "alpha",
                "name": "Alpha",
                "repo": "caty-ai/alpha",
                "status": "published",
                "tagline": {
                    "en": "Alpha work",
                    "ja": "Alpha の仕事",
                    "zh": "Alpha 的工作",
                    "th": "งานของ Alpha",
                },
                "axis": {"group": "rules", "foundation": False},
            },
            {
                "id": "beta",
                "name": "Beta",
                "repo": "caty-ai/beta",
                "status": "published",
                "tagline": {
                    "en": "Beta work",
                    "ja": "Beta の仕事",
                    "zh": "Beta 的工作",
                    "th": "งานของ Beta",
                },
                "axis": {"group": "vertical", "foundation": True},
                "readme_overrides": {"README.zh-CN.md": "zh"},
            },
            {
                "id": "gamma",
                "name": "Gamma",
                "repo": "caty-ai/gamma",
                "status": "preparing",
                "tagline": {
                    "en": "Gamma work",
                    "ja": "Gamma の仕事",
                    "zh": "Gamma 的工作",
                    "th": "งานของ Gamma",
                },
                "axis": {"group": "horizontal", "foundation": False},
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


def test_table_rendering():
    registry = base_registry()
    region = render_region(registry, registry["modules"][0], "en", "\n")
    table_lines = [line for line in region.splitlines() if line.startswith("|")]
    assert table_lines == [
        "| Axis | Module | What it does | State |",
        "| --- | --- | --- | --- |",
        "| Map | [Family OS](https://github.com/caty-ai/family-os) | The family map | published |",
        "| Rules | **Alpha** | Alpha work | published |",
        "| Vertical · foundation | [Beta](https://github.com/caty-ai/beta) | Beta work | published |",
        "| Horizontal | **Gamma** | Gamma work | preparing |",
    ]
    assert "https://github.com/caty-ai/alpha" not in region
    assert "https://github.com/caty-ai/gamma" not in region

    ja_region = render_region(registry, registry["modules"][0], "ja", "\n")
    assert "| 軸 | モジュール | 何をするもの | 状態 |" in ja_region
    assert "| 地図 | [Family OS](https://github.com/caty-ai/family-os) | ファミリーの地図 | 公開 |" in ja_region
    assert "| 掟 | **Alpha** | Alpha の仕事 | 公開 |" in ja_region
    assert "| 縦軸・基盤 | [Beta](https://github.com/caty-ai/beta) | Beta の仕事 | 公開 |" in ja_region
    assert "| 横軸 | **Gamma** | Gamma の仕事 | 準備中 |" in ja_region


def test_map_row_and_registry_ordering():
    registry = base_registry()
    for host in registry["modules"] + [None]:
        region = render_region(registry, host, "en", "\n")
        data_rows = [
            line
            for line in region.splitlines()
            if line.startswith("|") and not line.startswith("| ---")
        ][1:]
        assert data_rows[0].startswith(
            "| Map | [Family OS](https://github.com/caty-ai/family-os) |"
        )

    reordered = copy.deepcopy(registry)
    reordered["modules"] = [
        reordered["modules"][2],
        reordered["modules"][0],
        reordered["modules"][1],
    ]
    region = render_region(reordered, reordered["modules"][0], "en", "\n")
    assert region.index("| Horizontal | **Gamma**") < region.index("| Rules | [Alpha]")
    assert region.index("| Rules | [Alpha]") < region.index("| Vertical · foundation | [Beta]")


def test_table_lint_failures():
    missing_tagline = base_registry()
    del missing_tagline["modules"][0]["tagline"]["th"]
    failures = lint_registry(missing_tagline)
    assert any(
        "module 'alpha': tagline.th must be a string" in failure for failure in failures
    )

    missing_headers = base_registry()
    del missing_headers["footer_text"]["table_what"]
    del missing_headers["footer_text"]["table_state"]["zh"]
    failures = lint_registry(missing_headers)
    assert "registry/modules.json: footer_text.table_what must be an object" in failures
    assert "registry/modules.json: footer_text.table_state.zh must be a string" in failures

    invalid_tagline = base_registry()
    invalid_tagline["modules"][0]["tagline"]["en"] = "Alpha | work"
    try:
        render_region(invalid_tagline, invalid_tagline["modules"][0], "en", "\n")
    except FooterError as exc:
        assert "tagline.en may not contain '|'" in str(exc)
    else:
        raise AssertionError("a pipe in a rendered tagline must fail closed")

    missing_axis = base_registry()
    del missing_axis["modules"][0]["axis"]
    failures = lint_registry(missing_axis)
    assert "registry/modules.json: module 'alpha': axis must be an object" in failures

    bad_axis_group = base_registry()
    bad_axis_group["modules"][0]["axis"]["group"] = "diagonal"
    failures = lint_registry(bad_axis_group)
    assert any("axis.group must be one of" in failure for failure in failures)

    missing_axis_language = base_registry()
    del missing_axis_language["footer_text"]["axis_vertical"]["ja"]
    failures = lint_registry(missing_axis_language)
    assert "registry/modules.json: footer_text.axis_vertical.ja must be a string" in failures

    invalid_axis_label = base_registry()
    invalid_axis_label["footer_text"]["axis_rules"]["en"] = "Rules | policy"
    failures = lint_registry(invalid_axis_label)
    assert "registry/modules.json: footer_text.axis_rules.en may not contain '|'" in failures


def test_check_rules():
    registry = base_registry()

    mismatch_registry = copy.deepcopy(registry)
    mismatch_registry["modules"][0]["footer"] = True
    good_region = render_region(mismatch_registry, mismatch_registry["modules"][0], "en", "\n")
    bad_doc = document_with_region(good_region.replace("Alpha work", "Alpha drift", 1), "\n")
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
        assert "| Map | [Family OS](https://github.com/caty-ai/family-os) |" in readme
        assert "| Rules | **Alpha** | Alpha work | published |" in readme
        assert "| Horizontal | **Gamma** | Gamma work | preparing |" in readme
        assert "https://github.com/caty-ai/gamma" not in readme

        ja_readme = (root / "README.ja.md").read_bytes().decode("utf-8")
        assert "| 軸 | モジュール | 何をするもの | 状態 |" in ja_readme
        assert "| 地図 | [Family OS](https://github.com/caty-ai/family-os) |" in ja_readme
        assert "| 掟 | **Alpha** | Alpha の仕事 | 公開 |" in ja_readme
        assert "| 横軸 | **Gamma** | Gamma の仕事 | 準備中 |" in ja_readme

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
        test_table_rendering,
        test_map_row_and_registry_ordering,
        test_table_lint_failures,
        test_check_rules,
        test_render_idempotency_and_listing,
    ]
    for test in tests:
        test()
    print("OK — family footer selftest passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
