#!/usr/bin/env python3
"""Audit repository-state stamps across every public repository in the org.

The org universe is deliberately enumerated without authentication.  The
Actions sub-check is the one exception: GitHub does not expose workflow state
reliably to anonymous callers, so it prefers GH_TOKEN/GITHUB_TOKEN when present.

Python 3.9+, standard library only.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from check_registry import fetch_org_repos


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = REPO_ROOT / "registry" / "modules.json"
DEFAULT_SCHEMA = REPO_ROOT / "docs" / "repo-state" / "status.schema.json"
DEFAULT_GENERATOR = REPO_ROOT / "tools" / "repo-state-gen.sh"

REPOSITORY_PATH = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
STAMP_PREFIX = "chore(repo-state):"
BOT_COMMITTER = "github-actions[bot]"
TRANSIENT_MAX_AGE = datetime.timedelta(days=7)
BEGIN_MARKER = "<!-- repo-state:begin (generated; do not edit) -->"
END_MARKER = "<!-- repo-state:end -->"

STATUS_ORDER = {"PASS": 0, "UNKNOWN": 1, "TRANSIENT": 2, "FAIL": 3}
SUPPORTED_SCHEMA_KEYWORDS = {
    "$id",
    "$schema",
    "additionalProperties",
    "const",
    "description",
    "enum",
    "format",
    "minLength",
    "pattern",
    "properties",
    "required",
    "title",
    "type",
}


class AuditError(Exception):
    """A known audit-contract failure."""


@dataclasses.dataclass(frozen=True)
class CommitIdentity:
    sha: str
    parents: Tuple[str, ...]
    committer: str
    committed_at: datetime.datetime
    message: str

    @property
    def is_stamp_message(self) -> bool:
        return self.message.startswith(STAMP_PREFIX)


@dataclasses.dataclass(frozen=True)
class Check:
    status: str
    detail: str


@dataclasses.dataclass(frozen=True)
class RepoResult:
    repo: str
    status: str
    details: Tuple[str, ...]


def run_git(repo_dir: pathlib.Path, *args: str) -> str:
    command = ["git", "-C", str(repo_dir)] + list(args)
    completed = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        raise AuditError("git %s failed" % " ".join(args))
    return completed.stdout.rstrip("\n")


def read_commit(repo_dir: pathlib.Path, revision: str) -> CommitIdentity:
    output = run_git(
        repo_dir,
        "show",
        "-s",
        "--format=%H%x00%P%x00%cn%x00%cI%x00%B",
        revision,
    )
    fields = output.split("\x00", 4)
    if len(fields) != 5:
        raise AuditError("could not parse commit identity for %s" % revision)
    sha, raw_parents, committer, committed_at, message = fields
    parents = tuple(raw_parents.split()) if raw_parents else ()
    try:
        timestamp = datetime.datetime.fromisoformat(committed_at.replace("Z", "+00:00"))
    except ValueError:
        raise AuditError("could not parse commit date for %s" % revision)
    return CommitIdentity(sha, parents, committer, timestamp, message.rstrip("\n"))


def nearest_non_stamp_ancestor(repo_dir: pathlib.Path, revision: str) -> str:
    """Walk the first-parent stamp chain until commit identity is content."""
    current = read_commit(repo_dir, revision)
    while current.is_stamp_message:
        if len(current.parents) != 1:
            raise AuditError(
                "stamp commit %s must have exactly one parent" % current.sha
            )
        current = read_commit(repo_dir, current.parents[0])
    return current.sha


def classify_identity(
    repo_dir: pathlib.Path,
    status: dict,
    now: Optional[datetime.datetime] = None,
) -> Check:
    mode = status.get("stamp_mode")
    described = status.get("describes_commit")
    head = read_commit(repo_dir, "HEAD")

    if mode == "auto":
        if not head.is_stamp_message:
            current_time = now or datetime.datetime.now(datetime.timezone.utc)
            age = current_time - head.committed_at.astimezone(datetime.timezone.utc)
            if age >= TRANSIENT_MAX_AGE:
                return Check(
                    "FAIL",
                    "HEAD has remained an unstamped content commit for at least 7 days",
                )
            return Check(
                "TRANSIENT",
                "HEAD is a content commit; the automatic stamp may still be pending",
            )
        if head.committer != BOT_COMMITTER:
            return Check(
                "FAIL",
                "HEAD has a stamp message but committer is not github-actions[bot]",
            )
        expected = nearest_non_stamp_ancestor(repo_dir, head.sha)
        if described != expected:
            return Check(
                "FAIL",
                "auto stamp describes %s, nearest non-stamp ancestor is %s"
                % (str(described)[:12], expected[:12]),
            )
        return Check("PASS", "auto identity invariant holds")

    if mode == "verify-only":
        if head.is_stamp_message:
            return Check(
                "FAIL",
                "verify-only HEAD must be the merged content commit, not a stamp commit",
            )
        if not head.parents:
            return Check("FAIL", "verify-only HEAD has no base-branch parent lineage")
        expected = nearest_non_stamp_ancestor(repo_dir, head.parents[0])
        if described != expected:
            return Check(
                "FAIL",
                "verify-only stamp describes %s, base HEAD^ lineage resolves to %s"
                % (str(described)[:12], expected[:12]),
            )
        return Check("PASS", "verify-only base HEAD^ identity invariant holds")

    return Check("FAIL", "unknown stamp_mode %r" % mode)


def _json_type_matches(value, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    return False


def _valid_datetime(value: str) -> bool:
    try:
        datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return "T" in value and (
        value.endswith("Z") or re.search(r"[+-][0-9]{2}:[0-9]{2}$", value) is not None
    )


def _valid_uri(value: str) -> bool:
    parsed = urllib.parse.urlsplit(value)
    return bool(parsed.scheme and parsed.netloc)


def _validate_node(value, schema: dict, path: str, errors: List[str]) -> None:
    # Issue #133 makes agents_entry nullable.  Accept both the v0.11 schema and
    # that forward-compatible representation while the sibling lane lands.
    if path == "$.agents_entry" and value is None:
        return

    expected_types = schema.get("type")
    if expected_types is not None:
        if isinstance(expected_types, str):
            expected_types = [expected_types]
        if not any(_json_type_matches(value, item) for item in expected_types):
            errors.append("%s: expected type %s" % (path, " or ".join(expected_types)))
            return

    if "const" in schema and value != schema["const"]:
        errors.append("%s: does not match the schema constant" % path)
    if "enum" in schema and value not in schema["enum"]:
        errors.append("%s: is not one of the allowed values" % path)

    if isinstance(value, dict):
        required = schema.get("required", [])
        for field in required:
            if field not in value:
                errors.append("%s.%s: required property is missing" % (path, field))
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for field in value:
                if field not in properties:
                    errors.append("%s.%s: additional property is not allowed" % (path, field))
        for field, child in properties.items():
            if field in value:
                _validate_node(value[field], child, "%s.%s" % (path, field), errors)

    if isinstance(value, str):
        minimum = schema.get("minLength")
        if minimum is not None and len(value) < minimum:
            errors.append("%s: shorter than minLength %d" % (path, minimum))
        pattern = schema.get("pattern")
        if pattern is not None and re.search(pattern, value) is None:
            errors.append("%s: does not match the required pattern" % path)
        format_name = schema.get("format")
        if format_name == "date-time" and not _valid_datetime(value):
            errors.append("%s: is not a valid date-time" % path)
        if format_name == "uri" and not _valid_uri(value):
            errors.append("%s: is not a valid URI" % path)


def ensure_supported_schema(schema: dict, path: str = "$") -> None:
    unknown = sorted(set(schema) - SUPPORTED_SCHEMA_KEYWORDS)
    if unknown:
        raise AuditError(
            "%s uses unsupported schema keywords: %s" % (path, ", ".join(unknown))
        )
    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        raise AuditError("%s.properties must be an object" % path)
    for field, child in properties.items():
        if not isinstance(child, dict):
            raise AuditError("%s.properties.%s must be an object" % (path, field))
        ensure_supported_schema(child, "%s.properties.%s" % (path, field))


def validate_status(status: dict, schema: dict, repo: str) -> List[str]:
    errors: List[str] = []
    _validate_node(status, schema, "$", errors)
    if status.get("repo") != repo:
        errors.append("$.repo: expected %s" % repo)
    if status.get("branch") != "main":
        errors.append("$.branch: weekly audit requires main")
    if status.get("generated_at") != status.get("describes_commit_date"):
        errors.append("$.generated_at: must equal describes_commit_date")

    described = status.get("describes_commit")
    expected_api = "https://api.github.com/repos/%s/commits/main" % repo
    expected_raw = "https://raw.githubusercontent.com/%s/%s/status.json" % (
        repo,
        described,
    )
    if status.get("canonical_api") != expected_api:
        errors.append("$.canonical_api: inconsistent with repo/main")
    if status.get("canonical_raw") != expected_raw:
        errors.append("$.canonical_raw: inconsistent with describes_commit")
    return errors


def _expected_block(status: dict) -> List[str]:
    return [
        BEGIN_MARKER,
        '<p align="center"><sub>generation: <code>%s</code> (%s) · verify: '
        '<a href="%s">API HEAD</a> · <a href="./status.json">status.json</a></sub></p>'
        % (
            status["describes_commit"][:7],
            status["generated_at"],
            status["canonical_api"],
        ),
        END_MARKER,
    ]


def _block_bounds(lines: Sequence[str], path: pathlib.Path) -> Tuple[int, int]:
    begins = [index for index, line in enumerate(lines) if BEGIN_MARKER in line]
    ends = [index for index, line in enumerate(lines) if END_MARKER in line]
    if len(begins) != 1 or len(ends) != 1 or begins[0] >= ends[0]:
        raise AuditError("%s: missing, duplicate, or malformed stamp markers" % path.name)
    if lines[begins[0]] != BEGIN_MARKER or lines[ends[0]] != END_MARKER:
        raise AuditError("%s: stamp markers must occupy exact lines" % path.name)
    return begins[0], ends[0]


def strip_stamp_block(data: bytes, path: pathlib.Path) -> bytes:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AuditError("%s is not UTF-8: %s" % (path.name, error))
    lines = text.splitlines(keepends=True)
    marker_lines = [line.rstrip("\r\n") for line in lines]
    begin, end = _block_bounds(marker_lines, path)
    return "".join(lines[:begin] + lines[end + 1 :]).encode("utf-8")


def validate_stamp_blocks(repo_dir: pathlib.Path, status: dict) -> List[pathlib.Path]:
    readmes = sorted(
        path for path in repo_dir.glob("README*.md") if path.is_file()
    )
    if not readmes:
        raise AuditError("no root README*.md files found")
    targets = list(readmes)
    agents_entry = status.get("agents_entry")
    if agents_entry is None:
        if (repo_dir / "AGENTS.md").exists() or (repo_dir / "FOR-AGENTS.md").exists():
            raise AuditError("agents_entry is null but an agent entry file exists")
    else:
        agents_path = repo_dir / agents_entry
        if not agents_path.is_file():
            raise AuditError("agents_entry file %s is missing" % agents_entry)
        targets.append(agents_path)

    expected = _expected_block(status)
    for path in targets:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError) as error:
            raise AuditError("could not read %s: %s" % (path.name, error))
        begin, end = _block_bounds(lines, path)
        if lines[begin : end + 1] != expected:
            raise AuditError("%s: stamp block is inconsistent with status.json" % path.name)
    return targets


def _snapshot_paths(
    repo_dir: pathlib.Path, paths: Iterable[str]
) -> Dict[str, bytes]:
    snapshot: Dict[str, bytes] = {}
    for relative in sorted(set(paths)):
        path = repo_dir / relative
        if path.is_file():
            snapshot[relative] = path.read_bytes()
    return snapshot


def _nul_paths(output: str) -> List[str]:
    return [path for path in output.split("\x00") if path]


def _working_tree_changes(repo_dir: pathlib.Path) -> List[str]:
    changed = set(_nul_paths(run_git(repo_dir, "diff", "--name-only", "-z", "--")))
    changed.update(
        _nul_paths(run_git(repo_dir, "diff", "--cached", "--name-only", "-z", "--"))
    )
    changed.update(
        _nul_paths(run_git(repo_dir, "ls-files", "--others", "--exclude-standard", "-z"))
    )
    return sorted(changed)


def check_regeneration(
    repo_dir: pathlib.Path,
    repo: str,
    status: dict,
    generator: pathlib.Path,
    identity: Check,
) -> Check:
    agents_entry = status.get("agents_entry")
    nullable_without_agents = (
        agents_entry is None
        and not (repo_dir / "AGENTS.md").exists()
        and not (repo_dir / "FOR-AGENTS.md").exists()
    )

    allowed = {"status.json"}
    allowed.update(
        path.name for path in repo_dir.glob("README*.md") if path.is_file()
    )
    if agents_entry is not None:
        allowed.add(agents_entry)
    before = _snapshot_paths(repo_dir, allowed)
    environment = os.environ.copy()
    environment.update(
        {
            "REPO_STATE_NO_GH": "1",
            "REPO_STATE_REPO": repo,
            "REPO_STATE_BRANCH": "main",
        }
    )
    try:
        completed = subprocess.run(
            ["sh", str(generator), "--stamp-mode", status["stamp_mode"]],
            cwd=str(repo_dir),
            env=environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError:
        return Check("FAIL", "canonical generator could not be executed")
    if completed.returncode != 0:
        if (
            nullable_without_agents
            and "neither FOR-AGENTS.md nor AGENTS.md exists" in completed.stderr
        ):
            return Check(
                "UNKNOWN",
                "regeneration skipped: v0.11.0 generator cannot run without an agents entry",
            )
        return Check("FAIL", "canonical generator failed")

    changed = _working_tree_changes(repo_dir)
    after = _snapshot_paths(repo_dir, allowed)

    outside = [path for path in changed if path not in allowed]
    if outside:
        return Check(
            "FAIL",
            "generator changed files outside managed regions: %s" % ", ".join(outside),
        )

    for relative in changed:
        if relative == "status.json":
            continue
        path = pathlib.Path(relative)
        if relative not in before or relative not in after:
            return Check("FAIL", "generator added or removed managed file %s" % relative)
        try:
            if strip_stamp_block(before[relative], path) != strip_stamp_block(
                after[relative], path
            ):
                return Check(
                    "FAIL", "generator changed content outside the stamp block in %s" % relative
                )
        except AuditError as error:
            return Check("FAIL", str(error))

    if not changed:
        return Check("PASS", "canonical regeneration is byte-clean")
    if status["stamp_mode"] == "auto" and identity.status == "PASS":
        return Check(
            "FAIL",
            "canonical regeneration changed managed state on a healthy auto stamp",
        )
    return Check(
        "PASS",
        "canonical regeneration changed only stamp-managed regions (%s)"
        % ", ".join(changed),
    )


def _http_json(url: str, token: Optional[str], timeout: float):
    opener = urllib.request.build_opener()

    def fetch(auth_token: Optional[str]):
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "family-os-repo-state-audit",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if auth_token:
            headers["Authorization"] = "Bearer %s" % auth_token
        request = urllib.request.Request(url, headers=headers)
        with opener.open(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        return fetch(token)
    except urllib.error.HTTPError:
        if not token:
            raise
        return fetch(None)


def check_actions(repo: str, token: Optional[str], timeout: float) -> Check:
    if not token:
        return Check("UNKNOWN", "caller UNKNOWN(no-token)")
    encoded_repo = urllib.parse.quote(repo, safe="/")
    try:
        payload = _http_json(
            "https://api.github.com/repos/%s/actions/workflows?per_page=100" % encoded_repo,
            token,
            timeout,
        )
        workflows = payload.get("workflows") if isinstance(payload, dict) else None
        if not isinstance(workflows, list):
            return Check("FAIL", "repo-state caller workflow list is unparseable")
        if any(not isinstance(workflow, dict) for workflow in workflows):
            return Check("FAIL", "repo-state caller workflow list is unparseable")
        total_count = payload.get("total_count")
        if isinstance(total_count, int) and total_count > len(workflows):
            return Check("FAIL", "repo-state caller workflow list is truncated")

        exact = [
            workflow
            for workflow in workflows
            if workflow.get("path") == ".github/workflows/repo-state.yml"
        ]
        candidates = exact or [
            workflow
            for workflow in workflows
            if "repo-state" in str(workflow.get("path", "")).casefold()
            or str(workflow.get("name", "")).casefold()
            in {"repository state", "repo-state"}
        ]
        if not candidates:
            return Check("FAIL", "repo-state caller workflow is missing")
        if len(candidates) != 1:
            return Check("FAIL", "repo-state caller workflow is ambiguous")
        workflow = candidates[0]
        if workflow.get("state") != "active":
            return Check(
                "FAIL",
                "repo-state caller workflow is %s" % workflow.get("state", "unparseable"),
            )
        workflow_id = workflow.get("id")
        if not isinstance(workflow_id, int):
            return Check("FAIL", "repo-state caller workflow id is unparseable")

        runs = _http_json(
            "https://api.github.com/repos/%s/actions/workflows/%d/runs?branch=main&per_page=100"
            % (encoded_repo, workflow_id),
            token,
            timeout,
        )
        workflow_runs = runs.get("workflow_runs") if isinstance(runs, dict) else None
        if not isinstance(workflow_runs, list):
            return Check("FAIL", "repo-state caller run list is unparseable")
        if not workflow_runs:
            return Check("UNKNOWN", "no main-branch caller runs yet")
        saw_in_progress = False
        for run in workflow_runs:
            if not isinstance(run, dict):
                return Check("FAIL", "latest repo-state caller run is unparseable")
            conclusion = run.get("conclusion")
            if conclusion in {"skipped", "cancelled"}:
                continue
            if conclusion is None:
                saw_in_progress = True
                continue
            if conclusion != "success":
                return Check(
                    "FAIL", "latest repo-state caller conclusion is %s" % conclusion
                )
            return Check("PASS", "latest repo-state caller conclusion is success")
        if saw_in_progress:
            return Check("UNKNOWN", "no terminal caller run yet")
        return Check(
            "UNKNOWN", "only skipped/cancelled caller runs in the latest page"
        )
    except (
        AuditError,
        OSError,
        urllib.error.URLError,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ):
        return Check("UNKNOWN", "caller UNKNOWN(api-error)")


def _combine(checks: Iterable[Check]) -> Tuple[str, Tuple[str, ...]]:
    checks = tuple(checks)
    status = max(checks, key=lambda item: STATUS_ORDER[item.status]).status
    details = tuple(check.detail for check in checks)
    return status, details


def _load_status(repo_dir: pathlib.Path, schema: dict, repo: str) -> Tuple[dict, List[pathlib.Path]]:
    path = repo_dir / "status.json"
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise AuditError("could not read status.json: %s" % error)
    if len(raw) > 2048:
        raise AuditError("status.json exceeds 2 KiB")
    try:
        status = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise AuditError("status.json is not valid UTF-8 JSON: %s" % error)
    if not isinstance(status, dict):
        raise AuditError("status.json must be a JSON object")
    errors = validate_status(status, schema, repo)
    if errors:
        raise AuditError("status.json invalid: %s" % "; ".join(errors))
    targets = validate_stamp_blocks(repo_dir, status)
    return status, targets


def audit_checkout(
    repo: str,
    repo_dir: pathlib.Path,
    schema: dict,
    generator: pathlib.Path,
    token: Optional[str],
    timeout: float,
) -> RepoResult:
    if not (repo_dir / "status.json").exists():
        return RepoResult(repo, "PENDING", ("status.json absent (rollout not landed)",))
    try:
        status, _targets = _load_status(repo_dir, schema, repo)
        identity = classify_identity(repo_dir, status)
        regeneration = check_regeneration(repo_dir, repo, status, generator, identity)
        actions = check_actions(repo, token, timeout)
        overall, details = _combine((identity, regeneration, actions))
        return RepoResult(repo, overall, details)
    except AuditError as error:
        return RepoResult(repo, "FAIL", (str(error),))


def _clone_main(
    repo: str, destination: pathlib.Path, timeout: float
) -> Optional[Check]:
    try:
        completed = subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                "--filter=blob:none",
                "--no-tags",
                "https://github.com/%s.git" % repo,
                str(destination),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return Check("UNKNOWN", "clone unavailable")
    if completed.returncode != 0:
        return Check("UNKNOWN", "clone unavailable")
    try:
        run_git(destination, "rev-parse", "--verify", "refs/remotes/origin/main")
    except AuditError:
        return Check("PENDING", "no main branch (empty or non-main default)")
    try:
        run_git(destination, "checkout", "--quiet", "--detach", "refs/remotes/origin/main")
    except AuditError:
        return Check("FAIL", "main branch cannot be checked out")
    return None


def format_report_line(result: RepoResult, audit_date: str) -> str:
    details = "; ".join(result.details)
    return "- %s | %s | %s | %s" % (
        audit_date,
        result.repo,
        result.status,
        details,
    )


def _load_json(path: pathlib.Path, label: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AuditError("could not load %s: %s" % (label, error))
    if not isinstance(value, dict):
        raise AuditError("%s must contain a JSON object" % label)
    return value


def _repositories(args, registry: dict) -> Tuple[Optional[List[str]], Optional[str]]:
    if args.repo:
        invalid = [repo for repo in args.repo if REPOSITORY_PATH.fullmatch(repo) is None]
        if invalid:
            raise AuditError("invalid --repo value: %s" % invalid[0])
        return sorted(set(args.repo), key=str.casefold), None

    map_repo = registry.get("map_repo")
    if not isinstance(map_repo, str) or "/" not in map_repo:
        raise AuditError("registry map_repo does not identify an organization")
    org = map_repo.split("/", 1)[0]
    repos = fetch_org_repos(org, timeout=args.timeout)
    if repos is None:
        if args.require_reality:
            raise AuditError(
                "could not enumerate org:%s; --require-reality rejects this degraded run"
                % org
            )
        return None, org
    if not repos:
        raise AuditError("org:%s enumeration returned an empty universe" % org)
    return sorted(set(repos), key=str.casefold), None


def parse_args(argv: Optional[Sequence[str]] = None):
    parser = argparse.ArgumentParser(
        description=(
            "Audit repo-state status, commit identity, canonical regeneration, "
            "and latest caller conclusion."
        )
    )
    parser.add_argument(
        "--repo",
        action="append",
        help="audit one owner/repo instead of enumerating the registry organization",
    )
    parser.add_argument(
        "--registry",
        type=pathlib.Path,
        default=DEFAULT_REGISTRY,
        help="registry JSON path (default: %(default)s)",
    )
    parser.add_argument(
        "--schema",
        type=pathlib.Path,
        default=DEFAULT_SCHEMA,
        help="status schema path (default: %(default)s)",
    )
    parser.add_argument(
        "--generator",
        type=pathlib.Path,
        default=DEFAULT_GENERATOR,
        help="canonical generator from this checkout (default: %(default)s)",
    )
    parser.add_argument(
        "--require-reality",
        action="store_true",
        help="fail if the public-repository universe cannot be enumerated",
    )
    parser.add_argument(
        "--report-file",
        type=pathlib.Path,
        help="also write the dated per-repository lines to this file",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="network/clone timeout in seconds (default: %(default)s)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    try:
        registry = _load_json(args.registry, "registry")
        schema = _load_json(args.schema, "status schema")
        ensure_supported_schema(schema)
        if not args.generator.is_file():
            raise AuditError("canonical generator is missing: %s" % args.generator)
        repos, degraded_org = _repositories(args, registry)
    except AuditError as error:
        print("repo-state audit: error: %s" % error, file=sys.stderr)
        return 2

    audit_date = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    if repos is None:
        lines = [
            "- %s | org:%s | UNKNOWN | public-repository universe unavailable"
            % (audit_date, degraded_org)
        ]
        results: List[RepoResult] = []
    else:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        results = []
        with tempfile.TemporaryDirectory(prefix="repo-state-audit.") as temporary:
            temporary_root = pathlib.Path(temporary)
            for index, repo in enumerate(repos):
                checkout = temporary_root / ("repo-%03d" % index)
                clone_problem = _clone_main(repo, checkout, args.timeout)
                if clone_problem is not None:
                    results.append(
                        RepoResult(
                            repo,
                            clone_problem.status,
                            (clone_problem.detail,),
                        )
                    )
                    continue
                results.append(
                    audit_checkout(
                        repo,
                        checkout,
                        schema,
                        args.generator,
                        token,
                        args.timeout,
                    )
                )
        lines = [format_report_line(result, audit_date) for result in results]

    for line in lines:
        print(line)
    if args.report_file:
        try:
            args.report_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError as error:
            print("repo-state audit: error: could not write report: %s" % error, file=sys.stderr)
            return 2

    if any(result.status == "FAIL" for result in results):
        return 1
    if (
        args.require_reality
        and results
        and all(
            result.status == "UNKNOWN" and result.details == ("clone unavailable",)
            for result in results
        )
    ):
        print(
            "repo-state audit: error: all repositories are clone-unavailable; "
            "--require-reality rejects this unreachable universe",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
