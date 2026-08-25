#!/bin/bash

set -euo pipefail

ROOT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
GENERATOR="$ROOT_DIR/tools/repo-state-gen.sh"
TEST_TMP=$(mktemp -d "${TMPDIR:-/tmp}/selftest-repo-state.XXXXXX")
trap 'rm -rf "$TEST_TMP"' EXIT

fail() {
    printf 'selftest_repo_state_gen: FAIL: %s\n' "$*" >&2
    exit 1
}

assert_eq() {
    local expected=$1
    local actual=$2
    local message=$3
    [[ "$expected" == "$actual" ]] || fail "$message (expected=$expected actual=$actual)"
}

new_repo() {
    local agents_file=$1
    local repo
    repo=$(mktemp -d "$TEST_TMP/repo.XXXXXX")
    git -C "$repo" init -q -b main
    git -C "$repo" config user.name 'Fixture Author'
    git -C "$repo" config user.email 'fixture@example.invalid'
    git -C "$repo" remote add origin https://github.com/fixture/repo.git

    cat > "$repo/README.md" <<'EOF'
<div align="center">
# Fixture
</div>

English introduction.
EOF
    cat > "$repo/README.ja.md" <<'EOF'
# Fixture JA

Japanese introduction.
EOF
    cat > "$repo/README.zh.md" <<'EOF'
# Fixture ZH

Chinese introduction.
EOF
    cat > "$repo/README.th.md" <<'EOF'
# Fixture TH

Thai introduction.
EOF
    cat > "$repo/$agents_file" <<'EOF'
# Agent guide

Route: read the repository guide first.
EOF

    git -C "$repo" add .
    GIT_AUTHOR_DATE=2026-08-25T01:02:03Z \
    GIT_COMMITTER_DATE=2026-08-25T01:02:03Z \
        git -C "$repo" commit -q -m 'feat: fixture content'
    printf '%s\n' "$repo"
}

run_gen() {
    local repo=$1
    shift
    (
        cd "$repo"
        REPO_STATE_NO_GH=1 "$GENERATOR" "$@"
    )
}

expect_fail() {
    local message=$1
    shift
    if "$@" > "$TEST_TMP/expected-failure.out" 2> "$TEST_TMP/expected-failure.err"; then
        fail "$message"
    fi
    [[ -s "$TEST_TMP/expected-failure.err" ]] || fail "$message did not emit a clear error"
}

managed_digest() {
    local repo=$1
    (
        cd "$repo"
        find . -maxdepth 1 -type f \( -name 'README*.md' -o -name 'AGENTS.md' -o -name 'FOR-AGENTS.md' -o -name 'status.json' \) -print \
            | LC_ALL=C sort \
            | while IFS= read -r file; do shasum -a 256 "$file"; done \
            | shasum -a 256 \
            | awk '{print $1}'
    )
}

test_determinism() {
    local repo first second
    repo=$(new_repo FOR-AGENTS.md)
    run_gen "$repo" > /dev/null
    first=$(managed_digest "$repo")
    run_gen "$repo" > /dev/null
    second=$(managed_digest "$repo")
    assert_eq "$first" "$second" 'two generator runs were not byte-identical'
    printf 'determinism: byte-identical (%s)\n' "$first"
}

test_marker_idempotency() {
    local repo
    repo=$(new_repo FOR-AGENTS.md)
    run_gen "$repo" > /dev/null
    git -C "$repo" add .
    GIT_AUTHOR_DATE=2026-08-25T01:03:03Z \
    GIT_COMMITTER_DATE=2026-08-25T01:03:03Z \
        git -C "$repo" commit -q -m 'chore(repo-state): fixture'
    run_gen "$repo" > /dev/null
    git -C "$repo" diff --quiet || fail 'marker replacement was not idempotent'
    printf '%s\n' 'marker idempotency: ok'
}

test_chained_stamp_walk() {
    local repo content_sha actual_sha
    repo=$(new_repo FOR-AGENTS.md)
    content_sha=$(git -C "$repo" rev-parse HEAD)
    run_gen "$repo" > /dev/null
    git -C "$repo" add .
    GIT_AUTHOR_DATE=2026-08-25T01:03:03Z \
    GIT_COMMITTER_DATE=2026-08-25T01:03:03Z \
        git -C "$repo" commit -q -m 'chore(repo-state): first'
    GIT_AUTHOR_DATE=2026-08-25T01:04:03Z \
    GIT_COMMITTER_DATE=2026-08-25T01:04:03Z \
        git -C "$repo" commit -q --allow-empty -m 'chore(repo-state): second'
    run_gen "$repo" > /dev/null
    actual_sha=$(jq -r '.describes_commit' "$repo/status.json")
    assert_eq "$content_sha" "$actual_sha" 'describes_commit did not walk over chained stamp commits'
    assert_eq '2026-08-25T01:02:03Z' "$(jq -r '.generated_at' "$repo/status.json")" 'generated_at was not the content commit date'
    printf '%s\n' 'chained stamp walk: ok'
}

test_four_locale_set() {
    local repo file count
    repo=$(new_repo FOR-AGENTS.md)
    run_gen "$repo" > /dev/null
    count=0
    for file in README.md README.ja.md README.zh.md README.th.md; do
        [[ $(grep -c '<!-- repo-state:begin' "$repo/$file") -eq 1 ]] \
            || fail "$file was not stamped exactly once"
        count=$((count + 1))
    done
    assert_eq 4 "$count" 'four-locale README set was incomplete'
    assert_eq 1 "$(awk '/<\/div>/{close_line=NR} /repo-state:begin/{print NR-close_line; exit}' "$repo/README.md")" 'centered README stamp position changed'
    printf '%s\n' 'four-locale README set: ok'
}

test_agents_resolution() {
    local repo
    repo=$(new_repo AGENTS.md)
    run_gen "$repo" > /dev/null
    assert_eq AGENTS.md "$(jq -r '.agents_entry' "$repo/status.json")" 'AGENTS.md was not resolved'
    [[ -f "$repo/AGENTS.md" && ! -e "$repo/FOR-AGENTS.md" ]] || fail 'AGENTS.md fixture was altered incorrectly'

    repo=$(new_repo FOR-AGENTS.md)
    run_gen "$repo" > /dev/null
    assert_eq FOR-AGENTS.md "$(jq -r '.agents_entry' "$repo/status.json")" 'FOR-AGENTS.md was not resolved'
    [[ -f "$repo/FOR-AGENTS.md" && ! -e "$repo/AGENTS.md" ]] || fail 'FOR-AGENTS.md fixture was altered incorrectly'
    printf '%s\n' 'agents entry resolution: ok'
}

test_malformed_marker_error() {
    local repo before after
    repo=$(new_repo FOR-AGENTS.md)
    printf '%s\n' '<!-- repo-state:begin (generated; do not edit) -->' >> "$repo/README.md"
    before=$(shasum -a 256 "$repo/README.md" | awk '{print $1}')
    expect_fail 'begin marker without end marker was accepted' run_gen "$repo"
    after=$(shasum -a 256 "$repo/README.md" | awk '{print $1}')
    assert_eq "$before" "$after" 'malformed-marker failure modified the README'
    [[ ! -e "$repo/status.json" ]] || fail 'malformed-marker failure wrote status.json'
    printf '%s\n' 'malformed marker hard error: ok'
}

test_check_markerless_readme() {
    local repo
    repo=$(new_repo FOR-AGENTS.md)
    run_gen "$repo" > /dev/null
    cat > "$repo/README.extra.md" <<'EOF'
# Newly added locale

This file has no stamp yet.
EOF
    expect_fail '--check accepted a marker-less root README' run_gen "$repo" --check
    grep -q 'markers are missing in README.extra.md' "$TEST_TMP/expected-failure.err" \
        || fail '--check marker-less error did not identify the file'
    printf '%s\n' '--check marker-less README: red as expected'
}

test_check_cross_file_mismatch() {
    local repo
    repo=$(new_repo FOR-AGENTS.md)
    run_gen "$repo" > /dev/null
    sed 's/generation: <code>[0-9a-f][0-9a-f]*/generation: <code>0000000/' "$repo/README.ja.md" \
        > "$repo/README.ja.md.tmp"
    mv "$repo/README.ja.md.tmp" "$repo/README.ja.md"
    expect_fail '--check accepted a cross-file stamp mismatch' run_gen "$repo" --check
    grep -q 'inconsistent with status.json' "$TEST_TMP/expected-failure.err" \
        || fail '--check mismatch error was unclear'
    printf '%s\n' '--check cross-file mismatch: red as expected'
}

test_check_invalid_status() {
    local repo
    repo=$(new_repo FOR-AGENTS.md)
    run_gen "$repo" > /dev/null
    sed 's/"schema_version": 1/"schema_version": 2/' "$repo/status.json" > "$repo/status.json.tmp"
    mv "$repo/status.json.tmp" "$repo/status.json"
    expect_fail '--check accepted an invalid status.json' run_gen "$repo" --check
    grep -q 'status.json is invalid' "$TEST_TMP/expected-failure.err" \
        || fail '--check invalid-status error was unclear'
    printf '%s\n' '--check invalid status: red as expected'
}

test_check_missing_status() {
    local repo
    repo=$(new_repo FOR-AGENTS.md)
    expect_fail '--check accepted a missing status.json' run_gen "$repo" --check
    grep -q 'status.json is missing' "$TEST_TMP/expected-failure.err" \
        || fail '--check missing-status error was unclear'
    printf '%s\n' '--check missing status: red as expected'
}

test_check_healthy() {
    local repo output
    repo=$(new_repo FOR-AGENTS.md)
    run_gen "$repo" > /dev/null
    output=$(run_gen "$repo" --check)
    assert_eq 'repo-state: check ok' "$output" '--check rejected a healthy tree'
    printf '%s\n' '--check healthy tree: green'
}

test_verify_only_mode() {
    local repo
    repo=$(new_repo FOR-AGENTS.md)
    run_gen "$repo" --stamp-mode verify-only > /dev/null
    assert_eq verify-only "$(jq -r '.stamp_mode' "$repo/status.json")" 'verify-only mode was not recorded'
    run_gen "$repo" --check > /dev/null
    printf '%s\n' 'verify-only mode: ok'
}

test_determinism
test_marker_idempotency
test_chained_stamp_walk
test_four_locale_set
test_agents_resolution
test_malformed_marker_error
test_check_markerless_readme
test_check_cross_file_mismatch
test_check_invalid_status
test_check_missing_status
test_check_healthy
test_verify_only_mode

printf '%s\n' 'selftest_repo_state_gen: ok'
