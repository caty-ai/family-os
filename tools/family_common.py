#!/usr/bin/env python3
"""Shared helpers for Family OS registry-backed Markdown tooling.

Python 3.9+, standard library only.
"""

from __future__ import annotations

import pathlib
import re
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple


MARKER_TOKEN = "family:generated"
MARKER_PATTERN = (
    r"^<!-- family:generated:(?P<block>[a-z0-9][a-z0-9-]*):"
    r"(?P<edge>start|end) -->$"
)
MARKER = re.compile(MARKER_PATTERN)

LANG_TAG = re.compile(r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$")
README_NAME = re.compile(r"^README(?:\.(?P<tag>[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*))?\.md$")
FENCE_LINE = re.compile(r"^[ \t]*(?P<char>`|~){3,}.*$")
FENCE_PREFIX = re.compile(r"^[ \t]*(?P<char>`|~)(?P<rest>(?P=char){2,})(?P<tail>.*)$")
FENCE_CLOSE = re.compile(r"^[ \t]*(?P<char>`|~){3,}[ \t]*$")


class FamilyCommonError(Exception):
    """A shared tooling error."""


class MarkerError(FamilyCommonError):
    """A generated-marker parsing error with a source line number."""

    def __init__(self, line_number: int, message: str) -> None:
        super().__init__(message)
        self.line_number = line_number


def line_ending(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    raise FamilyCommonError("a start marker must occupy its own line")


def _normalise_primary(tag: str) -> str:
    if not LANG_TAG.fullmatch(tag):
        raise FamilyCommonError("undeclarable language tag '%s'" % tag)
    primary = tag.split("-", 1)[0].lower()
    if not re.fullmatch(r"[A-Za-z0-9]+", primary):
        raise FamilyCommonError("undeclarable language tag '%s'" % tag)
    return primary


def language_of(
    path: pathlib.Path,
    languages: Sequence[str],
    overrides: Optional[Dict[str, str]] = None,
) -> str:
    overrides = overrides or {}
    if path.name in overrides:
        override = overrides[path.name]
        if override not in languages:
            raise FamilyCommonError(
                "%s: override declares unknown language '%s'" % (path.name, override)
            )
        return override

    match = README_NAME.fullmatch(path.name)
    if not match:
        raise FamilyCommonError(
            "%s: filename does not declare a supported Markdown language" % path.name
        )

    tag = match.group("tag")
    if tag is None:
        lang = "en"
    else:
        lang = _normalise_primary(tag)
    if lang not in languages:
        if tag is None:
            raise FamilyCommonError(
                "%s: default language 'en' is not declared in registry languages"
                % path.name
            )
        raise FamilyCommonError(
            "%s: language tag '%s' resolves to unknown primary '%s'"
            % (path.name, tag, lang)
        )
    return lang


def _fence_info(line: str) -> Optional[Tuple[str, int, bool]]:
    if not FENCE_LINE.match(line):
        return None
    match = FENCE_PREFIX.match(line)
    if match is None:
        return None
    char = match.group("char")
    run_length = 1 + len(match.group("rest"))
    closing = FENCE_CLOSE.fullmatch(line) is not None
    return char, run_length, closing


def iter_marker_lines(
    text: str, live_ids: Iterable[str]
) -> Iterator[Tuple[int, str, str]]:
    live_ids = set(live_ids)
    fence_char = None
    fence_len = 0

    for index, raw_line in enumerate(text.splitlines(keepends=True)):
        line = raw_line.rstrip("\r\n")
        if MARKER_TOKEN in line.lower():
            match = MARKER.fullmatch(line)
            if match is None:
                raise MarkerError(
                    index + 1, "malformed generated marker: %s" % line
                )
            block = match.group("block")
            edge = match.group("edge")
            if fence_char is not None:
                if block in live_ids:
                    raise MarkerError(
                        index + 1,
                        "block-id '%s' may not appear inside a fenced code block"
                        % block
                    )
            else:
                yield index, block, edge

        fence = _fence_info(line)
        if fence is None:
            continue
        char, length, closing = fence
        if fence_char is None:
            fence_char = char
            fence_len = length
            continue
        if closing and char == fence_char and length >= fence_len:
            fence_char = None
            fence_len = 0


class DegradedReality:
    """Collect skip notes and emit the shared degraded failure wording."""

    def __init__(self) -> None:
        self._notes: List[str] = []
        self._units: Set[str] = set()

    def skip(self, unit: str, note: str) -> None:
        self._units.add(unit)
        self._notes.append(note)

    def notes(self) -> List[str]:
        return list(self._notes)

    def skipped(self) -> int:
        return len(self._units)

    def finalize(
        self, failures: List[str], require_reality: bool, noun: str = "modules"
    ) -> int:
        skipped = self.skipped()
        if require_reality and skipped:
            failures.append(
                "degraded: could not verify %d %s; --require-reality rejects "
                "this degraded run, not a confirmed registry mismatch" % (skipped, noun)
            )
        return skipped
