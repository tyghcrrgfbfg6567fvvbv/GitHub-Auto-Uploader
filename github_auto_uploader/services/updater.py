"""Fetch upstream release metadata and safely fast-forward the application."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import subprocess

import requests

from ..core.settings import (
    GITHUB_API_TIMEOUT,
    PROJECT_ROOT,
    UPSTREAM_API_URL,
    UPSTREAM_BRANCH,
    UPSTREAM_GIT_URL,
)


class UpdateState(str, Enum):
    CURRENT = "current"
    LOCAL_AHEAD = "local_ahead"
    UPDATE_AVAILABLE = "update_available"
    DIVERGED = "diverged"
    UNMANAGED = "unmanaged"
    OFFLINE = "offline"


@dataclass(frozen=True)
class ReleaseMetadata:
    tag: str
    title: str
    notes: str
    published_at: str
    url: str


@dataclass(frozen=True)
class UpdateStatus:
    state: UpdateState
    local_revision: str
    upstream_revision: str = ""
    release: ReleaseMetadata | None = None
    error: str = ""

    @property
    def update_available(self):
        return self.state == UpdateState.UPDATE_AVAILABLE

    @property
    def status_text(self):
        labels = {
            UpdateState.CURRENT: "Up to date with upstream",
            UpdateState.LOCAL_AHEAD: "Local checkout includes upstream and is ahead",
            UpdateState.UPDATE_AVAILABLE: "A safe upstream update is available",
            UpdateState.DIVERGED: "Local and upstream histories have diverged",
            UpdateState.UNMANAGED: "Not running from a Git checkout",
            UpdateState.OFFLINE: "Could not reach the upstream repository",
        }
        return labels[self.state]


@dataclass(frozen=True)
class UpdateResult:
    success: bool
    changed: bool
    message: str


def _run_git(arguments, root=PROJECT_ROOT):
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        capture_output=True,
        text=True,
    )


def _local_revision(root=PROJECT_ROOT):
    result = _run_git(["rev-parse", "--short", "HEAD"], root)
    return result.stdout.strip() if result.returncode == 0 else "unmanaged"


def _commit_exists(revision, root=PROJECT_ROOT):
    if not revision:
        return False
    return _run_git(["cat-file", "-e", f"{revision}^{{commit}}"], root).returncode == 0


def _is_ancestor(ancestor, descendant, root=PROJECT_ROOT):
    return _run_git(["merge-base", "--is-ancestor", ancestor, descendant], root).returncode == 0


def _request_json(url, session=None):
    requester = session or requests
    response = requester.get(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=GITHUB_API_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def fetch_upstream_status(root=PROJECT_ROOT, session=None):
    """Fetch current upstream metadata and compare it with the local Git graph."""
    root = Path(root)
    local_revision = _local_revision(root)
    if local_revision == "unmanaged":
        return UpdateStatus(UpdateState.UNMANAGED, local_revision)

    try:
        release_data = _request_json(f"{UPSTREAM_API_URL}/releases/latest", session)
        commit_data = _request_json(f"{UPSTREAM_API_URL}/commits/{UPSTREAM_BRANCH}", session)
    except (requests.RequestException, ValueError, KeyError) as error:
        return UpdateStatus(UpdateState.OFFLINE, local_revision, error=str(error))

    upstream_revision = str(commit_data.get("sha", ""))
    release = ReleaseMetadata(
        tag=str(release_data.get("tag_name") or "Unreleased"),
        title=str(release_data.get("name") or release_data.get("tag_name") or "Latest release"),
        notes=str(release_data.get("body") or "No release notes were published."),
        published_at=str(release_data.get("published_at") or ""),
        url=str(release_data.get("html_url") or ""),
    )

    full_local = _run_git(["rev-parse", "HEAD"], root).stdout.strip()
    if upstream_revision == full_local:
        state = UpdateState.CURRENT
    elif _commit_exists(upstream_revision, root) and _is_ancestor(upstream_revision, "HEAD", root):
        state = UpdateState.LOCAL_AHEAD
    elif _commit_exists(upstream_revision, root) and not _is_ancestor("HEAD", upstream_revision, root):
        state = UpdateState.DIVERGED
    else:
        state = UpdateState.UPDATE_AVAILABLE

    return UpdateStatus(state, local_revision, upstream_revision, release)


def apply_upstream_update(root=PROJECT_ROOT):
    """Fetch and apply only a clean, fast-forward upstream update."""
    root = Path(root)
    if not (root / ".git").exists():
        return UpdateResult(False, False, "This installation is not a Git checkout.")

    dirty = _run_git(["status", "--porcelain"], root)
    if dirty.returncode != 0:
        return UpdateResult(False, False, dirty.stderr.strip() or "Could not inspect the Git worktree.")
    if dirty.stdout.strip():
        return UpdateResult(
            False,
            False,
            "Update cancelled because the worktree has uncommitted changes.",
        )

    fetch = _run_git(["fetch", "--quiet", UPSTREAM_GIT_URL, UPSTREAM_BRANCH], root)
    if fetch.returncode != 0:
        return UpdateResult(False, False, fetch.stderr.strip() or "Could not fetch upstream.")

    current = _run_git(["rev-parse", "HEAD"], root).stdout.strip()
    fetched = _run_git(["rev-parse", "FETCH_HEAD"], root).stdout.strip()
    if current == fetched:
        return UpdateResult(True, False, "Already up to date.")
    if not _is_ancestor(current, fetched, root):
        return UpdateResult(
            False,
            False,
            "The histories are not fast-forward compatible; no files were changed.",
        )

    merge = _run_git(["merge", "--ff-only", "FETCH_HEAD"], root)
    if merge.returncode != 0:
        return UpdateResult(False, False, merge.stderr.strip() or "Fast-forward update failed.")
    return UpdateResult(True, True, "Update installed. Restart the application to load it.")
