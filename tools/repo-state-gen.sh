#!/bin/sh

set -eu

PROGRAM=${0##*/}
SCHEMA_URL=https://raw.githubusercontent.com/caty-ai/family-os/main/docs/repo-state/status.schema.json
GENERATOR_VERSION='repo-state-gen v1'
FRESHNESS_CONTRACT="SHA comparison only; dates may only ever trigger distrust. Protocol: docs/repo-state/spec.md, section 'Reader protocol'."
BEGIN_MARKER='<!-- repo-state:begin (generated; do not edit) -->'
END_MARKER='<!-- repo-state:end -->'

fail() {
    printf '%s: error: %s\n' "$PROGRAM" "$*" >&2
    exit 1
}

usage() {
    cat >&2 <<EOF
usage: $PROGRAM [--check] [--refresh-release] [--stamp-mode auto|verify-only]
EOF
    exit 2
}

check_only=false
stamp_mode=${REPO_STATE_STAMP_MODE:-auto}
refresh_release=${REPO_STATE_REFRESH_RELEASE:-0}
gh_bin=${REPO_STATE_GH_BIN:-gh}
case $refresh_release in
    0|1) ;;
    *) fail "REPO_STATE_REFRESH_RELEASE must be 0 or 1" ;;
esac
while [ "$#" -gt 0 ]; do
    case $1 in
        --check)
            check_only=true
            ;;
        --refresh-release)
            refresh_release=1
            ;;
        --stamp-mode)
            [ "$#" -ge 2 ] || usage
            stamp_mode=$2
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            usage
            ;;
    esac
    shift
done

case $stamp_mode in
    auto|verify-only) ;;
    *) fail "stamp mode must be auto or verify-only" ;;
esac

command -v git >/dev/null 2>&1 || fail "git is required"
repo_root=$(git rev-parse --show-toplevel 2>/dev/null) || fail "not inside a git repository"
cd "$repo_root"

tmp_root=$(mktemp -d "${TMPDIR:-/tmp}/repo-state-gen.XXXXXX") || fail "could not create temporary directory"
trap 'rm -rf "$tmp_root"' 0 HUP INT TERM

resolve_agents_entry() {
    if [ -f FOR-AGENTS.md ] && [ -f AGENTS.md ]; then
        fail "both FOR-AGENTS.md and AGENTS.md exist; agents_entry is ambiguous"
    elif [ -f FOR-AGENTS.md ]; then
        printf '%s\n' FOR-AGENTS.md
    elif [ -f AGENTS.md ]; then
        printf '%s\n' AGENTS.md
    else
        :
    fi
}

agents_entry=$(resolve_agents_entry)
for readme_file in README*.md; do
    [ -f "$readme_file" ] || continue
    printf '%s\n' "$readme_file"
done | LC_ALL=C sort > "$tmp_root/readmes"
[ -s "$tmp_root/readmes" ] || fail "no root README*.md files found"
cp "$tmp_root/readmes" "$tmp_root/targets"
if [ -n "$agents_entry" ]; then
    printf '%s\n' "$agents_entry" >> "$tmp_root/targets"
fi

marker_state() {
    awk '
        index($0, "<!-- repo-state:begin") {
            begins++
            if (!first_begin) first_begin = NR
        }
        index($0, "<!-- repo-state:end") {
            ends++
            if (!first_end) first_end = NR
        }
        END {
            if (begins == 0 && ends == 0) {
                print "absent"
                exit 0
            }
            if (begins == 1 && ends == 1 && first_begin < first_end) {
                print "present"
                exit 0
            }
            exit 1
        }
    ' "$1"
}

centered_div_anchor_exists() {
    awk '
        {
            lower = tolower($0)
            if (index(lower, "<div") &&
                (index(lower, "align=\"center\"") || index(lower, "align='\''center'\''"))) {
                centered = 1
            }
            if (centered && index(lower, "</div>")) {
                closed = 1
                exit
            }
        }
        END { exit !closed }
    ' "$1"
}

h1_anchor_exists() {
    awk '/^#[[:space:]]+[^#]/ { found = 1; exit } END { exit !found }' "$1"
}

while IFS= read -r file; do
    [ -f "$file" ] || fail "stamped file is missing: $file"
    if ! state=$(marker_state "$file"); then
        fail "malformed repo-state markers in $file"
    fi
    if [ "$check_only" = false ] && [ "$state" = absent ]; then
        if [ "$file" = "$agents_entry" ]; then
            h1_anchor_exists "$file" || fail "cannot insert stamp in $file: H1 not found"
        elif ! centered_div_anchor_exists "$file" && ! h1_anchor_exists "$file"; then
            fail "cannot insert stamp in $file: centered header and H1 not found"
        fi
    fi
done < "$tmp_root/targets"

make_block() {
    block_short_sha=$1
    block_time=$2
    block_api=$3
    cat > "$4" <<EOF
$BEGIN_MARKER
<p align="center"><sub>generation: <code>$block_short_sha</code> ($block_time) · verify: <a href="$block_api">API HEAD</a> · <a href="./status.json">status.json</a></sub></p>
$END_MARKER
EOF
}

validate_status() {
    [ -f status.json ] || fail "status.json is missing"
    status_size=$(wc -c < status.json | tr -d '[:space:]')
    [ "$status_size" -le 2048 ] || fail "status.json exceeds 2 KiB"
    command -v jq >/dev/null 2>&1 || fail "jq is required for --check"

    if ! jq -e \
        --arg schema "$SCHEMA_URL" \
        --arg generator "$GENERATOR_VERSION" \
        --arg freshness "$FRESHNESS_CONTRACT" '
        type == "object" and
        ([keys[]] - [
          "$schema", "schema_version", "generator_version", "repo", "stamp_mode",
          "generated_at", "describes_commit", "describes_commit_date", "branch",
          "latest_tag", "latest_release_url", "agents_entry", "canonical_api",
          "canonical_raw", "freshness_contract"
        ] | length == 0) and
        (has("$schema") and has("schema_version") and has("generator_version") and
         has("repo") and has("stamp_mode") and has("generated_at") and
         has("describes_commit") and has("describes_commit_date") and has("branch") and
         has("agents_entry") and has("canonical_api") and has("canonical_raw") and
         has("freshness_contract")) and
        .["$schema"] == $schema and
        .schema_version == 1 and
        .generator_version == $generator and
        (.repo | type == "string" and test("^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")) and
        (.stamp_mode == "auto" or .stamp_mode == "verify-only") and
        (.generated_at | type == "string" and test("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$") and
          (try (fromdateiso8601 | type == "number") catch false)) and
        (.describes_commit | type == "string" and test("^[0-9a-f]{40}$")) and
        (.describes_commit_date | type == "string" and test("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$") and
          (try (fromdateiso8601 | type == "number") catch false)) and
        .generated_at == .describes_commit_date and
        (.branch | type == "string" and length > 0) and
        ((has("latest_tag") | not) or .latest_tag == null or
          (.latest_tag | type == "string" and length > 0)) and
        ((has("latest_release_url") | not) or .latest_release_url == null or
          (.latest_release_url | type == "string" and test("^https://github[.]com/"))) and
        (.agents_entry == "FOR-AGENTS.md" or .agents_entry == "AGENTS.md" or
          .agents_entry == null) and
        (.canonical_api | type == "string") and
        (.canonical_raw | type == "string") and
        .freshness_contract == $freshness
        ' status.json >/dev/null 2>&1; then
        fail "status.json is invalid"
    fi

    status_repo=$(jq -r '.repo' status.json)
    status_branch=$(jq -r '.branch' status.json)
    status_sha=$(jq -r '.describes_commit' status.json)
    status_time=$(jq -r '.generated_at' status.json)
    status_agents=$(jq -r '.agents_entry // ""' status.json)
    status_api=$(jq -r '.canonical_api' status.json)
    status_raw=$(jq -r '.canonical_raw' status.json)
    expected_api="https://api.github.com/repos/$status_repo/commits/$status_branch"
    expected_raw="https://raw.githubusercontent.com/$status_repo/$status_sha/status.json"

    [ "$status_agents" = "$agents_entry" ] || fail "status.json agents_entry does not match the repository"
    [ "$status_api" = "$expected_api" ] || fail "status.json canonical_api is inconsistent"
    [ "$status_raw" = "$expected_raw" ] || fail "status.json canonical_raw is inconsistent"

    status_short_sha=$(printf '%s' "$status_sha" | cut -c1-7)
    make_block "$status_short_sha" "$status_time" "$status_api" "$tmp_root/expected-block"

    while IFS= read -r file; do
        if ! state=$(marker_state "$file"); then
            fail "malformed repo-state markers in $file"
        fi
        [ "$state" = present ] || fail "repo-state markers are missing in $file"
        awk '
            index($0, "<!-- repo-state:begin") { inside = 1 }
            inside { print }
            index($0, "<!-- repo-state:end") { inside = 0 }
        ' "$file" > "$tmp_root/actual-block"
        if ! cmp -s "$tmp_root/expected-block" "$tmp_root/actual-block"; then
            fail "repo-state stamp in $file is inconsistent with status.json"
        fi
    done < "$tmp_root/targets"
}

if [ "$check_only" = true ]; then
    validate_status
    printf '%s\n' "repo-state: check ok"
    exit 0
fi

head_sha=$(git rev-parse HEAD 2>/dev/null) || fail "HEAD does not resolve to a commit"
describes_commit=$head_sha
while :; do
    commit_message=$(git show -s --format=%B "$describes_commit")
    case $commit_message in
        chore\(repo-state\):*)
            parent=$(git rev-parse "$describes_commit^" 2>/dev/null) \
                || fail "stamp commit $describes_commit has no non-stamp ancestor"
            describes_commit=$parent
            ;;
        *) break ;;
    esac
done

commit_epoch=$(git show -s --format=%ct "$describes_commit")
if generated_at=$(date -u -r "$commit_epoch" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null); then
    :
elif generated_at=$(date -u -d "@$commit_epoch" '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null); then
    :
else
    fail "could not convert commit date to ISO-8601 UTC"
fi
describes_commit_date=$generated_at

if [ -n "${REPO_STATE_REPO:-}" ]; then
    repo_slug=$REPO_STATE_REPO
elif [ -n "${GITHUB_REPOSITORY:-}" ]; then
    repo_slug=$GITHUB_REPOSITORY
else
    remote_url=$(git config --get remote.origin.url 2>/dev/null) \
        || fail "cannot determine repo slug: remote.origin.url is missing"
    remote_url=${remote_url%.git}
    case $remote_url in
        *github.com:*) repo_slug=${remote_url#*github.com:} ;;
        *github.com/*) repo_slug=${remote_url#*github.com/} ;;
        *:*) repo_slug=${remote_url#*:} ;;
        *) fail "cannot determine GitHub repo slug from remote.origin.url" ;;
    esac
fi
printf '%s\n' "$repo_slug" | grep -Eq '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$' \
    || fail "invalid GitHub repo slug: $repo_slug"

if [ -n "${REPO_STATE_BRANCH:-}" ]; then
    branch=$REPO_STATE_BRANCH
elif branch=$(git symbolic-ref --quiet --short HEAD 2>/dev/null); then
    :
elif branch=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null); then
    branch=${branch#origin/}
else
    fail "cannot determine branch; set REPO_STATE_BRANCH for a detached checkout"
fi
[ -n "$branch" ] || fail "branch is empty"
printf '%s\n' "$branch" | grep -Eq '^[A-Za-z0-9._/-]+$' \
    || fail "branch contains characters that cannot be represented safely: $branch"

latest_release_url=
latest_tag=

decode_json_string_literal() {
    value=$1
    value=${value#\"}
    value=${value%\"}
    printf '%s' "$value" | sed 's/\\"/"/g; s/\\\\/\\/g'
}

read_existing_release_field_with_shell() {
    field_name=$1
    [ -f status.json ] || return 1
    field_literal=$(
        sed -n "s/^[[:space:]]*\"$field_name\"[[:space:]]*:[[:space:]]*//p" status.json \
            | sed -n '1p' \
            | sed 's/[[:space:]]*$//; s/,$//'
    )
    case $field_literal in
        '') return 1 ;;
        null) printf '%s' "" ;;
        \"*\") decode_json_string_literal "$field_literal" ;;
        *) return 1 ;;
    esac
}

load_existing_release_fields() {
    [ -f status.json ] || return 0
    if command -v jq >/dev/null 2>&1; then
        if existing_tag=$(jq -r 'if has("latest_tag") then .latest_tag // "" else "" end' status.json 2>/dev/null) &&
            existing_url=$(jq -r 'if has("latest_release_url") then .latest_release_url // "" else "" end' status.json 2>/dev/null); then
            latest_tag=$existing_tag
            latest_release_url=$existing_url
            return 0
        fi
    fi

    if existing_tag=$(read_existing_release_field_with_shell latest_tag); then
        latest_tag=$existing_tag
    fi
    if existing_url=$(read_existing_release_field_with_shell latest_release_url); then
        latest_release_url=$existing_url
    fi
}

refresh_release_fields() {
    [ "${REPO_STATE_NO_GH:-0}" != 1 ] \
        || fail "release refresh requires gh access; REPO_STATE_NO_GH=1 disables it"
    command -v "$gh_bin" >/dev/null 2>&1 || fail "gh is required to refresh release metadata"

    gh_error_file=$tmp_root/gh-release.err
    if release_fields=$(GH_PROMPT_DISABLED=1 GH_HTTP_TIMEOUT=5 \
        "$gh_bin" api "repos/$repo_slug/releases/latest" \
        --jq '[.tag_name, .html_url] | @tsv' 2>"$gh_error_file"); then
        tab=$(printf '\t')
        case $release_fields in
            *"$tab"*)
                latest_tag=${release_fields%%"$tab"*}
                latest_release_url=${release_fields#*"$tab"}
                [ -n "$latest_tag" ] || fail "latest release response did not include tag_name"
                [ -n "$latest_release_url" ] || fail "latest release response did not include html_url"
                ;;
            *)
                fail "latest release response was malformed"
                ;;
        esac
        return 0
    fi

    gh_error=$(cat "$gh_error_file")
    case $gh_error in
        *"HTTP 404"*)
            latest_tag=
            latest_release_url=
            ;;
        *)
            [ -n "$gh_error" ] && printf '%s\n' "$gh_error" >&2
            fail "could not refresh latest release metadata"
            ;;
    esac
}

if [ "$refresh_release" = 1 ]; then
    refresh_release_fields
else
    load_existing_release_fields
fi

canonical_api="https://api.github.com/repos/$repo_slug/commits/$branch"
canonical_raw="https://raw.githubusercontent.com/$repo_slug/$describes_commit/status.json"

json_escape() {
    printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

repo_json=$(json_escape "$repo_slug")
branch_json=$(json_escape "$branch")
if [ -n "$latest_tag" ]; then
    latest_tag_json="\"$(json_escape "$latest_tag")\""
else
    latest_tag_json=null
fi
if [ -n "$latest_release_url" ]; then
    latest_release_url_json="\"$(json_escape "$latest_release_url")\""
else
    latest_release_url_json=null
fi
if [ -n "$agents_entry" ]; then
    agents_entry_json="\"$agents_entry\""
else
    agents_entry_json=null
fi

cat > "$tmp_root/status.json" <<EOF
{
  "\$schema": "$SCHEMA_URL",
  "schema_version": 1,
  "generator_version": "$GENERATOR_VERSION",
  "repo": "$repo_json",
  "stamp_mode": "$stamp_mode",
  "generated_at": "$generated_at",
  "describes_commit": "$describes_commit",
  "describes_commit_date": "$describes_commit_date",
  "branch": "$branch_json",
  "latest_tag": $latest_tag_json,
  "latest_release_url": $latest_release_url_json,
  "agents_entry": $agents_entry_json,
  "canonical_api": "$canonical_api",
  "canonical_raw": "$canonical_raw",
  "freshness_contract": "$FRESHNESS_CONTRACT"
}
EOF

status_size=$(wc -c < "$tmp_root/status.json" | tr -d '[:space:]')
[ "$status_size" -le 2048 ] || fail "generated status.json exceeds 2 KiB"
short_sha=$(printf '%s' "$describes_commit" | cut -c1-7)
make_block "$short_sha" "$generated_at" "$canonical_api" "$tmp_root/block"

replace_block() {
    input_file=$1
    output_file=$2
    awk -v block_file="$tmp_root/block" '
        function emit_block(    line) {
            while ((getline line < block_file) > 0) print line
            close(block_file)
        }
        index($0, "<!-- repo-state:begin") {
            emit_block()
            skipping = 1
            next
        }
        skipping && index($0, "<!-- repo-state:end") {
            skipping = 0
            next
        }
        !skipping { print }
    ' "$input_file" > "$output_file"
}

insert_after_h1() {
    input_file=$1
    output_file=$2
    awk -v block_file="$tmp_root/block" '
        function emit_block(    line) {
            while ((getline line < block_file) > 0) print line
            close(block_file)
        }
        { print }
        !inserted && /^#[[:space:]]+[^#]/ {
            emit_block()
            inserted = 1
        }
    ' "$input_file" > "$output_file"
}

insert_after_centered_div() {
    input_file=$1
    output_file=$2
    awk -v block_file="$tmp_root/block" '
        function emit_block(    line) {
            while ((getline line < block_file) > 0) print line
            close(block_file)
        }
        {
            print
            lower = tolower($0)
            if (index(lower, "<div") &&
                (index(lower, "align=\"center\"") || index(lower, "align='\''center'\''"))) {
                centered = 1
            }
            if (!inserted && centered && index(lower, "</div>")) {
                emit_block()
                inserted = 1
            }
        }
    ' "$input_file" > "$output_file"
}

file_number=0
while IFS= read -r file; do
    file_number=$((file_number + 1))
    output_file="$tmp_root/stamped-$file_number"
    state=$(marker_state "$file")
    if [ "$state" = present ]; then
        replace_block "$file" "$output_file"
    elif [ "$file" = "$agents_entry" ]; then
        insert_after_h1 "$file" "$output_file"
    elif centered_div_anchor_exists "$file"; then
        insert_after_centered_div "$file" "$output_file"
    else
        insert_after_h1 "$file" "$output_file"
    fi
    mv "$output_file" "$file"
done < "$tmp_root/targets"
mv "$tmp_root/status.json" status.json

printf '%s\n' "repo-state: generated $short_sha ($generated_at)"
