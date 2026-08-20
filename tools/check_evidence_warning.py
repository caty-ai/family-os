#!/usr/bin/env python3
"""Warn when evidence reviews approach their expiry without blocking CI.

This detector reports review dates that need attention; it is intentionally not
the evidence freshness gate. Warnings deliberately return exit 0, and the
workflow decides whether to file or update an issue. Parse and read failures
return 2. The gate owns the 90-day validity rule, while this tool gives
maintainers time to re-review entries before that boundary.

Python 3.9+, standard library only.
"""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import re
import sys


HEADING_PATTERN = re.compile(r"^## (?P<claim_id>EV-\d{3})\b")
ROW_PATTERN = re.compile(r"^\|(?P<left>[^|]+)\|(?P<right>[^|]+)\|$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class EvidenceWarningError(Exception):
    """An evidence document cannot be safely interpreted."""


def fail(message):
    print("ERROR: %s" % message, file=sys.stderr)
    return 2


def parse_date(value, claim_id, field):
    if not DATE_PATTERN.fullmatch(value):
        raise EvidenceWarningError(
            "%s has invalid %s %r; expected YYYY-MM-DD" % (claim_id, field, value)
        )
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise EvidenceWarningError(
            "%s has invalid %s %r; expected YYYY-MM-DD" % (claim_id, field, value)
        )


def headings(lines):
    result = []
    seen = set()
    for index, raw_line in enumerate(lines):
        match = HEADING_PATTERN.match(raw_line.strip())
        if not match:
            continue
        claim_id = match.group("claim_id")
        if claim_id in seen:
            raise EvidenceWarningError("duplicate evidence heading for %s" % claim_id)
        seen.add(claim_id)
        result.append((index, claim_id))
    if not result:
        raise EvidenceWarningError("parsed 0 evidence entries")
    return result


def reviewed_value(lines, start, end, claim_id):
    values = []
    for raw_line in lines[start:end]:
        match = ROW_PATTERN.match(raw_line.strip())
        if not match:
            continue
        if match.group("left").strip() == "last-reviewed":
            values.append(match.group("right").strip())
    if not values:
        raise EvidenceWarningError("%s is missing last-reviewed" % claim_id)
    if len(values) != 1:
        raise EvidenceWarningError("%s has duplicate last-reviewed rows" % claim_id)
    return values[0]


def parse_entries(document):
    lines = document.splitlines()
    section_headings = headings(lines)
    entries = []
    for position, (start, claim_id) in enumerate(section_headings):
        end = (
            section_headings[position + 1][0]
            if position + 1 < len(section_headings)
            else len(lines)
        )
        entries.append((claim_id, reviewed_value(lines, start + 1, end, claim_id)))
    return entries


def warnings(entries, threshold_days, as_of):
    result = []
    for claim_id, raw_reviewed in entries:
        reviewed = parse_date(raw_reviewed, claim_id, "last-reviewed")
        age_days = (as_of - reviewed).days
        if age_days < 0:
            raise EvidenceWarningError(
                "%s has future last-reviewed %s relative to %s"
                % (claim_id, reviewed.isoformat(), as_of.isoformat())
            )
        if age_days >= threshold_days:
            result.append((claim_id, reviewed.isoformat(), age_days))
    return result


def make_parser():
    parser = argparse.ArgumentParser(
        description="warn when docs/evidence.md review dates approach expiry"
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=Path("docs/evidence.md"),
        help="evidence document (default: docs/evidence.md)",
    )
    parser.add_argument(
        "--threshold-days",
        type=int,
        default=60,
        help="warn at this review age or older (default: 60)",
    )
    parser.add_argument(
        "--as-of",
        default=None,
        help="UTC comparison date as YYYY-MM-DD (default: today)",
    )
    parser.add_argument(
        "--format",
        choices=("human", "github"),
        default="human",
        help="output format (default: human)",
    )
    return parser


def main(argv=None):
    args = make_parser().parse_args(argv)
    if args.threshold_days < 0:
        return fail("--threshold-days must be non-negative")

    try:
        as_of = (
            parse_date(args.as_of, "--as-of", "date")
            if args.as_of is not None
            else datetime.now(timezone.utc).date()
        )
        document = args.evidence.read_text(encoding="utf-8")
        entries = parse_entries(document)
        found = warnings(entries, args.threshold_days, as_of)
    except (EvidenceWarningError, OSError, UnicodeError) as error:
        return fail(str(error))

    if not found:
        print(
            "OK: no evidence entries older than %d days (checked %d entries)"
            % (args.threshold_days, len(entries))
        )
        return 0

    for claim_id, reviewed, age_days in found:
        if args.format == "github":
            print("WARN\t%s\t%s\t%d" % (claim_id, reviewed, age_days))
        else:
            print(
                "WARN %s: last-reviewed %s is %d days old"
                % (claim_id, reviewed, age_days)
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
