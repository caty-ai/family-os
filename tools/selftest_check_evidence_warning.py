#!/usr/bin/env python3
"""Subprocess self-tests for the evidence warning detector."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile


CHECKER = Path(__file__).with_name("check_evidence_warning.py")


def evidence(*reviewed_values):
    document = "# Evidence\n"
    for index, last_reviewed in enumerate(reviewed_values, start=1):
        claim_id = "EV-%03d" % index
        document += (
            "\n## %s — fixture\n\n" % claim_id
            + "| field | value |\n"
            + "| --- | --- |\n"
            + "| claim-id | %s |\n" % claim_id
            + "| last-reviewed | %s |\n" % last_reviewed
        )
    return document


def run_checker(root, document, arguments=()):
    evidence_path = root / "docs" / "evidence.md"
    evidence_path.parent.mkdir(exist_ok=True)
    evidence_path.write_text(document, encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-B", str(CHECKER)] + list(arguments),
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def test_fresh_ok():
    with tempfile.TemporaryDirectory() as temporary:
        result = run_checker(
            Path(temporary),
            evidence("2026-08-20", "2026-08-19"),
            ("--as-of", "2026-08-20"),
        )
    check(result.returncode == 0, result.stderr)
    check(
        result.stdout == "OK: no evidence entries older than 60 days (checked 2 entries)\n",
        result.stdout,
    )


def test_age_61_github_warning():
    with tempfile.TemporaryDirectory() as temporary:
        result = run_checker(
            Path(temporary),
            evidence("2026-06-20"),
            ("--as-of", "2026-08-20", "--format", "github"),
        )
    check(result.returncode == 0, result.stderr)
    check(result.stdout == "WARN\tEV-001\t2026-06-20\t61\n", result.stdout)


def test_threshold_boundaries():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        warning = run_checker(
            root,
            evidence("2026-06-21"),
            ("--as-of", "2026-08-20", "--format", "github"),
        )
        fresh = run_checker(
            root,
            evidence("2026-06-22"),
            ("--as-of", "2026-08-20", "--format", "github"),
        )
    check(warning.returncode == 0, warning.stderr)
    check(warning.stdout == "WARN\tEV-001\t2026-06-21\t60\n", warning.stdout)
    check(fresh.returncode == 0, fresh.stderr)
    check(
        fresh.stdout == "OK: no evidence entries older than 60 days (checked 1 entries)\n",
        fresh.stdout,
    )


def test_malformed_date_fails_closed():
    with tempfile.TemporaryDirectory() as temporary:
        result = run_checker(Path(temporary), evidence("2026-02-30"))
    check(result.returncode == 2, result.returncode)
    check("EV-001" in result.stderr, result.stderr)


def test_zero_entries_fails_closed():
    with tempfile.TemporaryDirectory() as temporary:
        result = run_checker(Path(temporary), "# Evidence\n")
    check(result.returncode == 2, result.returncode)
    check("parsed 0 evidence entries" in result.stderr, result.stderr)


def main():
    test_fresh_ok()
    test_age_61_github_warning()
    test_threshold_boundaries()
    test_malformed_date_fails_closed()
    test_zero_entries_fails_closed()
    print("selftest_check_evidence_warning: ok")


if __name__ == "__main__":
    main()
