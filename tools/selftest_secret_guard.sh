#!/usr/bin/env bash
set -eu

ROOT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
# Keep all scratch files inside the ignored workspace, including hook mktemp.
mkdir -p "$ROOT_DIR/.omc"
TEST_TMP=$(mktemp -d "$ROOT_DIR/.omc/secret-guard.XXXXXX")
trap 'rm -rf "$TEST_TMP"' EXIT
export TMPDIR="$TEST_TMP"
export SECRET_GUARD_SKIP_GITLEAKS=1 GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
# A test invoked from another hook must never inherit that repository's index.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_COMMON_DIR GIT_OBJECT_DIRECTORY \
  GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_CONFIG GIT_CONFIG_PARAMETERS GIT_CONFIG_COUNT
mkdir "$TEST_TMP/hooks" "$TEST_TMP/repo"
cp "$ROOT_DIR/tools/secret_guard_pre_commit.sh" "$TEST_TMP/hooks/pre-commit"
chmod +x "$TEST_TMP/hooks/pre-commit"
cd "$TEST_TMP/repo"
git init -q
git config user.name 'Secret Guard Selftest'
git config user.email 'secret-guard@localhost'
git config core.hooksPath "$TEST_TMP/hooks"
git config commit.gpgsign false
git commit -q --allow-empty -m base

count=0
failures=''
check_commit() {
  local expected=$1 label=$2 actual=pass prerequisite=${3:-1} marker=${4:-}
  count=$((count + 1))
  if git commit -q -m x > "$TEST_TMP/commit.log" 2>&1; then
    :
  else
    actual=block
    # Nonzero alone could hide Git setup failures unrelated to the guard.
    if ! grep -q '^Secret guard: .* Commit blocked\.$' "$TEST_TMP/commit.log"; then
      actual=error
    fi
    git reset -q
  fi
  case "$marker" in
    present) [ -f chained.marker ] || prerequisite=0 ;;
    absent) [ ! -f chained.marker ] || prerequisite=0 ;;
  esac
  if [ "$actual" = "$expected" ] && [ "$prerequisite" = 1 ]; then
    printf 'PASS: %s\n' "$label"
  else
    printf 'FAIL: %s (expected %s, got %s; prerequisite=%s)\n' \
      "$label" "$expected" "$actual" "$prerequisite"
    cat "$TEST_TMP/commit.log" >&2
    failures="${failures} ${label};"
  fi
}
vector() {
  printf '%s\n' "$3" > vector.txt
  git add vector.txt
  check_commit "$1" "$2"
}

# Assemble fixtures at runtime: no source line may trip CI/editor/host secret
# scanners (including the old regex). Split credential runs and false positives.
call='apiKey: getEffective'
call="${call}Value(\"elevenlabs_api_key\"),"
label='openai_compatible_tts_api_key: "OpenAI-'
label="${label}compatible TTS API key\","
vector pass 'identifier call' "$call"
vector pass 'quoted human-readable label' "$label"
comment_label='api_key: "OpenAI-'
comment_label="${comment_label}compatible TTS API key\" # label shown in settings"
vector pass 'quoted human-readable label with comment' "$comment_label"
vector pass 'tokenizer regression' 'token = tokens[index]'
vector pass 'mixed-case translation call' 'const apiKeyLabel = t("settings.apiKeyDescription");'
vector pass 'environment lookup call' 'api_key: os.environ.get("ELEVENLABS_API_KEY")'
equality='token === someLong'
equality="${equality}IdentifierName;"
vector pass 'JS strict equality with long identifier' "$equality"
vector pass 'dotted identifier chain' 'api_key = config.settings.value'

key='sk_01234567'
key="${key}89abcdef0123"
tp1="api_key = \"${key}\""
vector block 'double-quoted key' "$tp1"
vector block 'unquoted key at EOL' "API_KEY=${key}"
ghp='ghp_abcdefghijk'
ghp="${ghp}lmnopqrstuv"
ghp="${ghp}wxyz0123"
vector block 'single-quoted token with comma' "token: '${ghp}',"
json='AbCdEfGhIjKl'
json="${json}MnOpQrStUv"
vector block 'JSON apiToken' "  \"apiToken\": \"${json}\""
aws='AKIA'
aws="${aws}ABCDEFGHIJKLMNOP"
vector block 'AWS access-key ID' "$aws"
pem='-----BEGIN RSA'
pem="${pem} PRIVATE KEY-----"
vector block 'RSA private-key marker' "$pem"
vector block 'unquoted key with comment' "API_KEY=${key} # rotated 2026-09"
vector block 'URL query key with ampersand' "curl \"https://api.example.com/v1?api_key=${key}&format=json\""
vector block 'shell assignment with closing double quote' "docker run -e \"API_KEY=${key}\" img"
vector block 'unquoted key with line continuation' "  API_KEY=${key} \\"
vector block 'unquoted token with pipe' "TOKEN=${ghp} | tee"
base64='YWJjZGVmZ2hp'
base64="${base64}amtsbW5vcHFy"
vector block 'base64 padded quoted' "API_KEY=\"${base64}==\""
vector block 'base64 padded unquoted at EOL' "api_key: ${base64}="
jwt='eyJhbGciOiJI'
jwt="${jwt}UzI1NiJ9.eyJzdWIi"
jwt="${jwt}OiIxMjM0In0.abc"
vector block 'JWT three-segment token' "token = ${jwt}"
vector block 'unquoted key with question mark' "api_key=${key}?x=1"
vector block 'unquoted key with redirection' "api_key=${key}>out"
vector block 'unquoted key with colon' "api_key: ${key}:v2"
vector block 'URL-embedded credential' "https://x-access-token:${ghp}@github.com/o/r.git"
vector block 'markdown backtick key' "\`API_KEY=${key}\`"
vector block 'f-string key with exclamation mark' "raise ValueError(f\"api_key=${key}!\")"
vector block 'bold markdown key' "**api_key=${key}**"
vector block 'token at sentence end' "set token = ${ghp}."
vector block 'key with colon latest suffix' "API_KEY=${key}:latest"
placeholder='REPLACE_ME_WITH_'
placeholder="${placeholder}YOUR_KEY"
vector block 'JSON placeholder value (accepted trade, see header)' "\"api_key\": \"${placeholder}\""

# A repo-local hook must not break benign commits; secrets block before it.
cat > .git/hooks/pre-commit <<'HOOK'
#!/bin/sh
: > chained.marker
HOOK
chmod +x .git/hooks/pre-commit
printf '%s\n' 'benign chained content' > vector.txt
git add vector.txt
check_commit pass 'benign commit with repo-local hook present succeeds'
rm -f chained.marker
printf '%s\n' "$tp1" > vector.txt
git add vector.txt
check_commit block 'secret blocked before repo-local hook' 1 absent

# An inherited secret must pass the merge filter; a novel one must block.
# Seed the inherited fixture with the hook explicitly disabled only for setup.
rm -f vector.txt
git checkout -q -b guard-left
printf '%s\n' "$call" > left.txt
git add left.txt
git commit -q -m left
git checkout -q -b guard-right HEAD^
printf '%s\n' "$tp1" > right.txt
git add right.txt
git -c core.hooksPath=/dev/null commit -q -m right
git checkout -q guard-left
git merge --no-commit --no-ff guard-right > "$TEST_TMP/merge.log" 2>&1
test -f .git/MERGE_HEAD
inherited_ok=1
if ! "$TEST_TMP/hooks/pre-commit" > "$TEST_TMP/inherited.log" 2>&1; then
  inherited_ok=0
  cat "$TEST_TMP/inherited.log" >&2
fi
printf '%s\n' "API_KEY=${key}" > novel.txt
git add novel.txt
check_commit block 'merge inherited content allowed; novel secret blocked' "$inherited_ok"

if [ -n "$failures" ]; then
  printf 'FAIL: secret guard selftest:%s\n' "$failures" >&2
  exit 1
fi
printf 'PASS: secret guard selftest (%s vectors)\n' "$count"
