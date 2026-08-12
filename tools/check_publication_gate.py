#!/usr/bin/env python3
"""Fail closed when publication sources expose private context or stale state.

The public repository is copied and rendered in places where comments, metadata,
and source-only text remain visible. This gate therefore checks raw source, ties
personal repository URLs to the registry, requires state labels beside module
home links, and keeps SVG decorations subordinate to Markdown state claims.

Python 3.9+, standard library only.
"""

import argparse
import html
import json
import pathlib
import re
import subprocess
import sys
from typing import Dict, Iterable, List, Mapping, Set, Tuple


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCANNED_SUFFIXES = frozenset((".md", ".json", ".py", ".yml", ".yaml", ".svg", ".sh"))
ACCOUNT_SLUG = "sho" + "jikumaru"
ACCOUNT_MASK = "_account_slug_"

# Changes to these fail-closed policy rules require owner approval.
DENYLIST_PATTERNS = (
    (
        "personal real name",
        re.compile(r"\b(?:" + "Sho" + "ji|Ku" + "maru" + r")\b", re.IGNORECASE),
    ),
    ("personal real name", re.compile("翔" + "さん|翔" + "士", re.IGNORECASE)),
    (
        "approval record",
        re.compile(
            "承認" + "記録|オーナー" + "承認|approved" + r"\s+by|CP-\d+\s*(?:GO|承認)",
            re.IGNORECASE,
        ),
    ),
    ("absolute personal path", re.compile(re.escape("/" + "Users" + "/"))),
    (
        "private network address",
        re.compile(r"\b100\.(?:6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\.\d+\.\d+\b"),
    ),
    ("local service address", re.compile("local" + r"host:\d+", re.IGNORECASE)),
    (
        "email address",
        re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    ),
    (
        "private repository reference",
        re.compile(
            r"\b(?:"
            + "alpha-" + "loom|alpha-" + "wiki|alpha-" + "mission-control|"
            + "family-" + "vault|wip-" + "caty-talk|sitter-" + "private|claude-" + "workspace"
            + r")\b",
            re.IGNORECASE,
        ),
    ),
)

# Exact (repository-relative path, full line text) additions require owner approval.
# The initial population ships with issue #26 for review. These are navigation
# prose / axis-description tables where the label lives elsewhere. Any change
# to these lines breaks the whitelist match and must come back through owner
# approval; that breakage is intended fail-closed behavior.
MISSING_LABEL_WHITELIST: Tuple[Tuple[str, str], ...] = (
    (
        "README.ja.md",
        "迷ったら、縦軸の [Caty Agent Harness](https://github.com/caty-ai/caty-agent-harness) から始めてください。1体のAIが失敗から学び、長い作業を証拠つきで最後まで進められるようになります。無料の MIT で、導入手順はそのリポジトリの README にあります。いちばん困っているのが「黙って止まる作業」なら、[Sitter](https://github.com/caty-ai/sitter) へ直接どうぞ — こちらも公開済み・MIT です。",
    ),
    (
        "README.ja.md",
        "横軸の [FMA](https://github.com/caty-ai/family-memory-architecture) も公開済み（MIT）です。いちばん困っているのが「記憶がばらばら」なら、そちらから始めてください。",
    ),
    (
        "README.ja.md",
        "迷ったら、縦軸の [Caty Agent Harness](https://github.com/caty-ai/caty-agent-harness) から始めてください。1体のAIが失敗から学び、長い作業を証拠つきで最後まで進められるようになります。無料の MIT で、導入手順はそのリポジトリの README にあります。いちばん困っているのが「黙って止まる作業」なら、[Sitter](https://github.com/caty-ai/sitter) へ直接どうぞ — こちらも公開済み・MIT です。",
    ),
    (
        "README.md",
        "If you are unsure, start with [Caty Agent Harness](https://github.com/caty-ai/caty-agent-harness) on the vertical axis. It lets one agent learn from failure and carry long work through to the end with evidence behind it. It is free under MIT, and the setup steps are in that repository's README. If the thing that hurts most is work that stops without telling you, go straight to [Sitter](https://github.com/caty-ai/sitter) instead — it is also open and also MIT.",
    ),
    (
        "README.md",
        "FMA on the horizontal axis is published too (MIT). If scattered memory is what hurts most, start with [FMA](https://github.com/caty-ai/family-memory-architecture).",
    ),
    (
        "README.md",
        "If you are unsure, start with [Caty Agent Harness](https://github.com/caty-ai/caty-agent-harness) on the vertical axis. It lets one agent learn from failure and carry long work through to the end with evidence behind it. It is free under MIT, and the setup steps are in that repository's README. If the thing that hurts most is work that stops without telling you, go straight to [Sitter](https://github.com/caty-ai/sitter) instead — it is also open and also MIT.",
    ),
    (
        "README.th.md",
        "ถ้าไม่แน่ใจว่าจะเริ่มตรงไหน ให้เริ่มจาก [Caty Agent Harness](https://github.com/caty-ai/caty-agent-harness) บนแกนตั้ง มันทำให้ AI หนึ่งตัวเรียนรู้จากความล้มเหลว และเดินงานยาว ๆ ไปจนจบพร้อมหลักฐาน เป็น MIT ที่ใช้ฟรี และขั้นตอนการติดตั้งอยู่ใน README ของรีโปนั้น ถ้าสิ่งที่เจ็บที่สุดคืองานที่หยุดไปเงียบ ๆ โดยไม่บอก ให้ตรงไปที่ [Sitter](https://github.com/caty-ai/sitter) ได้เลย — เปิดแล้วเช่นกันและเป็น MIT เช่นกัน",
    ),
    (
        "README.th.md",
        "[FMA](https://github.com/caty-ai/family-memory-architecture) บนแกนนอนก็เปิดแล้วเช่นกัน (MIT) ถ้าสิ่งที่ปวดหัวที่สุดคือความทรงจำที่กระจัดกระจาย เริ่มจากตัวนั้นได้เลย",
    ),
    (
        "README.th.md",
        "ถ้าไม่แน่ใจว่าจะเริ่มตรงไหน ให้เริ่มจาก [Caty Agent Harness](https://github.com/caty-ai/caty-agent-harness) บนแกนตั้ง มันทำให้ AI หนึ่งตัวเรียนรู้จากความล้มเหลว และเดินงานยาว ๆ ไปจนจบพร้อมหลักฐาน เป็น MIT ที่ใช้ฟรี และขั้นตอนการติดตั้งอยู่ใน README ของรีโปนั้น ถ้าสิ่งที่เจ็บที่สุดคืองานที่หยุดไปเงียบ ๆ โดยไม่บอก ให้ตรงไปที่ [Sitter](https://github.com/caty-ai/sitter) ได้เลย — เปิดแล้วเช่นกันและเป็น MIT เช่นกัน",
    ),
    (
        "README.zh.md",
        "如果不知从何入手，就从纵轴的 [Caty Agent Harness](https://github.com/caty-ai/caty-agent-harness) 开始。它能让一个 AI 从失败中学习，并带着证据把长时间的工作做到最后。它是免费的 MIT，安装步骤在那个仓库的 README 里。如果最让你头疼的是「悄无声息就停住的工作」，那就直接去 [Sitter](https://github.com/caty-ai/sitter) —— 它同样已经公开，同样是 MIT。",
    ),
    (
        "README.zh.md",
        "横轴的 [FMA](https://github.com/caty-ai/family-memory-architecture) 也已公开（MIT）。如果你最头疼的是记忆各自为政，就从它开始。",
    ),
    (
        "README.zh.md",
        "如果不知从何入手，就从纵轴的 [Caty Agent Harness](https://github.com/caty-ai/caty-agent-harness) 开始。它能让一个 AI 从失败中学习，并带着证据把长时间的工作做到最后。它是免费的 MIT，安装步骤在那个仓库的 README 里。如果最让你头疼的是「悄无声息就停住的工作」，那就直接去 [Sitter](https://github.com/caty-ai/sitter) —— 它同样已经公开，同样是 MIT。",
    ),
    (
        "docs/engineering.ja.md",
        "| 掟 | 並行作業を壊さない進め方 — Issue・ブランチ・worktree・受け渡し | [Family Dev Handbook](https://github.com/caty-ai/family-dev-handbook) |",
    ),
    (
        "docs/engineering.ja.md",
        "| 縦軸 | 1体のAIが、覚え・やり切り・育つ方法 | [Caty Agent Harness](https://github.com/caty-ai/caty-agent-harness) と成長ループ |",
    ),
    (
        "docs/engineering.ja.md",
        "| 横軸 | 複数のAIが記憶を共有し、仕事を渡す方法 | [Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture) と [Sitter](https://github.com/caty-ai/sitter) |",
    ),
    (
        "docs/engineering.ja.md",
        "| 横軸 | 複数のAIが記憶を共有し、仕事を渡す方法 | [Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture) と [Sitter](https://github.com/caty-ai/sitter) |",
    ),
    (
        "docs/engineering.md",
        "| Rules | how parallel work stays safe — issues, branches, worktrees, handoffs | [Family Dev Handbook](https://github.com/caty-ai/family-dev-handbook) |",
    ),
    (
        "docs/engineering.md",
        "| Vertical | how one agent remembers, finishes, and grows | [Caty Agent Harness](https://github.com/caty-ai/caty-agent-harness) plus growth loops |",
    ),
    (
        "docs/engineering.md",
        "| Horizontal | how several agents share memory and hand work over | [Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture) and [Sitter](https://github.com/caty-ai/sitter) |",
    ),
    (
        "docs/engineering.md",
        "| Horizontal | how several agents share memory and hand work over | [Family Memory Architecture](https://github.com/caty-ai/family-memory-architecture) and [Sitter](https://github.com/caty-ai/sitter) |",
    ),
)

LANG_SUFFIX = re.compile(r"\.(?P<lang>[a-z]{2}(?:-[A-Z]{2})?)\.md$")
PERSONAL_GITHUB_URL = re.compile(
    r"github\.com/" + re.escape(ACCOUNT_SLUG) + r"/(?P<repo>[A-Za-z0-9_.-]+)",
    re.IGNORECASE,
)
SVG_TEXT_ELEMENT = re.compile(
    r"<(text|title|desc|metadata)\b[^>]*>(.*?)</\1\s*>", re.IGNORECASE | re.DOTALL
)


def language_of(path: pathlib.Path) -> str:
    """Match the Markdown suffix convention used by check_registry.py."""
    match = LANG_SUFFIX.search(path.name)
    return match.group("lang") if match else "en"


def iter_source_paths(root: pathlib.Path) -> Iterable[pathlib.Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=str(root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise OSError(
            "could not enumerate repository sources: %s"
            % result.stderr.decode("utf-8", errors="replace").strip()
        )
    for relative_bytes in sorted(filter(None, result.stdout.split(b"\0"))):
        relative = relative_bytes.decode("utf-8")
        path = root / relative
        if not path.is_file() or path.suffix.lower() not in SCANNED_SUFFIXES:
            continue
        yield path


def read_sources(root: pathlib.Path, failures: List[str]) -> Dict[str, str]:
    documents: Dict[str, str] = {}
    for path in iter_source_paths(root):
        relative = path.relative_to(root).as_posix()
        try:
            documents[relative] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            failures.append("source-read: %s could not be read as UTF-8: %s" % (relative, exc))
    return documents


def mask_account_slug(text: str) -> str:
    return text.replace(ACCOUNT_SLUG, ACCOUNT_MASK)


def line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def check_denylist(documents: Mapping[str, str], failures: List[str]) -> int:
    checked = 0
    for path, text in documents.items():
        masked = mask_account_slug(text)
        for description, pattern in DENYLIST_PATTERNS:
            for match in pattern.finditer(masked):
                failures.append(
                    "denylist: %s:%d contains %s" % (path, line_number(masked, match.start()), description)
                )
                checked += 1
    return checked


def registry_allowlist(registry: dict) -> Set[str]:
    repos = {module["repo"] for module in registry["modules"]}
    repos.update(entry["repo"] for entry in registry.get("retired_repos", []))
    if not all(isinstance(repo, str) and "/" in repo for repo in repos):
        raise ValueError("module and retired repository names must be owner/repository strings")
    return repos


def check_personal_urls(
    markdown: Mapping[str, str], registry: dict, failures: List[str]
) -> int:
    allowlist = registry_allowlist(registry)
    checked = 0
    for path, text in markdown.items():
        for match in PERSONAL_GITHUB_URL.finditer(text):
            repo = "%s/%s" % (ACCOUNT_SLUG, match.group("repo"))
            checked += 1
            if repo not in allowlist:
                failures.append(
                    "personal-url: %s:%d references unknown repository %s"
                    % (path, line_number(text, match.start()), repo)
                )
    return checked


def module_names(module: dict) -> Set[str]:
    name = module["name"]
    if isinstance(name, str):
        names = {name}
    elif isinstance(name, dict) and all(isinstance(value, str) for value in name.values()):
        names = set(name.values())
    else:
        raise ValueError("modules[].name must be a string or language-to-string object")
    names.add(module["repo"].rsplit("/", 1)[-1])
    return {value for value in names if value}


def repo_home_pattern(repo: str) -> re.Pattern:
    base = r"(?:https?://)?github\.com/" + re.escape(repo)
    terminator = r"""[\s`'<>,.)"#?]"""
    return re.compile(base + r"/?(?=$|" + terminator + r")", re.IGNORECASE)


def check_missing_labels(
    markdown: Mapping[str, str], registry: dict, failures: List[str]
) -> int:
    labels = registry["status_labels"]
    map_repo = registry.get("map_repo")
    checked = 0

    for path_text, text in markdown.items():
        path = pathlib.Path(path_text)
        lang = language_of(path)
        lines = text.splitlines()
        for module in registry["modules"]:
            if module["repo"] == map_repo:
                continue
            try:
                label = labels[module["status"]][lang]
            except (KeyError, TypeError) as exc:
                failures.append(
                    "missing-label: registry has no label for %s status=%s language=%s (%s)"
                    % (module.get("repo", "<unknown>"), module.get("status", "<unknown>"), lang, exc)
                )
                continue

            pattern = repo_home_pattern(module["repo"])
            for number, line in enumerate(lines, 1):
                if not pattern.search(line):
                    continue
                checked += 1
                if label not in line and (path_text, line) not in MISSING_LABEL_WHITELIST:
                    failures.append(
                        "missing-label: %s:%d links to %s without '%s' on the same line"
                        % (path_text, number, module["repo"], label)
                    )
    return checked


def name_pattern(name: str) -> re.Pattern:
    return re.compile(
        r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])", re.IGNORECASE
    )


def svg_visible_text(source: str) -> str:
    chunks = []
    for match in SVG_TEXT_ELEMENT.finditer(source):
        without_tags = re.sub(r"<[^>]+>", " ", match.group(2))
        chunks.append(html.unescape(without_tags))
    return "\n".join(chunks)


def markdown_status_evidence(markdown: Mapping[str, str], registry: dict) -> Dict[str, bool]:
    labels = registry["status_labels"]
    evidence = {module["repo"]: False for module in registry["modules"]}
    for path_text, text in markdown.items():
        lang = language_of(pathlib.Path(path_text))
        for module in registry["modules"]:
            try:
                label = labels[module["status"]][lang]
            except (KeyError, TypeError):
                continue
            markers = module_names(module)
            markers.add("github.com/%s" % module["repo"])
            for line in text.splitlines():
                if label in line and any(name_pattern(marker).search(line) for marker in markers):
                    evidence[module["repo"]] = True
                    break
    return evidence


def check_svg_state_sources(
    svg_documents: Mapping[str, str],
    markdown: Mapping[str, str],
    registry: dict,
    failures: List[str],
) -> int:
    evidence = markdown_status_evidence(markdown, registry)
    checked = 0
    for path, source in svg_documents.items():
        visible = svg_visible_text(source)
        for module in registry["modules"]:
            for name in sorted(module_names(module)):
                if not name_pattern(name).search(visible):
                    continue
                checked += 1
                if not evidence[module["repo"]]:
                    failures.append(
                        "svg-state: %s contains '%s' for %s, but no Markdown line carries its name/link and status label"
                        % (path, name, module["repo"])
                    )
    return checked


def fixture_registry() -> dict:
    return {
        "languages": ["en", "ja"],
        "map_repo": "caty-ai/family-os",
        "status_labels": {
            "published": {"en": "published, MIT", "ja": "公開・MIT"}
        },
        "footer_text": {"table_state": {"en": "State", "ja": "状態"}},
        "modules": [
            {
                "name": "Alpha Module",
                "repo": "caty-ai/alpha-module",
                "status": "published",
            }
        ],
        "retired_repos": [{"repo": ACCOUNT_SLUG + "/retired-module"}],
    }


def selftest_denylist() -> None:
    failures: List[str] = []
    clean = {"clean.md": "https://github.com/%s/retired-module\n" % ACCOUNT_SLUG}
    assert check_denylist(clean, failures) == 0 and failures == []

    violations = (
        "Sho" + "ji",
        "承認" + "記録",
        "/" + "Users" + "/person/project",
        "100." + "64.1.2",
        "local" + "host:8080",
        "person" + "@example.com",
        "alpha-" + "loom",
    )
    for index, violation in enumerate(violations):
        caught: List[str] = []
        assert check_denylist({"negative-%d.md" % index: violation}, caught) >= 1
        assert caught


def selftest_personal_urls() -> None:
    registry = fixture_registry()
    failures: List[str] = []
    clean = {"README.md": "https://github.com/%s/retired-module" % ACCOUNT_SLUG}
    assert check_personal_urls(clean, registry, failures) == 1 and failures == []

    caught: List[str] = []
    negative = {"README.md": "https://github.com/%s/unknown-module" % ACCOUNT_SLUG}
    assert check_personal_urls(negative, registry, caught) == 1 and caught


def selftest_missing_labels() -> None:
    registry = fixture_registry()
    pattern = repo_home_pattern("caty-ai/alpha-module")
    for terminator in (" ", "\t", "`", "'", "<", ">", ",", ".", ")", '"', "#", "?", ""):
        assert pattern.search("https://github.com/caty-ai/alpha-module" + terminator)
        assert pattern.search("https://github.com/caty-ai/alpha-module/" + terminator)
    assert not pattern.search("https://github.com/caty-ai/alpha-module/issues/3")

    failures: List[str] = []
    clean = {
        "README.md": "- [Alpha](https://github.com/caty-ai/alpha-module) (published, MIT)\n"
        "https://github.com/caty-ai/alpha-module/issues/3\n"
        "- [Family OS](https://github.com/caty-ai/family-os)\n",
        "README.ja.md": "| モジュール | 状態 |\n"
        "| --- | --- |\n"
        "| [Alpha](https://github.com/caty-ai/alpha-module) | 公開・MIT |\n",
    }
    assert check_missing_labels(clean, registry, failures) == 2 and failures == []

    caught: List[str] = []
    negative = {"README.md": "- [Alpha](https://github.com/caty-ai/alpha-module)"}
    assert check_missing_labels(negative, registry, caught) == 1 and caught

    prose_caught: List[str] = []
    negative_prose = {
        "README.md": "See [Alpha](https://github.com/caty-ai/alpha-module) for details."
    }
    assert check_missing_labels(negative_prose, registry, prose_caught) == 1
    assert prose_caught

    bare_space_caught: List[str] = []
    negative_bare_space = {
        "README.md": "See https://github.com/caty-ai/alpha-module for details."
    }
    assert check_missing_labels(negative_bare_space, registry, bare_space_caught) == 1
    assert bare_space_caught

    table_caught: List[str] = []
    negative_table = {
        "README.ja.md": "| モジュール | 状態 |\n"
        "| --- | --- |\n"
        "| [Alpha](https://github.com/caty-ai/alpha-module) | 不明 |\n"
    }
    assert check_missing_labels(negative_table, registry, table_caught) == 1
    assert table_caught

    whitelisted_line = next(
        line
        for path, line in MISSING_LABEL_WHITELIST
        if path == "README.md" and "caty-ai/caty-agent-harness" in line
    )
    whitelist_registry = fixture_registry()
    whitelist_registry["modules"][0].update(
        {"name": "Caty Agent Harness", "repo": "caty-ai/caty-agent-harness"}
    )
    whitelist_failures: List[str] = []
    assert check_missing_labels(
        {"README.md": whitelisted_line}, whitelist_registry, whitelist_failures
    ) == 1
    assert whitelist_failures == []

    deep_link_failures: List[str] = []
    deep_link = {
        "README.md": "See https://github.com/caty-ai/alpha-module/issues/3 for details."
    }
    assert check_missing_labels(deep_link, registry, deep_link_failures) == 0
    assert deep_link_failures == []


def selftest_svg_state_sources() -> None:
    registry = fixture_registry()
    clean_svg = {"assets/map.svg": "<svg><text>Alpha Module</text></svg>"}
    clean_md = {
        "README.md": "Alpha Module — https://github.com/caty-ai/alpha-module — published, MIT"
    }
    failures: List[str] = []
    assert check_denylist(clean_svg, failures) == 0
    assert check_svg_state_sources(clean_svg, clean_md, registry, failures) == 1
    assert failures == []

    caught: List[str] = []
    assert check_svg_state_sources(clean_svg, {"README.md": "Alpha Module"}, registry, caught) == 1
    assert caught

    denylist_caught: List[str] = []
    private_svg = {"assets/private.svg": "<metadata>local" + "host:9000</metadata>"}
    assert check_denylist(private_svg, denylist_caught) == 1 and denylist_caught


def run_selftests() -> int:
    tests = (
        selftest_denylist,
        selftest_personal_urls,
        selftest_missing_labels,
        selftest_svg_state_sources,
    )
    for test in tests:
        test()
        print("ok: %s" % test.__name__)
    print("OK — publication gate selftest passed; all negative fixtures were caught.")
    return 0


def load_registry(root: pathlib.Path) -> dict:
    path = root / "registry" / "modules.json"
    registry = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(registry.get("modules"), list) or not registry["modules"]:
        raise ValueError("registry modules must be a non-empty list")
    if not isinstance(registry.get("status_labels"), dict):
        raise ValueError("registry status_labels must be an object")
    return registry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true", help="run embedded gate fixtures")
    parser.add_argument(
        "--root",
        type=pathlib.Path,
        default=REPO_ROOT,
        help="repository checkout to inspect (default: the checkout containing this script)",
    )
    args = parser.parse_args()
    if args.selftest:
        return run_selftests()

    root = args.root.expanduser().resolve()
    failures: List[str] = []
    try:
        registry = load_registry(root)
        documents = read_sources(root, failures)
        markdown = {path: text for path, text in documents.items() if path.endswith(".md")}
        svg_documents = {path: text for path, text in documents.items() if path.endswith(".svg")}

        denylist_hits = check_denylist(documents, failures)
        personal_urls = check_personal_urls(markdown, registry, failures)
        root_links = check_missing_labels(markdown, registry, failures)
        svg_names = check_svg_state_sources(svg_documents, markdown, registry, failures)
    except (KeyError, OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        failures.append("gate-error: publication checks could not complete: %s" % exc)
        denylist_hits = personal_urls = root_links = svg_names = 0

    print("source files scanned : %d" % len(locals().get("documents", {})))
    print("denylist matches     : %d" % denylist_hits)
    print("personal URLs checked: %d" % personal_urls)
    print("module links checked : %d" % root_links)
    print("SVG names checked    : %d" % svg_names)
    print("label whitelist      : %d" % len(MISSING_LABEL_WHITELIST))

    if failures:
        print("\nFAILED (%d):" % len(failures))
        for failure in failures:
            print("  - %s" % failure)
        return 1

    print(
        "\nOK — publication gate passed with %d explicit label whitelist entries."
        % len(MISSING_LABEL_WHITELIST)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
