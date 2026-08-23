#!/usr/bin/env python3
"""Offline self-tests for the family footer contract."""

from __future__ import annotations

import copy
import json
import pathlib
import tempfile
import urllib.error
from typing import Optional
from unittest import mock

from family_common import FamilyCommonError, MarkerError, iter_marker_lines, language_of
from family_footer import (
    BLOCK_ID,
    END_MARKER,
    ORG_BLOCK_ID,
    ORG_END_MARKER,
    ORG_SVG_PREPARING_BADGES,
    ORG_START_MARKER,
    START_MARKER,
    FetchResult,
    FooterError,
    _assert_org_svg_legacy,
    assert_org_svg,
    check_registry_footers,
    fetch_readme,
    find_footer_regions,
    lint_registry,
    load_registry,
    module_table,
    published_modules,
    render_org_block,
    render_org_to_target,
    render_region,
    render_repo_to_target,
    resolve_declared_readmes,
)


class Response:
    def __init__(self, status: int, text: bytes = b"") -> None:
        self.status = status
        self._text = text

    def read(self) -> bytes:
        return self._text

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
        "https://raw.githubusercontent.com/caty-ai/example/HEAD/README.md",
        code,
        "test",
        headers,
        None,
    )


def base_registry():
    registry = {
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
    profile = {
        "repo": "caty-ai/.github",
        "enforced": True,
        "files": {
            "profile/README.md": "en",
            "README.md": "en",
            "README.ja.md": "ja",
            "README.zh.md": "zh",
            "README.th.md": "th",
        },
        "intro": {lang: "Intro {count}." for lang in registry["languages"]},
        "status_labels": {
            "published": {lang: " (OSS)" for lang in registry["languages"]},
            "preparing": {lang: " (soon)" for lang in registry["languages"]},
        },
        "status_labels_bare": {
            "published": {lang: "OSS" for lang in registry["languages"]},
            "preparing": {lang: "soon" for lang in registry["languages"]},
        },
        "table_headers": {
            lang: ["Module", "In one line", "Status"]
            for lang in registry["languages"]
        },
        "svg_question": {
            lang: "Question %s?" % lang for lang in registry["languages"]
        },
        "map": {
            "name": "Family OS",
            "desc": {lang: "Family map" for lang in registry["languages"]},
            "desc_short": {
                lang: "Family map short" for lang in registry["languages"]
            },
        },
        "modules": {},
    }
    for module in registry["modules"]:
        profile["modules"][module["id"]] = {
            "name": module["id"],
            "desc": {
                lang: "%s description" % module["id"] for lang in registry["languages"]
            },
            "desc_short": {
                lang: "%s short" % module["id"] for lang in registry["languages"]
            },
        }
    registry["org_profile"] = profile
    return registry


def document_with_region(region: str, newline: str) -> str:
    return START_MARKER + newline + region + END_MARKER + newline


def org_document(registry, lang, newline="\n"):
    region = render_org_block(registry, lang).replace("\n", newline)
    return ORG_START_MARKER + newline + region + ORG_END_MARKER + newline


def svg_document(registry, lang, badge_override=None, count_override=None, missing=None):
    count = str(len([m for m in registry["modules"] if m["status"] == "published"]) + 1)
    count = count_override or count
    intro = {
        "en": "%s open today" % count,
        "ja": "このうち%s" % count,
        "zh": "其中%s" % count,
        "th": "%s ตัวในนี้" % count,
    }[lang]
    preparing_badge = {
        "en": "coming soon",
        "ja": "公開準備中",
        "zh": "即将发布",
        "th": "เร็ว ๆ นี้",
    }[lang]
    lines = ["<text>%s</text>" % intro]
    for module in registry["modules"]:
        if module["id"] == missing:
            continue
        badge = "repo ↗" if module["status"] == "published" else preparing_badge
        if badge_override and module["id"] == badge_override[0]:
            badge = badge_override[1]
        lines.extend(("<text>⏺ %s</text>" % module["id"], "<text>%s</text>" % badge))
    return "\n".join(lines)


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


def test_module_table_map_rendering():
    registry = base_registry()
    host = registry["modules"][0]

    default_table = module_table(registry, host, "en", "\n")
    explicit_default_table = module_table(registry, host, "en", "\n", bold_map=False)
    bold_map_table = module_table(registry, None, "en", "\n", bold_map=True)

    assert default_table == explicit_default_table
    assert "| Map | [Family OS](https://github.com/caty-ai/family-os) |" in default_table
    assert "| Map | **Family OS** | The family map | published |" in bold_map_table
    assert "https://github.com/caty-ai/family-os" not in bold_map_table


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


def test_fetch_readme_status_contract():
    cases = [
        (Response(200, b"# README\n"), FetchResult("ok", "# README\n")),
        (
            http_error(301, "https://raw.githubusercontent.com/caty-ai/moved/HEAD/README.md"),
            FetchResult(
                "moved", "https://raw.githubusercontent.com/caty-ai/moved/HEAD/README.md"
            ),
        ),
        (http_error(399), FetchResult("moved")),
        (http_error(404), FetchResult("missing")),
        (http_error(410), FetchResult("hard", "HTTP status 410")),
        (http_error(451), FetchResult("hard", "HTTP status 451")),
        (http_error(403), FetchResult("skip")),
        (http_error(429), FetchResult("skip")),
        (http_error(500), FetchResult("skip")),
        (http_error(599), FetchResult("skip")),
        (http_error(401), FetchResult("skip", "unexpected HTTP status 401")),
        (http_error(405), FetchResult("skip", "unexpected HTTP status 405")),
    ]
    for result, expected in cases:
        with mock.patch(
            "family_footer.urllib.request.build_opener", return_value=Opener(result)
        ) as build_opener, mock.patch(
            "family_footer.urllib.request.urlopen", side_effect=[result]
        ):
            actual = fetch_readme("caty-ai/example", "README.md")
        assert actual == expected, (result, expected, actual)
        handler = build_opener.call_args.args[0]
        assert type(handler).__name__ == "NoRedirectHandler", handler
        assert handler.redirect_request(None, None, 301, None, {}, None) is None


def test_fetch_readme_results_are_recorded_by_footer_check():
    registry = base_registry()

    failures, notes = check_registry_footers(
        registry,
        fetcher=lambda repo, filename: FetchResult(
            "moved", "https://raw.githubusercontent.com/caty-ai/moved/HEAD/README.md"
        ),
    )
    assert any(failure.startswith("moved: caty-ai/alpha:README.md ->") for failure in failures)
    assert notes == []

    failures, notes = check_registry_footers(
        registry, fetcher=lambda repo, filename: FetchResult("moved")
    )
    assert any("-> (missing Location header)" in failure for failure in failures)
    assert notes == []

    failures, notes = check_registry_footers(
        registry, fetcher=lambda repo, filename: FetchResult("hard", "HTTP status 410")
    )
    assert any("caty-ai/alpha:README.md: HTTP status 410" in failure for failure in failures)
    assert notes == []

    failures, notes = check_registry_footers(
        registry,
        fetcher=lambda repo, filename: FetchResult(
            "skip", "unexpected HTTP status 405"
        ),
    )
    assert failures == [], failures
    assert any("unexpected HTTP status 405" in note for note in notes)


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


def checkable_registry():
    registry = base_registry()
    for module in registry["modules"]:
        if module["status"] == "published":
            module["footer"] = True
    return registry


def fixture_fetcher(registry, org_mutations=None, skipped=None, calls=None):
    org_mutations = org_mutations or {}
    skipped = set(skipped or ())
    modules = {module["repo"]: module for module in registry["modules"]}

    def fetch(repo, filename):
        if calls is not None:
            calls.append((repo, filename))
        if (repo, filename) in skipped:
            return FetchResult("skip")
        if repo == registry["org_profile"]["repo"]:
            if filename in registry["org_profile"]["files"]:
                lang = registry["org_profile"]["files"][filename]
                text = org_document(registry, lang)
                mutation = org_mutations.get(filename)
                if mutation:
                    text = mutation(text)
                return FetchResult("ok", text)
            svg_langs = {
                "profile/assets/readme-terminal-en.svg": "en",
                "profile/assets/readme-terminal-ja.svg": "ja",
                "profile/assets/readme-terminal-zh.svg": "zh",
                "profile/assets/readme-terminal-th.svg": "th",
            }
            if filename in svg_langs:
                return FetchResult("ok", svg_document(registry, svg_langs[filename]))
        module = modules.get(repo)
        if module is not None:
            lang = dict(resolve_declared_readmes(module, registry["languages"]))[filename]
            return FetchResult("ok", document_with_region(render_region(registry, module, lang, "\n"), "\n"))
        return FetchResult("missing")

    return fetch


def test_org_required_and_enforcement_fail_closed():
    deleted = base_registry()
    del deleted["org_profile"]
    assert "registry/modules.json: org_profile must be an object" in lint_registry(deleted)

    present = checkable_registry()
    present["org_profile"]["enforced"] = False
    failures, _notes = check_registry_footers(present, fetcher=fixture_fetcher(present))
    assert any("org profile block exists but is not enforced" in failure for failure in failures)

    absent = checkable_registry()
    absent["org_profile"]["enforced"] = False
    mutations = {"README.zh.md": lambda _text: "# no markers\n"}
    failures, _notes = check_registry_footers(
        absent, fetcher=fixture_fetcher(absent, org_mutations=mutations)
    )
    assert any(
        "README.zh.md" in failure and "markers are missing" in failure
        for failure in failures
    )


def test_org_ordered_fetch_and_per_file_failures():
    registry = checkable_registry()
    calls = []
    failures, _notes = check_registry_footers(
        registry, fetcher=fixture_fetcher(registry, calls=calls)
    )
    assert failures == []
    declared_org_calls = [
        filename
        for repo, filename in calls
        if repo == registry["org_profile"]["repo"] and filename.endswith(".md")
    ]
    assert declared_org_calls == [
        "profile/README.md",
        "README.md",
        "README.ja.md",
        "README.zh.md",
        "README.th.md",
    ]
    svg_calls = [
        filename
        for repo, filename in calls
        if repo == registry["org_profile"]["repo"] and filename.endswith(".svg")
    ]
    assert svg_calls == [
        "profile/assets/readme-terminal-en.svg",
        "profile/assets/readme-terminal-ja.svg",
        "profile/assets/readme-terminal-zh.svg",
        "profile/assets/readme-terminal-th.svg",
    ]

    mutations = {"README.th.md": lambda text: text.replace("gamma short", "drift", 1)}
    failures, _notes = check_registry_footers(
        registry, fetcher=fixture_fetcher(registry, org_mutations=mutations)
    )
    assert any("README.th.md" in failure and "does not match" in failure for failure in failures)
    assert not any("README.ja.md" in failure for failure in failures)

    mutations = {"README.md": lambda text: text.replace("alpha short", "drift", 1)}
    failures, _notes = check_registry_footers(
        registry, fetcher=fixture_fetcher(registry, org_mutations=mutations)
    )
    assert any("README.md" in failure and "does not match" in failure for failure in failures)
    assert not any("profile/README.md" in failure for failure in failures)


def test_duplicate_json_key_and_org_declared_set_guards():
    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "duplicate.json"
        path.write_text('{"languages": [], "languages": []}', encoding="utf-8")
        try:
            load_registry(path)
        except FooterError as exc:
            assert "duplicate JSON key 'languages'" in str(exc)
        else:
            raise AssertionError("duplicate JSON keys must fail")

    for bad_path in (
        "../x/README.md",
        "/etc/README.md",
        "profile\\README.md",
        "profile/%2e%2e/README.md",
        "profile/READ ME.md",
        "README.md.bak",
        "readme.md",
        "docs/README.md",
    ):
        registry = base_registry()
        files = registry["org_profile"]["files"]
        first = next(iter(files))
        files[bad_path] = files.pop(first)
        assert any("not an allowed README path" in failure for failure in lint_registry(registry))

    dropped = base_registry()
    del dropped["org_profile"]["files"]["README.th.md"]
    assert any(
        "closed declared set" in failure for failure in lint_registry(dropped)
    )

    reordered = base_registry()
    files = reordered["org_profile"]["files"]
    first_language = files.pop("profile/README.md")
    files["profile/README.md"] = first_language
    assert any(
        "closed declared set" in failure for failure in lint_registry(reordered)
    )


def test_org_module_key_set_fails_closed():
    registry = checkable_registry()
    del registry["org_profile"]["modules"]["beta"]

    lint_failures = lint_registry(registry)
    assert any(
        "org_profile.modules keys must exactly match modules[].id" in failure
        and "missing: beta" in failure
        for failure in lint_failures
    )

    failures, notes = check_registry_footers(
        registry, fetcher=fixture_fetcher(registry)
    )
    assert failures == lint_failures
    assert notes == []

    try:
        render_org_block(registry, "en")
    except FooterError as exc:
        assert "registry module 'beta' is missing from org_profile.modules" in str(exc)
    else:
        raise AssertionError("render_org_block must translate a missing key to FooterError")


def test_org_table_validator_attacks_and_required_fields():
    attacks = (
        "bad\nvalue",
        "bad\tvalue",
        "bad\x7fvalue",
        "family:generated:attack",
        "bad]",
        "bad[",
        "bad|",
        "bad<",
        "bad`",
        "-bad",
        "*bad",
        "#bad",
        ">bad",
    )
    for attack in attacks:
        registry = base_registry()
        registry["org_profile"]["modules"]["alpha"]["desc_short"]["en"] = attack
        assert lint_registry(registry), "table attack was accepted: %r" % attack

    injected = base_registry()
    injected["org_profile"]["modules"]["alpha"]["desc_short"]["en"] = (
        "<!-- family:generated:org-profile-modules:start -->"
    )
    assert any("generated-marker text" in failure for failure in lint_registry(injected))

    missing = base_registry()
    del missing["org_profile"]["modules"]["alpha"]["desc_short"]
    assert any(
        "org_profile.modules.alpha.desc_short must be an object" in failure
        for failure in lint_registry(missing)
    )

    missing_language = base_registry()
    del missing_language["org_profile"]["map"]["desc_short"]["ja"]
    assert any(
        "org_profile.map.desc_short must contain exactly the languages" in failure
        for failure in lint_registry(missing_language)
    )

    empty = base_registry()
    empty["org_profile"]["modules"]["beta"]["desc_short"]["zh"] = ""
    assert any(
        "org_profile.modules.beta.desc_short.zh must be non-empty" in failure
        for failure in lint_registry(empty)
    )

    for field in ("status_labels_bare", "table_headers", "svg_question"):
        registry = base_registry()
        del registry["org_profile"][field]
        assert any("org_profile.%s" % field in failure for failure in lint_registry(registry))


def test_org_count_preparing_and_golden_bytes():
    fixture = {
        "languages": ["en", "ja", "zh", "th"],
        "map_repo": "fixture/map",
        "modules": [
            {
                "id": "zed",
                "repo": "fixture/zed-repo",
                "status": "published",
            },
            {
                "id": "prep",
                "repo": "fixture/prep-repo",
                "status": "preparing",
            },
            {
                "id": "alpha",
                "repo": "other/alpha-repo",
                "status": "published",
            },
        ],
        "org_profile": {
            "intro": {
                "en": "E{count}",
                "ja": "日{count}",
                "zh": "中{count}",
                "th": "ท{count}",
            },
            "status_labels": {
                "published": {
                    "en": " (P)",
                    "ja": "（公）",
                    "zh": "（发）",
                    "th": " (ผ)",
                },
                "preparing": {
                    "en": " (S)",
                    "ja": "（準）",
                    "zh": "（备）",
                    "th": " (ร)",
                },
            },
            "status_labels_bare": {
                "published": {"en": "P", "ja": "公", "zh": "发", "th": "ผ"},
                "preparing": {"en": "S", "ja": "準", "zh": "备", "th": "ร"},
            },
            "table_headers": {
                "en": ["M", "R", "S"],
                "ja": ["日M", "日R", "日S"],
                "zh": ["中M", "中R", "中S"],
                "th": ["ทM", "ทR", "ทS"],
            },
            "map": {
                "name": "Map",
                "desc": {"en": "eM", "ja": "日M", "zh": "中M", "th": "ทM"},
                "desc_short": {
                    "en": "eMs",
                    "ja": "日Ms",
                    "zh": "中Ms",
                    "th": "ทMs",
                },
            },
            "modules": {
                "zed": {
                    "name": "Zed",
                    "desc": {"en": "eZ", "ja": "日Z", "zh": "中Z", "th": "ทZ"},
                    "desc_short": {
                        "en": "eZs",
                        "ja": "日Zs",
                        "zh": "中Zs",
                        "th": "ทZs",
                    },
                },
                "prep": {
                    "name": "Prep",
                    "desc": {"en": "eQ", "ja": "日Q", "zh": "中Q", "th": "ทQ"},
                    "desc_short": {
                        "en": "eQs",
                        "ja": "日Qs",
                        "zh": "中Qs",
                        "th": "ทQs",
                    },
                },
                "alpha": {
                    "name": "Alpha",
                    "desc": {"en": "eA", "ja": "日A", "zh": "中A", "th": "ทA"},
                    "desc_short": {
                        "en": "eAs",
                        "ja": "日As",
                        "zh": "中As",
                        "th": "ทAs",
                    },
                },
            },
        },
    }
    expected = {
        "en": (
            "\nE3\n\n"
            "| M | R | S |\n"
            "|---|---|---|\n"
            "| **[Map](https://github.com/fixture/map)** | eMs | P |\n"
            "| **[Zed](https://github.com/fixture/zed-repo)** | eZs | P |\n"
            "| **Prep** | eQs | S |\n"
            "| **[Alpha](https://github.com/other/alpha-repo)** | eAs | P |\n\n"
        ),
        "ja": (
            "\n日3\n\n"
            "| 日M | 日R | 日S |\n"
            "|---|---|---|\n"
            "| **[Map](https://github.com/fixture/map)** | 日Ms | 公 |\n"
            "| **[Zed](https://github.com/fixture/zed-repo)** | 日Zs | 公 |\n"
            "| **Prep** | 日Qs | 準 |\n"
            "| **[Alpha](https://github.com/other/alpha-repo)** | 日As | 公 |\n\n"
        ),
        "zh": (
            "\n中3\n\n"
            "| 中M | 中R | 中S |\n"
            "|---|---|---|\n"
            "| **[Map](https://github.com/fixture/map)** | 中Ms | 发 |\n"
            "| **[Zed](https://github.com/fixture/zed-repo)** | 中Zs | 发 |\n"
            "| **Prep** | 中Qs | 备 |\n"
            "| **[Alpha](https://github.com/other/alpha-repo)** | 中As | 发 |\n\n"
        ),
        "th": (
            "\nท3\n\n"
            "| ทM | ทR | ทS |\n"
            "|---|---|---|\n"
            "| **[Map](https://github.com/fixture/map)** | ทMs | ผ |\n"
            "| **[Zed](https://github.com/fixture/zed-repo)** | ทZs | ผ |\n"
            "| **Prep** | ทQs | ร |\n"
            "| **[Alpha](https://github.com/other/alpha-repo)** | ทAs | ผ |\n\n"
        ),
    }

    published_count = sum(
        module["status"] == "published" for module in fixture["modules"]
    )
    preparing = [
        module for module in fixture["modules"] if module["status"] == "preparing"
    ]
    assert len(preparing) == 1
    for lang in fixture["languages"]:
        rendered = render_org_block(fixture, lang)
        assert rendered == expected[lang]
        assert rendered.splitlines()[1] == fixture["org_profile"]["intro"][lang].replace(
            "{count}", str(published_count + 1)
        )
        preparing_profile = fixture["org_profile"]["modules"][preparing[0]["id"]]
        assert "| **%s** |" % preparing_profile["name"] in rendered
        assert "https://github.com/%s" % preparing[0]["repo"] not in rendered


def test_org_ja_intro_uses_counter_for_eleven():
    # The live registry plus one fixture module must land in the double-digit
    # regime, where the ja intro takes the 個 counter, never つ. Counted from
    # the registry so a new published module does not invalidate this test.
    registry = load_registry()
    registry["modules"].append(
        {"id": "extra", "repo": "fixture/extra", "status": "published"}
    )
    registry["org_profile"]["modules"]["extra"] = {
        "name": "extra",
        "desc_short": {lang: "extra" for lang in registry["languages"]},
    }
    count = len(published_modules(registry)) + 1
    assert count >= 11
    rendered = render_org_block(registry, "ja")
    assert "このうち%d個は" % count in rendered
    assert "このうち%dつは" % count not in rendered


def test_org_degradation_and_svg_assertions():
    registry = checkable_registry()
    org_repo = registry["org_profile"]["repo"]
    skipped = {(org_repo, filename) for filename in registry["org_profile"]["files"]}
    failures, notes = check_registry_footers(
        registry, fetcher=fixture_fetcher(registry, skipped=skipped)
    )
    assert failures == []
    assert len([note for note in notes if "org profile check skipped" in note]) == 5
    failures, _notes = check_registry_footers(
        registry,
        require_reality=True,
        fetcher=fixture_fetcher(registry, skipped=skipped),
    )
    assert any(
        "degraded: could not verify 5 targets" in failure for failure in failures
    )

    assert ORG_SVG_PREPARING_BADGES == {
        "en": "coming soon",
        "ja": "公開準備中",
        "zh": "即将发布",
        "th": "เร็ว ๆ นี้",
    }
    for lang in registry["languages"]:
        assert assert_org_svg(
            registry, lang, svg_document(registry, lang), "fixture"
        ) == []

        minimal = "<svg><text>visitor voice</text><text>%s</text></svg>" % (
            registry["org_profile"]["svg_question"][lang]
        )
        assert assert_org_svg(registry, lang, minimal, "fixture") == []

    legacy_complete_ja = svg_document(registry, "ja")
    assert assert_org_svg(registry, "ja", legacy_complete_ja, "fixture") == []
    legacy_with_question_ja = "%s\n<text>%s</text>" % (
        legacy_complete_ja,
        registry["org_profile"]["svg_question"]["ja"],
    )
    legacy_with_question_failures = assert_org_svg(
        registry, "ja", legacy_with_question_ja, "fixture"
    )
    for module in registry["modules"]:
        assert any(
            "minimal profile contains module residue '%s'" % module["id"] in failure
            for failure in legacy_with_question_failures
        )

    passing = svg_document(registry, "en")
    published_to_preparing = svg_document(
        registry, "en", badge_override=("alpha", "coming soon")
    )
    assert any(
        "alpha" in failure and "badge 'repo ↗'" in failure
        for failure in _assert_org_svg_legacy(
            registry, "en", published_to_preparing, "fixture"
        )
    )
    preparing_to_published = svg_document(
        registry, "en", badge_override=("gamma", "repo ↗")
    )
    assert any(
        "gamma" in failure and "badge 'coming soon'" in failure
        for failure in _assert_org_svg_legacy(
            registry, "en", preparing_to_published, "fixture"
        )
    )
    missing_preparing_badge = passing.replace(
        "<text>⏺ gamma</text>\n<text>coming soon</text>",
        "<text>⏺ gamma</text>\n<text>⏺ trailing-module</text>",
    )
    assert any(
        "gamma" in failure and "no badge" in failure
        for failure in _assert_org_svg_legacy(
            registry, "en", missing_preparing_badge, "fixture"
        )
    )
    expected_count = str(
        len([module for module in registry["modules"] if module["status"] == "published"]) + 1
    )
    wrong_count = svg_document(registry, "en", count_override=expected_count * 2)
    assert any(
        "count" in failure
        for failure in _assert_org_svg_legacy(
            registry, "en", wrong_count, "fixture"
        )
    )
    missing = svg_document(registry, "en", missing="beta")
    assert any(
        "missing module 'beta'" in failure
        for failure in _assert_org_svg_legacy(registry, "en", missing, "fixture")
    )
    substring_only = passing.replace(
        "<text>⏺ alpha</text>", "<text>prefix ⏺ alpha suffix</text>"
    )
    assert any(
        "missing module 'alpha'" in failure
        for failure in _assert_org_svg_legacy(
            registry, "en", substring_only, "fixture"
        )
    )

    question = registry["org_profile"]["svg_question"]["en"]
    mixed = "<svg><text>%s</text><text>alpha</text></svg>" % question
    mixed_legacy_failures = _assert_org_svg_legacy(
        registry, "en", mixed, "fixture"
    )
    assert any("missing module 'alpha'" in failure for failure in mixed_legacy_failures)
    assert any("missing the ecosystem intro line" in failure for failure in mixed_legacy_failures)
    mixed_failures = assert_org_svg(registry, "en", mixed, "fixture")
    assert any(
        "minimal profile contains module residue 'alpha'" in failure
        for failure in mixed_failures
    )

    empty_failures = assert_org_svg(registry, "en", "<svg></svg>", "fixture")
    assert empty_failures
    assert all("minimal profile" in failure for failure in empty_failures)
    assert any("missing the question needle" in failure for failure in empty_failures)


def test_org_render_and_block_isolation():
    registry = base_registry()
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        for filename, lang in registry["org_profile"]["files"].items():
            path = root / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(org_document(registry, lang), encoding="utf-8")
        first = render_org_to_target(registry, root, stray_scan=True)
        assert all(changed is False for _filename, changed in first)
        second = render_org_to_target(registry, root, stray_scan=True)
        assert first == second
        missing_path = root / "README.th.md"
        original = missing_path.read_text(encoding="utf-8")
        missing_path.write_text(
            original.replace(ORG_START_MARKER, "missing start marker", 1).replace(
                ORG_END_MARKER, "missing end marker", 1
            ),
            encoding="utf-8",
        )
        try:
            render_org_to_target(registry, root)
        except FooterError as exc:
            assert "README.th.md" in str(exc) and "markers are missing" in str(exc)
        else:
            raise AssertionError("render-org must list a file with missing markers")
        missing_path.write_text(original, encoding="utf-8")
        stray = root / "notes.md"
        stray.write_text(ORG_START_MARKER + "\n", encoding="utf-8")
        try:
            render_org_to_target(registry, root, stray_scan=True)
        except FooterError as exc:
            assert "outside the declared file set" in str(exc)
        else:
            raise AssertionError("stray org marker must fail")

    both = org_document(registry, "en") + document_with_region("\n", "\n")
    try:
        find_footer_regions("both.md", both, ORG_BLOCK_ID)
    except FooterError as exc:
        assert "unknown block-id 'family-footer'" in str(exc)
    else:
        raise AssertionError("a pass must reject the other live block id")


def main() -> int:
    tests = [
        test_fence_exemption_rules,
        test_fence_tracker_edges,
        test_language_resolution,
        test_declared_set_resolution,
        test_table_rendering,
        test_map_row_and_registry_ordering,
        test_module_table_map_rendering,
        test_table_lint_failures,
        test_check_rules,
        test_fetch_readme_status_contract,
        test_fetch_readme_results_are_recorded_by_footer_check,
        test_render_idempotency_and_listing,
        test_org_required_and_enforcement_fail_closed,
        test_org_ordered_fetch_and_per_file_failures,
        test_duplicate_json_key_and_org_declared_set_guards,
        test_org_module_key_set_fails_closed,
        test_org_table_validator_attacks_and_required_fields,
        test_org_count_preparing_and_golden_bytes,
        test_org_ja_intro_uses_counter_for_eleven,
        test_org_degradation_and_svg_assertions,
        test_org_render_and_block_isolation,
    ]
    for test in tests:
        test()
        print("ok: %s" % test.__name__)
    print("OK — family footer selftest passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
