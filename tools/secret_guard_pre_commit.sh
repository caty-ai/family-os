#!/bin/sh
# Family secret guard — block staged secrets before commit (self-growth adoption
# claude-code-secret-guard__community, sgl trial 20260721t044422).
# Rollback: git config --global --unset core.hooksPath; rm this file.
# Versioned source of truth; ~/.config/git/hooks/pre-commit is a copy of this file.
#
# 2026-07-28: the keyword patterns now require a secret-shaped VALUE after the
# separator, not merely the keyword followed by ":" or "=". The old form matched
# any line containing `token =` or `token:`, so it blocked every tokenizer,
# lexer, and parser the family writes — alpha-loom #4 could not be committed at
# all because src/core/hook_enforcer.py is a shell tokenizer full of
# `token = tokens[index]`. Detection strength is unchanged: a bare `token =`
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
# caty-ai/family-os#156 and caty-ai/meetmate#101). Quoted runs must close with
# a quote; unquoted runs must end at line end or supported punctuation (including
# query/shell delimiters), never an opening parenthesis or another word.
# Contiguous credential literals still block, including quoted JSON keys.
# gitleaks remains the primary scanner;
# SECRET_GUARD_SKIP_GITLEAKS=1 bypasses it only for the regex selftest.
set -eu

if [ "${SECRET_GUARD_SKIP_GITLEAKS:-0}" != 1 ] && command -v gitleaks >/dev/null 2>&1; then
  gitleaks protect --staged >/dev/null
fi

# A secret-shaped value is >=16 credential-alphabet chars, with a boundary.
# Backtracking to a shorter run cannot help: the next run character is neither
# a quote nor a terminator. Calls and spaced labels therefore cannot match.
run='[A-Za-z0-9_/+-]{16,}'
quoted_value='["'"'"']'"${run}"'["'"'"']'
unquoted_value="${run}[[:space:]]*([,;)}#&|\"'\\\\]|\]|$)"
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
