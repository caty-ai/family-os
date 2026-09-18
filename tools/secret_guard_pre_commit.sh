#!/bin/sh
# Family secret guard — block staged secrets before commit (self-growth adoption
# claude-code-secret-guard__community, sgl trial 20260721t044422).
# Rollback: git config --global --unset core.hooksPath; rm this file.
# Versioned source of truth; ~/.config/git/hooks/pre-commit is a copy of this file.
#
# 2026-07-28: the keyword patterns now require a secret-shaped VALUE after the
# separator, not merely the keyword followed by ":" or "=". The old form matched
# any line containing `token =` or `token:`, so it blocked every tokenizer,
# lexer, and parser the family writes — a private shell tokenizer full of
# `token = tokens[index]` could not be committed at all. Detection strength is
# unchanged: a bare `token =`
# with no literal after it was never evidence of a secret, and gitleaks above
# remains the primary scanner.
#
# 2026-08-31 (owner-approved, session 2ae6e680): merge commits scan only lines
# novel to BOTH parents. The old form re-scanned the entire incoming side of a
# take-in merge, so already-published upstream content (meetmate main:
# `apiKey:` followed by
# `getEffectiveValue("elevenlabs_api_key")`, fixture
# "eleven-preview-key") blocked every integration merge — content already on
# the public remote cannot be protected by blocking a local merge. Non-merge
# commits are scanned exactly as before; conflict resolutions and evil-merge
# lines are novel to both parents and remain fully scanned. gitleaks still
# runs on the full staged tree either way.
#
# 2026-09-17: terminate keyword values to exclude long identifier/call
# expressions and human-readable quoted labels containing spaces (see
# caty-ai/family-os#156 and caty-ai/meetmate#101). A quoted value is a run followed
# by anything but whitespace up to the closing quote or end of line; unquoted runs
# end at line end or are terminated by any non-run character other than `(`.
# Contiguous credential literals still block, including quoted JSON keys.
# Quoted JSON keys now match, so space-free placeholder values block; write a
# spaced label or use --no-verify with an audit note, as before.
# Chaining activated 2026-09-18, see below.
# gitleaks remains the primary scanner;
# SECRET_GUARD_SKIP_GITLEAKS=1 is intended for the regex selftest only; nothing else should set it.
#
# 2026-09-18 (caty-ai/family-os#180): resolve the repository's own hook via
# `git rev-parse --git-common-dir`; linked worktrees share <main>/.git/hooks.
# Previously --git-path hooks/ returned this very file under a global
# core.hooksPath on git 2.48, making chaining a no-op. This is a behaviour
# change: repo-local pre-commit hooks (lint, format, own secret checks) run
# after the guard passes; blocked commits never reach them. A repo-local
# hook must not invoke the global hook (e.g. a stale guard copy);
# SECRET_GUARD_CHAINED scopes loop prevention to the same repository.
set -eu
this_common=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null || git rev-parse --git-common-dir 2>/dev/null || true)
case "$this_common" in ''|/*) ;; *) this_common=$PWD/$this_common ;; esac
# Scope re-entry to one repository: another repo committed by a chained hook
# still gets scanned. Only a second hop into the same repo skips the index
# scan that the first hop already passed, preventing a chaining loop.
if [ -n "${SECRET_GUARD_CHAINED:-}" ] && [ -d "$SECRET_GUARD_CHAINED" ] && [ "$SECRET_GUARD_CHAINED" -ef "$this_common" ]; then
  exit 0
fi

if [ "${SECRET_GUARD_SKIP_GITLEAKS:-0}" != 1 ] && command -v gitleaks >/dev/null 2>&1; then
  gitleaks protect --staged >/dev/null
fi

# A secret-shaped value is >=16 credential-alphabet chars, with a boundary.
# Unquoted runs are terminated by any non-run character other than `(`, or EOL.
# Backtracking cannot help: a remaining run character is not a terminator.
# A quoted value is a run followed by anything but whitespace up to the closing quote or end of line.
# This excludes spaced labels while allowing punctuation and padding inside quotes.
run='[A-Za-z0-9_/+-]{16,}'
quoted_value='["'"'"']'"${run}[^[:space:]]*"'(["'"'"']|$)'
unquoted_value="${run}([^A-Za-z0-9_/+(-]|$)"
keyword_api='[Aa][Pp][Ii][_-]?[Kk][Ee][Yy]'
keyword_token='[Tt][Oo][Kk][Ee][Nn]'
sep='[[:space:]]*[:=][[:space:]]*'
# Permit the closing quote of a JSON key before the unchanged separator.
key_quote='["'"'"']?'
pattern="^\+.*(AKIA[0-9A-Z]{16}\
|-----BEGIN [A-Z ]*PRIVATE KEY-----\
|${keyword_api}${key_quote}${sep}(${quoted_value}|${unquoted_value})\
|${keyword_token}${key_quote}${sep}(${quoted_value}|${unquoted_value}))"

git_dir=$(git rev-parse --git-dir)
if [ -f "$git_dir/MERGE_HEAD" ]; then
  # Merge commit: a line is scanned only if it is an addition relative to BOTH
  # parents (HEAD and MERGE_HEAD). Lines inherited from either parent are
  # already committed history; blocking here cannot un-publish them.
  tmp_head=$(mktemp) tmp_merge=$(mktemp)
  trap 'rm -f "$tmp_head" "$tmp_merge"' EXIT
  git diff --cached --no-ext-diff --unified=0 -- . | grep '^\+' | grep -v '^+++' | sort -u > "$tmp_head" || true
  git diff --cached --no-ext-diff --unified=0 MERGE_HEAD -- . | grep '^\+' | grep -v '^+++' | sort -u > "$tmp_merge" || true
  if comm -12 "$tmp_head" "$tmp_merge" | grep -Eq "$pattern"; then
    printf 'Secret guard: novel merge content matches a common secret pattern. Commit blocked.\n' >&2
    exit 1
  fi
else
  if git diff --cached --no-ext-diff --unified=0 -- . | grep -Eq "$pattern"; then
    printf 'Secret guard: staged content matches a common secret pattern. Commit blocked.\n' >&2
    exit 1
  fi
fi

# Chain to a repo-local pre-commit hook if one exists (global hooksPath shadows it).
# Compare paths and file identity to skip the same hook.
common_dir=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null || git rev-parse --git-common-dir 2>/dev/null || true)
case "$common_dir" in ''|/*) ;; *) common_dir=$PWD/$common_dir ;; esac
if [ -n "$common_dir" ]; then
  repo_hook="$common_dir/hooks/pre-commit"
  if [ -f "$repo_hook" ] && [ -x "$repo_hook" ] && [ "$repo_hook" != "$0" ] && ! [ "$repo_hook" -ef "$0" ]; then
    # exec bypasses the EXIT trap; explicitly remove merge temps first.
    if [ -n "${tmp_head:-}" ]; then rm -f "$tmp_head" "${tmp_merge:-}"; fi
    export SECRET_GUARD_CHAINED="$common_dir"
    exec "$repo_hook" "$@"
  fi
fi
