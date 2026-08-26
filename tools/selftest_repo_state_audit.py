#!/usr/bin/env python3
"""Local, network-free self-test for repo_state_audit.py."""

from __future__ import annotations

import datetime
import io
import json
import os
import pathlib
import subprocess
import tempfile
import unittest
import urllib.parse
from types import SimpleNamespace
from unittest import mock

import repo_state_audit as audit


class RepoFixture:
    def __init__(self, root: pathlib.Path) -> None:
        self.root = root
        subprocess.run(
            ["git", "init", "-q", "-b", "main", str(root)],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(root), "config", "user.name", "Fixture Author"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(root), "config", "user.email", "fixture@localhost"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(root), "config", "core.hooksPath", "/dev/null"],
            check=True,
        )
        self.counter = 0

    def commit(self, message: str, committer: str = "Fixture Author") -> str:
        self.counter += 1
        (self.root / "content.txt").write_text(
            "fixture %d\n" % self.counter, encoding="utf-8"
        )
        subprocess.run(
            ["git", "-C", str(self.root), "add", "content.txt"], check=True
        )
        return self.commit_staged(message, committer)

    def commit_staged(self, message: str, committer: str) -> str:
        environment = os.environ.copy()
        environment.update(
            {
                "GIT_AUTHOR_NAME": committer,
                "GIT_AUTHOR_EMAIL": "fixture@localhost",
                "GIT_COMMITTER_NAME": committer,
                "GIT_COMMITTER_EMAIL": "fixture@localhost",
            }
        )
        subprocess.run(
            ["git", "-C", str(self.root), "commit", "-q", "-m", message],
            check=True,
            env=environment,
        )
        return audit.run_git(self.root, "rev-parse", "HEAD")


class RepoStateAuditSelfTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="selftest-repo-state-audit.")
        self.root = pathlib.Path(self.temporary.name) / "repo"
        self.fixture = RepoFixture(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _check_actions_with_runs(
        self,
        workflow_runs,
        *,
        runs_total_count=None,
        workflows=None,
        default_branch="main",
        expected_workflow_id=1,
    ):
        active = {
            "total_count": len(workflows) if workflows is not None else 1,
            "workflows": (
                workflows
                if workflows is not None
                else [
                    {
                        "id": 1,
                        "name": "repository state",
                        "path": ".github/workflows/repo-state.yml",
                        "state": "active",
                    }
                ]
            ),
        }
        runs = {
            "total_count": (
                len(workflow_runs)
                if runs_total_count is None
                else runs_total_count
            ),
            "workflow_runs": workflow_runs,
        }
        with mock.patch.object(
            audit, "_http_json", side_effect=[active, runs]
        ) as http_json:
            result = audit.check_actions(
                "fixture/repo", "fixture-token", 1, default_branch
            )
        self.assertIn("per_page=100", http_json.call_args_list[1].args[0])
        self.assertIn(
            "/actions/workflows/%d/runs" % expected_workflow_id,
            http_json.call_args_list[1].args[0],
        )
        self.assertIn(
            "branch=%s" % urllib.parse.quote(default_branch, safe=""),
            http_json.call_args_list[1].args[0],
        )
        return result

    def test_stamp_commit_parsing_and_auto_identity(self) -> None:
        content = self.fixture.commit("feat: content")
        first_stamp = self.fixture.commit(
            "chore(repo-state): %s" % content[:7], audit.BOT_COMMITTER
        )
        stamp = self.fixture.commit(
            "chore(repo-state): retry %s" % content[:7], audit.BOT_COMMITTER
        )
        parsed = audit.read_commit(self.root, stamp)
        self.assertEqual(audit.BOT_COMMITTER, parsed.committer)
        self.assertTrue(parsed.is_stamp_message)
        self.assertEqual((first_stamp,), parsed.parents)

        result = audit.classify_identity(
            self.root,
            {"stamp_mode": "auto", "describes_commit": content},
        )
        self.assertEqual("PASS", result.status)

    def test_auto_identity_rejects_wrong_ancestor_and_wrong_committer(self) -> None:
        content = self.fixture.commit("feat: content")
        self.fixture.commit("chore(repo-state): wrong", audit.BOT_COMMITTER)
        wrong_ancestor = audit.classify_identity(
            self.root,
            {"stamp_mode": "auto", "describes_commit": "0" * 40},
        )
        self.assertEqual("FAIL", wrong_ancestor.status)

        self.fixture.commit("chore(repo-state): impostor")
        wrong_committer = audit.classify_identity(
            self.root,
            {"stamp_mode": "auto", "describes_commit": content},
        )
        self.assertEqual("FAIL", wrong_committer.status)

    def test_auto_content_head_is_transient_drift(self) -> None:
        content = self.fixture.commit("feat: content")
        result = audit.classify_identity(
            self.root,
            {"stamp_mode": "auto", "describes_commit": content},
        )
        self.assertEqual("TRANSIENT", result.status)

        committed_at = audit.read_commit(self.root, "HEAD").committed_at
        overdue = audit.classify_identity(
            self.root,
            {"stamp_mode": "auto", "describes_commit": content},
            now=committed_at + datetime.timedelta(days=8),
        )
        self.assertEqual("FAIL", overdue.status)

    def test_verify_only_uses_base_head_parent_lineage(self) -> None:
        base = self.fixture.commit("feat: base")
        self.fixture.commit("feat: merged content")
        healthy = audit.classify_identity(
            self.root,
            {"stamp_mode": "verify-only", "describes_commit": base},
        )
        self.assertEqual("PASS", healthy.status)

        stale = audit.classify_identity(
            self.root,
            {"stamp_mode": "verify-only", "describes_commit": "0" * 40},
        )
        self.assertEqual("FAIL", stale.status)

    def test_missing_status_is_pending(self) -> None:
        self.fixture.commit("feat: content")
        result = audit.audit_checkout(
            "fixture/repo",
            self.root,
            {},
            pathlib.Path("unused-generator"),
            None,
            1.0,
        )
        self.assertEqual("PENDING", result.status)

    def test_nullable_agents_entry_generator_failure_is_unknown(self) -> None:
        schema = json.loads(audit.DEFAULT_SCHEMA.read_text(encoding="utf-8"))
        described = self.fixture.commit("feat: content")
        status = {
            "$schema": "https://raw.githubusercontent.com/caty-ai/family-os/main/docs/repo-state/status.schema.json",
            "schema_version": 1,
            "generator_version": "repo-state-gen v1",
            "repo": "fixture/repo",
            "stamp_mode": "auto",
            "generated_at": "2026-08-25T01:02:03Z",
            "describes_commit": described,
            "describes_commit_date": "2026-08-25T01:02:03Z",
            "branch": "main",
            "latest_tag": None,
            "latest_release_url": None,
            "agents_entry": None,
            "canonical_api": "https://api.github.com/repos/fixture/repo/commits/main",
            "canonical_raw": "https://raw.githubusercontent.com/fixture/repo/%s/status.json"
            % described,
            "freshness_contract": "SHA comparison only; dates may only ever trigger distrust. Protocol: docs/repo-state/spec.md, section 'Reader protocol'.",
        }
        self.assertEqual([], audit.validate_status(status, schema, "fixture/repo"))
        expected_block = "\n".join(audit._expected_block(status))
        (self.root / "README.md").write_text(
            "# Fixture\n\n%s\n" % expected_block,
            encoding="utf-8",
        )
        (self.root / "status.json").write_text(
            json.dumps(status, indent=2) + "\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "-C", str(self.root), "add", "README.md", "status.json"],
            check=True,
        )
        self.fixture.commit_staged(
            "chore(repo-state): %s" % described[:7], audit.BOT_COMMITTER
        )
        stub_generator = pathlib.Path(self.temporary.name) / "stub-generator.sh"
        stub_generator.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' 'neither FOR-AGENTS.md nor AGENTS.md exists' >&2\n"
            "exit 1\n",
            encoding="utf-8",
        )

        with mock.patch.object(
            audit, "check_actions", return_value=audit.Check("PASS", "caller success")
        ):
            result = audit.audit_checkout(
                "fixture/repo",
                self.root,
                schema,
                stub_generator,
                "fixture-token",
                1.0,
            )
        self.assertEqual("UNKNOWN", result.status)
        self.assertIn(
            "regeneration skipped: v0.11.0 generator cannot run without an agents entry",
            result.details,
        )
        self.assertFalse((self.root / "AGENTS.md").exists())
        self.assertFalse((self.root / "FOR-AGENTS.md").exists())

    def test_nullable_agents_entry_real_generator_is_byte_clean(self) -> None:
        schema = json.loads(audit.DEFAULT_SCHEMA.read_text(encoding="utf-8"))
        (self.root / "README.md").write_text("# Fixture\n", encoding="utf-8")
        subprocess.run(
            ["git", "-C", str(self.root), "add", "README.md"], check=True
        )
        described = self.fixture.commit("feat: content")
        environment = os.environ.copy()
        environment.update(
            {
                "REPO_STATE_NO_GH": "1",
                "REPO_STATE_REPO": "fixture/repo",
                "REPO_STATE_BRANCH": "main",
            }
        )
        subprocess.run(
            ["sh", str(audit.DEFAULT_GENERATOR), "--stamp-mode", "auto"],
            cwd=str(self.root),
            check=True,
            env=environment,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "add", "README.md", "status.json"],
            check=True,
        )
        self.fixture.commit_staged(
            "chore(repo-state): %s" % described[:7], audit.BOT_COMMITTER
        )

        with mock.patch.object(
            audit, "check_actions", return_value=audit.Check("PASS", "caller success")
        ):
            result = audit.audit_checkout(
                "fixture/repo",
                self.root,
                schema,
                audit.DEFAULT_GENERATOR,
                "fixture-token",
                1.0,
            )
        status = json.loads((self.root / "status.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", result.status)
        self.assertIn("canonical regeneration is byte-clean", result.details)
        self.assertFalse((self.root / "AGENTS.md").exists())
        self.assertFalse((self.root / "FOR-AGENTS.md").exists())
        self.assertIsNone(status["agents_entry"])

    def test_regeneration_allows_transient_managed_diff_only(self) -> None:
        (self.root / "README.md").write_text("# Fixture\n", encoding="utf-8")
        (self.root / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
        content = self.fixture.commit("feat: initial content")
        environment = os.environ.copy()
        environment.update(
            {
                "REPO_STATE_NO_GH": "1",
                "REPO_STATE_REPO": "fixture/repo",
                "REPO_STATE_BRANCH": "main",
            }
        )
        subprocess.run(
            ["sh", str(audit.DEFAULT_GENERATOR), "--stamp-mode", "auto"],
            cwd=str(self.root),
            check=True,
            env=environment,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "add", "README.md", "AGENTS.md", "status.json"],
            check=True,
        )
        self.fixture.commit_staged(
            "chore(repo-state): %s" % content[:7], audit.BOT_COMMITTER
        )
        self.fixture.commit("feat: next content")

        status = json.loads((self.root / "status.json").read_text(encoding="utf-8"))
        identity = audit.classify_identity(self.root, status)
        self.assertEqual("TRANSIENT", identity.status)
        regeneration = audit.check_regeneration(
            self.root,
            "fixture/repo",
            status,
            audit.DEFAULT_GENERATOR,
            identity,
        )
        self.assertEqual("PASS", regeneration.status)
        self.assertIn("stamp-managed regions", regeneration.detail)

        bad_generator = pathlib.Path(self.temporary.name) / "bad-generator.sh"
        bad_generator.write_text(
            "#!/bin/sh\nprintf 'unexpected\\n' >> content.txt\n",
            encoding="utf-8",
        )
        outside = audit.check_regeneration(
            self.root,
            "fixture/repo",
            status,
            bad_generator,
            identity,
        )
        self.assertEqual("FAIL", outside.status)
        self.assertIn("outside managed regions", outside.detail)

    def test_report_line_format(self) -> None:
        result = audit.RepoResult(
            "caty-ai/example",
            "PASS",
            ("auto identity invariant holds", "caller success"),
        )
        self.assertEqual(
            "- 2026-08-25 | caty-ai/example | PASS | auto identity invariant holds; caller success",
            audit.format_report_line(result, "2026-08-25"),
        )

    def test_universe_enumeration_is_fail_closed_when_required(self) -> None:
        args = SimpleNamespace(repo=None, timeout=1.0, require_reality=True)
        with mock.patch.object(audit, "fetch_org_repos", return_value=None):
            with self.assertRaises(audit.AuditError):
                audit._repositories(args, {"map_repo": "caty-ai/family-os"})

        args.require_reality = False
        with mock.patch.object(audit, "fetch_org_repos", return_value=None):
            repos, degraded_org = audit._repositories(
                args, {"map_repo": "caty-ai/family-os"}
            )
        self.assertIsNone(repos)
        self.assertEqual("caty-ai", degraded_org)

    def test_actions_api_retries_anonymously_after_token_http_error(self) -> None:
        url = "https://api.github.com/repos/fixture/repo/actions/workflows"
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{"workflows": []}'
        forbidden = audit.urllib.error.HTTPError(url, 403, "Forbidden", {}, None)
        opener = mock.MagicMock()
        opener.open.side_effect = [forbidden, response]

        with mock.patch.object(
            audit.urllib.request, "build_opener", return_value=opener
        ):
            payload = audit._http_json(url, "fixture-token", 1.0)
        forbidden.close()

        self.assertEqual({"workflows": []}, payload)
        self.assertEqual(2, opener.open.call_count)
        first_request = opener.open.call_args_list[0].args[0]
        second_request = opener.open.call_args_list[1].args[0]
        self.assertEqual(
            "Bearer fixture-token", first_request.get_header("Authorization")
        )
        self.assertIsNone(second_request.get_header("Authorization"))

    def test_actions_api_is_unknown_when_token_and_anonymous_calls_fail(self) -> None:
        url = "https://api.github.com/repos/fixture/repo/actions/workflows"
        forbidden = audit.urllib.error.HTTPError(url, 403, "Forbidden", {}, None)
        opener = mock.MagicMock()
        opener.open.side_effect = [forbidden, forbidden]

        with mock.patch.object(
            audit.urllib.request, "build_opener", return_value=opener
        ):
            result = audit.check_actions("fixture/repo", "fixture-token", 1.0, "main")
        forbidden.close()

        self.assertEqual("UNKNOWN", result.status)
        self.assertEqual("caller UNKNOWN(api-error)", result.detail)
        self.assertEqual(2, opener.open.call_count)

    def test_persistent_actions_unknown_escalates_after_freshness_window(self) -> None:
        (self.root / "status.json").write_text("{}\n", encoding="utf-8")
        now = datetime.datetime.now(datetime.timezone.utc)
        unknown = audit.Check("UNKNOWN", "no default-branch caller runs yet")
        cases = [
            ("past-window", now - datetime.timedelta(days=15), "FAIL"),
            ("within-window", now - datetime.timedelta(days=13), "UNKNOWN"),
        ]
        for label, generated_at, expected in cases:
            with self.subTest(label=label):
                status = {
                    "branch": "trunk",
                    "generated_at": generated_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                }
                with mock.patch.multiple(
                    audit,
                    _load_status=mock.DEFAULT,
                    classify_identity=mock.DEFAULT,
                    check_regeneration=mock.DEFAULT,
                    check_actions=mock.DEFAULT,
                ) as patched:
                    patched["_load_status"].return_value = (status, [])
                    patched["classify_identity"].return_value = audit.Check(
                        "PASS", "identity healthy"
                    )
                    patched["check_regeneration"].return_value = audit.Check(
                        "PASS", "regeneration healthy"
                    )
                    patched["check_actions"].return_value = unknown
                    result = audit.audit_checkout(
                        "fixture/repo",
                        self.root,
                        {},
                        pathlib.Path("unused-generator"),
                        "fixture-token",
                        1.0,
                    )
                self.assertEqual(expected, result.status)
                patched["check_actions"].assert_called_once_with(
                    "fixture/repo", "fixture-token", 1.0, "trunk"
                )

        for detail in ("caller UNKNOWN(no-token)", "caller UNKNOWN(api-error)"):
            with self.subTest(detail=detail):
                exempt = audit.Check("UNKNOWN", detail)
                self.assertIs(
                    exempt,
                    audit._escalate_actions_unknown(
                        exempt,
                        (now - datetime.timedelta(days=30)).strftime(
                            "%Y-%m-%dT%H:%M:%SZ"
                        ),
                        now=now,
                    ),
                )

        healthy = audit.Check("PASS", "latest repo-state caller conclusion is success")
        self.assertIs(
            healthy,
            audit._escalate_actions_unknown(
                healthy,
                (now - datetime.timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                now=now,
            ),
        )

    def test_clone_without_origin_main_is_pending(self) -> None:
        source = pathlib.Path(self.temporary.name) / "trunk-source"
        source_fixture = RepoFixture(source)
        source_fixture.commit("feat: trunk content")
        subprocess.run(
            ["git", "-C", str(source), "branch", "-m", "trunk"], check=True
        )
        destination = pathlib.Path(self.temporary.name) / "trunk-clone"
        real_run = subprocess.run

        def clone_fixture(command, **kwargs):
            command = list(command)
            if command[:2] == ["git", "clone"]:
                command[-2] = str(source)
            return real_run(command, **kwargs)

        with mock.patch.object(audit.subprocess, "run", side_effect=clone_fixture):
            result = audit._clone_main("fixture/repo", destination, 5.0)

        self.assertEqual(
            audit.Check("PENDING", "no main branch (empty or non-main default)"),
            result,
        )

    def test_required_all_clone_unknown_is_fail_closed_but_mixed_is_not(self) -> None:
        clone_unknown = audit.Check("UNKNOWN", "clone unavailable")
        argv = [
            "--repo",
            "fixture/one",
            "--repo",
            "fixture/two",
            "--require-reality",
        ]
        stderr = io.StringIO()
        with mock.patch.object(audit, "_clone_main", return_value=clone_unknown):
            with mock.patch.object(audit.sys, "stdout", io.StringIO()):
                with mock.patch.object(audit.sys, "stderr", stderr):
                    exit_code = audit.main(argv)
        self.assertEqual(2, exit_code)
        self.assertIn("all repositories are clone-unavailable", stderr.getvalue())

        pending = audit.RepoResult(
            "fixture/two", "PENDING", ("status.json absent (rollout not landed)",)
        )
        with mock.patch.object(
            audit, "_clone_main", side_effect=[clone_unknown, None]
        ):
            with mock.patch.object(audit, "audit_checkout", return_value=pending):
                with mock.patch.object(audit.sys, "stdout", io.StringIO()):
                    mixed_exit_code = audit.main(argv)
        self.assertEqual(0, mixed_exit_code)

        drift = audit.RepoResult("fixture/two", "FAIL", ("drift",))
        with mock.patch.object(
            audit, "_clone_main", side_effect=[clone_unknown, None]
        ):
            with mock.patch.object(audit, "audit_checkout", return_value=drift):
                with mock.patch.object(audit.sys, "stdout", io.StringIO()):
                    drift_exit_code = audit.main(argv)
        self.assertEqual(1, drift_exit_code)

    def test_actions_known_drift_fails_but_no_token_is_unknown(self) -> None:
        self.assertEqual(
            "UNKNOWN", audit.check_actions("fixture/repo", None, 1, "main").status
        )

        unparseable = {"total_count": 1, "workflows": {}}
        with mock.patch.object(audit, "_http_json", return_value=unparseable):
            self.assertEqual(
                "FAIL",
                audit.check_actions("fixture/repo", "fixture-token", 1, "main").status,
            )

        truncated = {
            "total_count": 2,
            "workflows": [
                {
                    "id": 1,
                    "name": "repository state",
                    "path": ".github/workflows/repo-state.yml",
                    "state": "active",
                }
            ],
        }
        with mock.patch.object(audit, "_http_json", return_value=truncated):
            self.assertEqual(
                "FAIL",
                audit.check_actions("fixture/repo", "fixture-token", 1, "main").status,
            )

        missing = {"total_count": 0, "workflows": []}
        with mock.patch.object(audit, "_http_json", return_value=missing):
            self.assertEqual(
                "FAIL",
                audit.check_actions("fixture/repo", "fixture-token", 1, "main").status,
            )

        disabled = {
            "total_count": 1,
            "workflows": [
                {
                    "id": 1,
                    "name": "repository state",
                    "path": ".github/workflows/repo-state.yml",
                    "state": "disabled_manually",
                }
            ],
        }
        with mock.patch.object(audit, "_http_json", return_value=disabled):
            self.assertEqual(
                "FAIL",
                audit.check_actions("fixture/repo", "fixture-token", 1, "main").status,
            )

        active = {
            "total_count": 1,
            "workflows": [
                {
                    "id": 1,
                    "name": "repository state",
                    "path": ".github/workflows/repo-state.yml",
                    "state": "active",
                }
            ],
        }
        bad_id = {
            "total_count": 1,
            "workflows": [dict(active["workflows"][0], id="not-an-integer")],
        }
        with mock.patch.object(audit, "_http_json", return_value=bad_id):
            self.assertEqual(
                "FAIL",
                audit.check_actions("fixture/repo", "fixture-token", 1, "main").status,
            )

        bad_runs = {"workflow_runs": {}}
        with mock.patch.object(audit, "_http_json", side_effect=[active, bad_runs]):
            self.assertEqual(
                "FAIL",
                audit.check_actions("fixture/repo", "fixture-token", 1, "main").status,
            )

        failed_run = {
            "workflow_runs": [{"status": "completed", "conclusion": "failure"}]
        }
        with mock.patch.object(audit, "_http_json", side_effect=[active, failed_run]):
            self.assertEqual(
                "FAIL",
                audit.check_actions("fixture/repo", "fixture-token", 1, "main").status,
            )

        with mock.patch.object(audit, "_http_json", side_effect=OSError):
            self.assertEqual(
                "UNKNOWN",
                audit.check_actions("fixture/repo", "fixture-token", 1, "main").status,
            )

    def test_actions_uses_success_behind_newest_skipped_run(self) -> None:
        result = self._check_actions_with_runs(
            [
                {"status": "completed", "conclusion": "skipped"},
                {"status": "completed", "conclusion": "success"},
            ]
        )
        self.assertEqual(
            audit.Check("PASS", "latest repo-state caller conclusion is success"),
            result,
        )

    def test_actions_uses_failure_behind_newest_skipped_run(self) -> None:
        result = self._check_actions_with_runs(
            [
                {"status": "completed", "conclusion": "skipped"},
                {"status": "completed", "conclusion": "failure"},
            ]
        )
        self.assertEqual(
            audit.Check("FAIL", "latest repo-state caller conclusion is failure"),
            result,
        )

    def test_actions_all_skipped_or_cancelled_runs_are_unknown(self) -> None:
        result = self._check_actions_with_runs(
            [
                {"status": "completed", "conclusion": "skipped"},
                {"status": "completed", "conclusion": "cancelled"},
            ]
        )
        self.assertEqual(
            audit.Check(
                "UNKNOWN",
                "only skipped/cancelled/stale/neutral caller runs in the latest page",
            ),
            result,
        )

    def test_actions_empty_run_list_is_unknown(self) -> None:
        result = self._check_actions_with_runs([])
        self.assertEqual(
            audit.Check("UNKNOWN", "no default-branch caller runs yet"), result
        )

    def test_actions_reports_truncated_runs_when_terminal_verdict_is_buried(self) -> None:
        result = self._check_actions_with_runs(
            [
                {"status": "completed", "conclusion": "skipped"},
                {"status": "completed", "conclusion": "neutral"},
            ],
            runs_total_count=101,
        )
        self.assertEqual(
            audit.Check(
                "UNKNOWN", "repo-state caller runs truncated; verdict unreliable"
            ),
            result,
        )

    def test_actions_non_string_conclusion_is_unknown_instead_of_crashing(self) -> None:
        for conclusion in ([], {}):
            with self.subTest(conclusion=conclusion):
                result = self._check_actions_with_runs(
                    [{"status": "completed", "conclusion": conclusion}]
                )
                self.assertEqual(
                    audit.Check("UNKNOWN", "no terminal caller run yet"), result
                )

    def test_actions_stale_and_neutral_conclusions_are_skipped(self) -> None:
        for conclusion in ("stale", "neutral"):
            with self.subTest(conclusion=conclusion):
                result = self._check_actions_with_runs(
                    [
                        {"status": "completed", "conclusion": conclusion},
                        {"status": "completed", "conclusion": "success"},
                    ]
                )
                self.assertEqual(
                    audit.Check(
                        "PASS", "latest repo-state caller conclusion is success"
                    ),
                    result,
                )

    def test_actions_prefers_host_caller_and_keeps_standard_name(self) -> None:
        reusable = {
            "id": 1,
            "name": "repository state",
            "path": ".github/workflows/repo-state.yml",
            "state": "active",
        }
        caller = {
            "id": 2,
            "name": "repository state",
            "path": ".github/workflows/repo-state-caller.yml",
            "state": "active",
        }
        success = [{"status": "completed", "conclusion": "success"}]

        host_result = self._check_actions_with_runs(
            success,
            workflows=[reusable, caller],
            expected_workflow_id=2,
        )
        self.assertEqual("PASS", host_result.status)

        standard_result = self._check_actions_with_runs(
            success,
            workflows=[reusable],
            default_branch="release/v2",
            expected_workflow_id=1,
        )
        self.assertEqual("PASS", standard_result.status)

    def test_actions_uses_success_behind_in_progress_run(self) -> None:
        result = self._check_actions_with_runs(
            [
                {"status": "in_progress", "conclusion": None},
                {"status": "completed", "conclusion": "success"},
            ]
        )
        self.assertEqual(
            audit.Check("PASS", "latest repo-state caller conclusion is success"),
            result,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
