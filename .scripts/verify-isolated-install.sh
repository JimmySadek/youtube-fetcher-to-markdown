#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_package="${1:-$repo_root}"
skills_cli_version="${SKILLS_CLI_VERSION:-1.5.21}"
probe_root="$(mktemp -d)"

cleanup() {
  case "$probe_root" in
    "${TMPDIR:-/tmp}"/*|/tmp/*|/var/folders/*/T/*) rm -rf -- "$probe_root" ;;
    *) printf 'Refusing to remove unexpected probe path: %s\n' "$probe_root" >&2 ;;
  esac
}
trap cleanup EXIT

probe_home="$probe_root/home"
probe_project="$probe_root/project"
probe_cache="$probe_root/npm-cache"
mkdir -p "$probe_home" "$probe_project" "$probe_cache"
: > "$probe_root/npmrc"

(
  cd "$probe_project"
  HOME="$probe_home" \
  XDG_CONFIG_HOME="$probe_home/.config" \
  XDG_CACHE_HOME="$probe_home/.cache" \
  npm_config_cache="$probe_cache" \
  npm_config_userconfig="$probe_root/npmrc" \
  DO_NOT_TRACK=1 \
    npx --yes "skills@$skills_cli_version" add "$source_package" \
      --skill youtube-fetcher \
      --agent codex \
      --copy \
      --yes
)

installed_skill="$probe_project/.agents/skills/youtube-fetcher"
required_files=(
  "SKILL.md"
  "README.md"
  "LICENSE"
  "requirements.txt"
  "scripts/fetch_transcript.py"
  "assets/banner.png"
  "agents/openai.yaml"
)

for relative_path in "${required_files[@]}"; do
  if [[ ! -f "$installed_skill/$relative_path" ]]; then
    printf 'Missing installed file: %s\n' "$relative_path" >&2
    exit 1
  fi
  printf 'verified %s\n' "$relative_path"
done

HOME="$probe_home" python3 "$installed_skill/scripts/fetch_transcript.py" --check-deps
printf 'Isolated install verified with skills CLI %s.\n' "$skills_cli_version"
