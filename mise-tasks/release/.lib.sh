# shellcheck shell=bash
# Shared helpers for the release:prepare and release:tag tasks.
#
# Sourced, never run: the file is hidden and not executable, so mise doesn't
# list it as a task. Callers set `dry_run` (true or false) before sourcing it.

# shellcheck disable=SC2154 # dry_run is set by the caller.
: "${dry_run:?set dry_run before sourcing .lib.sh}"

# shellcheck disable=SC2034 # Used by the callers.
changelog=CHANGELOG.md
branch=main
remote=origin

cd "${MISE_PROJECT_ROOT:-$(git rev-parse --show-toplevel)}" || exit 1

step() { printf '\n==> %s\n' "$*"; }
info() { printf '    %s\n' "$*"; }
warn() { printf '    warning: %s\n' "$*" >&2; }
die() {
	printf 'error: %s\n' "$*" >&2
	exit 1
}

# Run a command that changes something, or only print it in a dry run.
run() {
	if $dry_run; then
		printf '    [dry-run] would run:'
	else
		printf '    $'
	fi
	printf ' %q' "$@"
	printf '\n'
	$dry_run || "$@"
}

# Print a command for the user to run, indented and quoted so it can be pasted.
show_cmd() {
	printf '      '
	printf ' %q' "$@"
	printf '\n'
}

# On a failed exit, print `undo_hint` (set it once the task starts changing
# things) so the user knows how to back out.
undo_hint=""
on_exit() {
	local status=$?
	rm -rf "$tmpdir"
	if [ "$status" -ne 0 ] && [ -n "$undo_hint" ]; then
		printf '\nerror: the task did not finish. %s\n' "$undo_hint" >&2
	fi
}
tmpdir=$(mktemp -d)
trap on_exit EXIT

# --- Repository checks -------------------------------------------------------

require_clean_tree() {
	[ -z "$(git status --porcelain)" ] || die "the working tree is not clean; commit or stash your changes first"
	info "working tree is clean"
}

require_on_main() {
	local current
	current=$(git symbolic-ref --short -q HEAD || true)
	[ "$current" = "$branch" ] || die "run this on '$branch', but the current branch is '${current:-(detached HEAD)}'"
	info "on branch $branch"
}

require_up_to_date() {
	local ahead behind
	# An explicit refspec, so this works whatever the remote's fetch config is.
	git fetch --quiet "$remote" "+refs/heads/$branch:refs/remotes/$remote/$branch" || die "could not fetch $remote/$branch"
	if [ "$(git rev-parse HEAD)" != "$(git rev-parse "refs/remotes/$remote/$branch")" ]; then
		read -r ahead behind < <(git rev-list --left-right --count "HEAD...$remote/$branch")
		die "$branch is not up to date with $remote/$branch ($ahead ahead, $behind behind); run: git pull --ff-only"
	fi
	info "$branch is up to date with $remote/$branch"
}

# Succeeds if the full ref (e.g. refs/tags/v1.0) exists on the remote.
remote_ref_exists() {
	local status=0
	git ls-remote --exit-code "$remote" "$1" >/dev/null || status=$?
	case $status in
	0) return 0 ;;
	2) return 1 ;;
	*) die "could not list refs on $remote" ;;
	esac
}

# Refuse if the full ref exists locally or on the remote. $2 names it in messages.
require_ref_absent() {
	local ref=$1 what=$2
	if git rev-parse -q --verify "$ref" >/dev/null; then
		die "$what already exists locally"
	fi
	if remote_ref_exists "$ref"; then
		die "$what already exists on $remote"
	fi
	info "$what does not exist locally or on $remote"
}
