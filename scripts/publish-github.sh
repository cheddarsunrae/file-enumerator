#!/usr/bin/env bash
set -euo pipefail

REPOSITORY="${REPOSITORY:-cheddarsunrae/file-enumerator}"
EXPECTED_BRANCH="${EXPECTED_BRANCH:-main}"

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

command -v git >/dev/null 2>&1 || fail "git is not installed"
command -v gh >/dev/null 2>&1 || fail "GitHub CLI 'gh' is not installed"

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "run this inside the file-enumerator Git repository"

gh auth status >/dev/null 2>&1 || fail "GitHub CLI is not authenticated; run: gh auth login"

current_branch="$(git branch --show-current)"
[[ "$current_branch" == "$EXPECTED_BRANCH" ]] || fail "expected branch '$EXPECTED_BRANCH'; found '$current_branch'"

if [[ -n "$(git status --porcelain)" ]]; then
    git status --short
    fail "working tree is not clean"
fi

expected_https="https://github.com/${REPOSITORY}.git"
expected_ssh="git@github.com:${REPOSITORY}.git"

if git remote get-url origin >/dev/null 2>&1; then
    origin_url="$(git remote get-url origin)"
    if [[ "$origin_url" != "$expected_https" && "$origin_url" != "$expected_ssh" ]]; then
        fail "origin points to '$origin_url', not '$REPOSITORY'"
    fi
fi

if gh repo view "$REPOSITORY" >/dev/null 2>&1; then
    visibility="$(gh repo view "$REPOSITORY" --json visibility --jq .visibility)"
    [[ "$visibility" == "PUBLIC" ]] || fail "repository exists but is not public"

    if ! git remote get-url origin >/dev/null 2>&1; then
        git remote add origin "$expected_ssh"
    fi

    git push -u origin "$EXPECTED_BRANCH"
else
    gh repo create "$REPOSITORY" \
        --public \
        --description "Recursive file inventory tool for Fedora, Linux, and Windows" \
        --source . \
        --remote origin \
        --push
fi

gh repo view "$REPOSITORY" --web=false
