#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  scripts/link-skills.sh [--dry-run] [--replace] [skill-name ...]

Link skills from this repository into:
  ~/.claude/skills
  ~/.codex/skills
  ~/.agents/skills

Examples:
  scripts/link-skills.sh
  scripts/link-skills.sh --dry-run
  scripts/link-skills.sh --replace code-analyze-business doc-render

Options:
  --dry-run   Print planned changes without creating directories or links.
  --replace   Replace existing symlinks that point somewhere else.
  -h, --help  Show this help.

Notes:
  Existing real files or directories are never removed. If a target path exists
  and is not a symlink, remove or rename it manually before linking.
USAGE
}

dry_run=false
replace=false
skills=()

while (($#)); do
  case "$1" in
    --dry-run)
      dry_run=true
      ;;
    --replace)
      replace=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      while (($#)); do
        skills+=("$1")
        shift
      done
      break
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      skills+=("$1")
      ;;
  esac
  shift
done

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "${script_dir}/.." && pwd)"
skills_dir="${repo_root}/skills"

if [[ ! -d "${skills_dir}" ]]; then
  echo "Skills directory not found: ${skills_dir}" >&2
  exit 1
fi

target_dirs=(
  "${HOME}/.claude/skills"
  "${HOME}/.codex/skills"
  "${HOME}/.agents/skills"
)

if ((${#skills[@]} == 0)); then
  while IFS= read -r skill_path; do
    skills+=("$(basename "${skill_path}")")
  done < <(
    find "${skills_dir}" -mindepth 1 -maxdepth 1 -type d \
      -exec test -f '{}/SKILL.md' ';' -print | sort
  )
fi

if ((${#skills[@]} == 0)); then
  echo "No skills found under ${skills_dir}" >&2
  exit 1
fi

link_skill() {
  local skill_name="$1"
  local source="${skills_dir}/${skill_name}"

  if [[ ! -f "${source}/SKILL.md" ]]; then
    echo "Skip ${skill_name}: ${source}/SKILL.md not found" >&2
    return 1
  fi

  for target_dir in "${target_dirs[@]}"; do
    local link_path="${target_dir}/${skill_name}"

    if [[ ! -d "${target_dir}" ]]; then
      if [[ "${dry_run}" == true ]]; then
        echo "Would create: ${target_dir}"
      else
        mkdir -p "${target_dir}"
      fi
    fi

    if [[ -L "${link_path}" ]]; then
      local current_target
      current_target="$(readlink "${link_path}")"
      if [[ "${current_target}" == "${source}" ]]; then
        echo "Already linked: ${link_path} -> ${source}"
        continue
      fi

      if [[ "${replace}" == true ]]; then
        if [[ "${dry_run}" == true ]]; then
          echo "Would remove: ${link_path}"
        else
          rm "${link_path}"
        fi
      else
        echo "Skip ${link_path}: symlink points to ${current_target} (use --replace to update)" >&2
        continue
      fi
    elif [[ -e "${link_path}" ]]; then
      echo "Skip ${link_path}: path exists and is not a symlink" >&2
      continue
    fi

    if [[ "${dry_run}" == true ]]; then
      echo "Would link: ${link_path} -> ${source}"
    else
      ln -s "${source}" "${link_path}"
      echo "Linked: ${link_path} -> ${source}"
    fi
  done
}

failed=0
for skill_name in "${skills[@]}"; do
  if ! link_skill "${skill_name}"; then
    failed=1
  fi
done

exit "${failed}"
