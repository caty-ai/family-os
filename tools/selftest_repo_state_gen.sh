#!/bin/bash

set -euo pipefail

unset \
    GITHUB_REPOSITORY \
    GH_REPO \
    REPO_STATE_BRANCH \
    REPO_STATE_GH_BIN \
    REPO_STATE_NO_GH \
    REPO_STATE_REFRESH_RELEASE \
    REPO_STATE_REPO \
    REPO_STATE_STAMP_MODE

ROOT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
GENERATOR="$ROOT_DIR/tools/repo-state-gen.sh"
TEST_TMP=$(mktemp -d "${TMPDIR:-/tmp}/selftest-repo-state.XXXXXX")
REAL_GIT=$(command -v git)
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
    git -C "$repo" config user.email 'fixture@localhost'
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
        REPO_STATE_NO_GH="${REPO_STATE_NO_GH:-1}" "$GENERATOR" "$@"
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

seed_release_fields() {
    local repo=$1
    local tag=$2
    local url=$3
    jq --arg tag "$tag" --arg url "$url" \
        '.latest_tag = $tag | .latest_release_url = $url' \
        "$repo/status.json" > "$repo/status.json.tmp"
    mv "$repo/status.json.tmp" "$repo/status.json"
}

make_git_wrapper_without_describe() {
    local dir=$1
    local marker=$2
    cat > "$dir/git" <<EOF
#!/bin/bash
set -euo pipefail
if [[ "\${1-}" == describe ]]; then
    printf '%s\n' 'git describe' >> "$marker"
    exit 97
fi
exec "$REAL_GIT" "\$@"
EOF
    chmod +x "$dir/git"
}

test_determinism() {
    local repo first second describes_commit expected_generated_at
    repo=$(new_repo FOR-AGENTS.md)
    run_gen "$repo" > /dev/null
    describes_commit=$(jq -r '.describes_commit' "$repo/status.json")
    expected_generated_at=$(git -C "$repo" show -s --format=%cI "$describes_commit" | sed 's/+00:00$/Z/')
    assert_eq "$expected_generated_at" "$(jq -r '.generated_at' "$repo/status.json")" \
        'generated_at did not equal the describes_commit committer date'
    first=$(managed_digest "$repo")
    sleep 2
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

test_github_repository_precedence() {
    local repo
    repo=$(new_repo FOR-AGENTS.md)
    GITHUB_REPOSITORY=explicit/repository run_gen "$repo" > /dev/null
    assert_eq explicit/repository "$(jq -r '.repo' "$repo/status.json")" \
        'GITHUB_REPOSITORY did not override the fixture remote'
    printf '%s\n' 'GITHUB_REPOSITORY precedence: ok'
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

test_check_malformed_marker_error() {
    local repo
    repo=$(new_repo FOR-AGENTS.md)
    run_gen "$repo" > /dev/null
    printf '%s\n' '<!-- repo-state:begin (generated; do not edit) -->' >> "$repo/README.md"
    expect_fail '--check accepted malformed repo-state markers' run_gen "$repo" --check
    grep -q 'malformed repo-state markers in README.md' "$TEST_TMP/expected-failure.err" \
        || fail '--check malformed-marker error did not identify README.md'
    printf '%s\n' '--check malformed marker: red as expected'
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

test_agents_entry_conflict() {
    local repo
    repo=$(new_repo AGENTS.md)
    cp "$repo/AGENTS.md" "$repo/FOR-AGENTS.md"
    expect_fail 'generator accepted both AGENTS.md and FOR-AGENTS.md' run_gen "$repo"
    grep -q 'agents_entry is ambiguous' "$TEST_TMP/expected-failure.err" \
        || fail 'agents-entry conflict error was unclear'
    printf '%s\n' 'agents entry conflict: red as expected'
}

test_anchorless_readme_error() {
    local repo
    repo=$(new_repo FOR-AGENTS.md)
    cat > "$repo/README.zh.md" <<'EOF'
This README has no centered header.
It also has no H1 anchor.
EOF
    expect_fail 'generator accepted an anchor-less README in auto mode' run_gen "$repo"
    grep -q 'cannot insert stamp in README.zh.md' "$TEST_TMP/expected-failure.err" \
        || fail 'anchor-less README error was unclear'
    [[ ! -e "$repo/status.json" ]] || fail 'anchor-less README failure wrote status.json'
    printf '%s\n' 'anchor-less README: red as expected'
}

test_release_fields_preserved_without_refresh() {
    local repo mock_dir git_marker gh_marker before after
    repo=$(new_repo FOR-AGENTS.md)
    run_gen "$repo" > /dev/null
    seed_release_fields "$repo" 'v1.2.3' 'https://github.com/fixture/repo/releases/tag/v1.2.3'
    before=$(managed_digest "$repo")

    mock_dir=$(mktemp -d "$TEST_TMP/mock-preserve.XXXXXX")
    git_marker="$mock_dir/git-describe.log"
    gh_marker="$mock_dir/gh.log"
    make_git_wrapper_without_describe "$mock_dir" "$git_marker"
    cat > "$mock_dir/gh" <<EOF
#!/bin/bash
set -euo pipefail
printf '%s\n' 'gh called unexpectedly' >> "$gh_marker"
exit 96
EOF
    chmod +x "$mock_dir/gh"

    PATH="$mock_dir:$PATH" REPO_STATE_GH_BIN="$mock_dir/gh" REPO_STATE_NO_GH=0 run_gen "$repo" > /dev/null
    after=$(managed_digest "$repo")

    assert_eq 'v1.2.3' "$(jq -r '.latest_tag' "$repo/status.json")" 'ordinary run did not preserve latest_tag'
    assert_eq 'https://github.com/fixture/repo/releases/tag/v1.2.3' "$(jq -r '.latest_release_url' "$repo/status.json")" \
        'ordinary run did not preserve latest_release_url'
    assert_eq "$before" "$after" 'ordinary run was not byte-identical after preserving release fields'
    [[ ! -e "$git_marker" ]] || fail 'ordinary run invoked git describe'
    [[ ! -e "$gh_marker" ]] || fail 'ordinary run invoked gh'
    printf '%s\n' 'ordinary release fields: preserved without refresh'
}

test_normal_run_without_gh_on_path() {
    local repo
    repo=$(new_repo FOR-AGENTS.md)
    REPO_STATE_GH_BIN=/nonexistent/gh REPO_STATE_NO_GH=0 run_gen "$repo" > /dev/null
    run_gen "$repo" --check > /dev/null
    printf '%s\n' 'ordinary run without gh on PATH: green'
}

test_refresh_release_without_gh_on_path_fails() {
    local repo
    repo=$(new_repo FOR-AGENTS.md)
    expect_fail 'refresh-release without gh on PATH was accepted' \
        env REPO_STATE_GH_BIN=/nonexistent/gh REPO_STATE_NO_GH=0 \
        bash -lc "cd \"\$1\" && exec \"\$2\" --refresh-release" _ "$repo" "$GENERATOR"
    grep -q 'gh is required to refresh release metadata' "$TEST_TMP/expected-failure.err" \
        || fail 'refresh-release without gh on PATH did not emit a clear gh-missing error'
    [[ ! -e "$repo/status.json" ]] || fail 'refresh-release without gh on PATH wrote status.json'
    printf '%s\n' 'refresh-release without gh on PATH: red as expected'
}

test_refresh_release_flag_queries_gh() {
    local repo mock_dir git_marker gh_args
    repo=$(new_repo FOR-AGENTS.md)
    mock_dir=$(mktemp -d "$TEST_TMP/mock-refresh-flag.XXXXXX")
    git_marker="$mock_dir/git-describe.log"
    gh_args="$mock_dir/gh-args.log"
    make_git_wrapper_without_describe "$mock_dir" "$git_marker"
    cat > "$mock_dir/gh" <<EOF
#!/bin/bash
set -euo pipefail
printf '%s\n' "\$*" > "$gh_args"
if [[ "\${1-}" == api && "\${2-}" == repos/fixture/repo/releases/latest ]]; then
    printf 'v2.0.0\thttps://github.com/fixture/repo/releases/tag/v2.0.0\n'
    exit 0
fi
printf 'unexpected gh invocation: %s\n' "\$*" >&2
exit 98
EOF
    chmod +x "$mock_dir/gh"

    PATH="$mock_dir:$PATH" REPO_STATE_GH_BIN="$mock_dir/gh" REPO_STATE_NO_GH=0 run_gen "$repo" --refresh-release > /dev/null

    assert_eq 'v2.0.0' "$(jq -r '.latest_tag' "$repo/status.json")" '--refresh-release did not update latest_tag'
    assert_eq 'https://github.com/fixture/repo/releases/tag/v2.0.0' "$(jq -r '.latest_release_url' "$repo/status.json")" \
        '--refresh-release did not update latest_release_url'
    grep -q 'repos/fixture/repo/releases/latest' "$gh_args" \
        || fail '--refresh-release did not query releases/latest'
    [[ ! -e "$git_marker" ]] || fail '--refresh-release invoked git describe'
    printf '%s\n' '--refresh-release flag: ok'
}

test_refresh_release_env_queries_gh() {
    local repo mock_dir git_marker
    repo=$(new_repo FOR-AGENTS.md)
    mock_dir=$(mktemp -d "$TEST_TMP/mock-refresh-env.XXXXXX")
    git_marker="$mock_dir/git-describe.log"
    make_git_wrapper_without_describe "$mock_dir" "$git_marker"
    cat > "$mock_dir/gh" <<'EOF'
#!/bin/bash
set -euo pipefail
if [[ "${1-}" == api && "${2-}" == repos/fixture/repo/releases/latest ]]; then
    printf 'v3.0.0\thttps://github.com/fixture/repo/releases/tag/v3.0.0\n'
    exit 0
fi
printf 'unexpected gh invocation: %s\n' "$*" >&2
exit 98
EOF
    chmod +x "$mock_dir/gh"

    PATH="$mock_dir:$PATH" REPO_STATE_GH_BIN="$mock_dir/gh" REPO_STATE_NO_GH=0 REPO_STATE_REFRESH_RELEASE=1 run_gen "$repo" > /dev/null

    assert_eq 'v3.0.0' "$(jq -r '.latest_tag' "$repo/status.json")" 'REPO_STATE_REFRESH_RELEASE=1 did not update latest_tag'
    assert_eq 'https://github.com/fixture/repo/releases/tag/v3.0.0' "$(jq -r '.latest_release_url' "$repo/status.json")" \
        'REPO_STATE_REFRESH_RELEASE=1 did not update latest_release_url'
    [[ ! -e "$git_marker" ]] || fail 'REPO_STATE_REFRESH_RELEASE=1 invoked git describe'
    printf '%s\n' 'refresh-release env flag: ok'
}

test_refresh_release_404_maps_null() {
    local repo mock_dir git_marker
    repo=$(new_repo FOR-AGENTS.md)
    run_gen "$repo" > /dev/null
    seed_release_fields "$repo" 'v9.9.9' 'https://github.com/fixture/repo/releases/tag/v9.9.9'

    mock_dir=$(mktemp -d "$TEST_TMP/mock-refresh-404.XXXXXX")
    git_marker="$mock_dir/git-describe.log"
    make_git_wrapper_without_describe "$mock_dir" "$git_marker"
    cat > "$mock_dir/gh" <<'EOF'
#!/bin/bash
set -euo pipefail
printf '%s\n' 'gh: Not Found (HTTP 404)' >&2
exit 1
EOF
    chmod +x "$mock_dir/gh"

    PATH="$mock_dir:$PATH" REPO_STATE_GH_BIN="$mock_dir/gh" REPO_STATE_NO_GH=0 run_gen "$repo" --refresh-release > /dev/null

    jq -e '.latest_tag == null and .latest_release_url == null' "$repo/status.json" > /dev/null \
        || fail 'HTTP 404 did not map release fields to null'
    [[ ! -e "$git_marker" ]] || fail '404 refresh invoked git describe'
    printf '%s\n' 'refresh-release 404: null as expected'
}

test_refresh_release_transport_error_is_fatal() {
    local repo mock_dir before after
    repo=$(new_repo FOR-AGENTS.md)
    mock_dir=$(mktemp -d "$TEST_TMP/mock-refresh-transport.XXXXXX")
    make_git_wrapper_without_describe "$mock_dir" "$mock_dir/git-describe.log"
    cat > "$mock_dir/gh" <<'EOF'
#!/bin/bash
set -euo pipefail
printf '%s\n' 'Get "https://api.github.com/repos/fixture/repo/releases/latest": dial tcp: lookup api.github.com: no such host' >&2
exit 1
EOF
    chmod +x "$mock_dir/gh"

    before=$(shasum -a 256 "$repo/README.md" | awk '{print $1}')
    expect_fail 'transport failure during release refresh was accepted' \
        env PATH="$mock_dir:$PATH" REPO_STATE_GH_BIN="$mock_dir/gh" REPO_STATE_NO_GH=0 \
        bash -lc "cd \"\$1\" && exec \"\$2\" --refresh-release" _ "$repo" "$GENERATOR"
    after=$(shasum -a 256 "$repo/README.md" | awk '{print $1}')
    assert_eq "$before" "$after" 'transport refresh failure modified README.md'
    [[ ! -e "$repo/status.json" ]] || fail 'transport refresh failure wrote status.json'
    grep -q 'could not refresh latest release metadata' "$TEST_TMP/expected-failure.err" \
        || fail 'transport refresh failure did not emit a clear fatal error'
    printf '%s\n' 'refresh-release transport failure: red as expected'
}

test_refresh_release_http_error_is_fatal() {
    local repo mock_dir
    repo=$(new_repo FOR-AGENTS.md)
    mock_dir=$(mktemp -d "$TEST_TMP/mock-refresh-http.XXXXXX")
    make_git_wrapper_without_describe "$mock_dir" "$mock_dir/git-describe.log"
    cat > "$mock_dir/gh" <<'EOF'
#!/bin/bash
set -euo pipefail
printf '%s\n' 'gh: Internal Server Error (HTTP 500)' >&2
exit 1
EOF
    chmod +x "$mock_dir/gh"

    expect_fail 'HTTP 500 during release refresh was accepted' \
        env PATH="$mock_dir:$PATH" REPO_STATE_GH_BIN="$mock_dir/gh" REPO_STATE_NO_GH=0 \
        bash -lc "cd \"\$1\" && exec \"\$2\" --refresh-release" _ "$repo" "$GENERATOR"
    [[ ! -e "$repo/status.json" ]] || fail 'HTTP 500 refresh failure wrote status.json'
    grep -q 'could not refresh latest release metadata' "$TEST_TMP/expected-failure.err" \
        || fail 'HTTP 500 refresh failure did not emit a clear fatal error'
    printf '%s\n' 'refresh-release HTTP failure: red as expected'
}

test_freshness_contract_literal_alignment() {
    local expected
    expected="SHA comparison only; dates may only ever trigger distrust. Protocol: docs/repo-state/spec.md, section 'Reader protocol'."
    grep -Fq "$expected" "$GENERATOR" || fail 'generator freshness_contract literal drifted'
    grep -Fq "$expected" "$ROOT_DIR/docs/repo-state/status.schema.json" \
        || fail 'status schema freshness_contract literal drifted'
    grep -Fq "$expected" "$ROOT_DIR/docs/repo-state/spec.md" \
        || fail 'spec freshness_contract literal drifted'
    printf '%s\n' 'freshness contract literal: aligned'
}

test_repo_state_docs_citations() {
    if grep -R -nE '§2\.3|§2\.6' \
        "$ROOT_DIR/docs/repo-state" "$GENERATOR" > "$TEST_TMP/stale-citations.out"; then
        cat "$TEST_TMP/stale-citations.out" >&2
        fail 'stale repo-state section citations remain'
    fi
    printf '%s\n' 'repo-state citations: clean'
}

test_determinism
test_marker_idempotency
test_chained_stamp_walk
test_four_locale_set
test_agents_resolution
test_github_repository_precedence
test_agents_entry_conflict
test_anchorless_readme_error
test_malformed_marker_error
test_check_malformed_marker_error
test_check_markerless_readme
test_check_cross_file_mismatch
test_check_invalid_status
test_check_missing_status
test_check_healthy
test_verify_only_mode
test_release_fields_preserved_without_refresh
test_normal_run_without_gh_on_path
test_refresh_release_without_gh_on_path_fails
test_refresh_release_flag_queries_gh
test_refresh_release_env_queries_gh
test_refresh_release_404_maps_null
test_refresh_release_transport_error_is_fatal
test_refresh_release_http_error_is_fatal
test_freshness_contract_literal_alignment
test_repo_state_docs_citations

printf '%s\n' 'selftest_repo_state_gen: ok'
