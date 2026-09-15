#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PYPROJECT = ROOT / "pyproject.toml"
DIST = ROOT / "dist"
TOKEN_FILE = ROOT / ".pypi_token"
PYPI_URL = "https://pypi.org/pypi/{name}/{version}/json"


def fail(message: str) -> None:
    print(f"\nERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def run(cmd: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    print("\n$ " + " ".join(cmd))
    return subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        check=True,
        capture_output=capture,
    )


def project_metadata() -> tuple[str, str]:
    text = PYPROJECT.read_text(encoding="utf-8")

    name = re.search(r'(?m)^name\s*=\s*"([^"]+)"', text)
    version = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)

    if not name or not version:
        fail("Could not read project name/version from pyproject.toml.")

    return name.group(1), version.group(1)


def check_tools() -> None:
    for command in ("git", "gh", "twine"):
        if shutil.which(command) is None:
            fail(f"Required command not found: {command}")

    result = subprocess.run(
        ["gh", "auth", "status"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        fail("GitHub CLI is not authenticated. Run: gh auth login")

    if not Path(sys.executable).exists():
        fail(f"Python executable not found: {sys.executable}")


def check_git() -> None:
    branch = run(
        ["git", "branch", "--show-current"],
        capture=True,
    ).stdout.strip()

    if branch != "main":
        fail(f"Release must run from main. Current branch: {branch}")

    status = run(
        ["git", "status", "--short"],
        capture=True,
    ).stdout.splitlines()

    unexpected = [
        line for line in status
        if line[3:] not in {"tracker.md", "release.py", ".gitignore", "pyproject.toml"}
    ]

    if unexpected:
        print("\nUnexpected working-tree changes:")
        for line in unexpected:
            print("  " + line)
        fail("Only tracker.md, release.py, .gitignore, and pyproject.toml may be locally modified.")

    if status:
        print("\nINFO: tracker.md is modified and will remain untouched.")


def pypi_exists(name: str, version: str) -> bool:
    url = PYPI_URL.format(name=name, version=version)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "general-scraper-engine-release"},
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status == 200
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return False
        fail(f"PyPI lookup failed with HTTP {exc.code}.")
    except urllib.error.URLError as exc:
        fail(f"PyPI lookup failed: {exc}")

    return False


def clean_dist() -> None:
    if DIST.exists():
        for item in DIST.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
    else:
        DIST.mkdir()


def build() -> list[Path]:
    run([sys.executable, "-m", "build"])

    artifacts = sorted(
        list(DIST.glob("*.whl")) +
        list(DIST.glob("*.tar.gz"))
    )

    if not artifacts:
        fail("Build produced no wheel or source distribution.")

    print("\nBuilt artifacts:")
    for artifact in artifacts:
        print("  " + artifact.name)

    return artifacts


def twine_check(artifacts: list[Path]) -> None:
    run([
        sys.executable,
        "-m",
        "twine",
        "check",
        *[str(x) for x in artifacts],
    ])


def existing_tag(tag: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", tag],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def tag_matches_head(tag: str) -> bool:
    tag_commit = run(
        ["git", "rev-list", "-n", "1", tag],
        capture=True,
    ).stdout.strip()

    head = run(
        ["git", "rev-parse", "HEAD"],
        capture=True,
    ).stdout.strip()

    return tag_commit == head


def git_release(version: str) -> str:
    tag = f"v{version}"

    if existing_tag(tag):
        if not tag_matches_head(tag):
            fail(f"Tag {tag} already exists but points to another commit.")
        print(f"INFO: {tag} already exists; resuming release.")
        return tag

    run(["git", "add", "-A"])

    staged = run(
        ["git", "diff", "--cached", "--name-only"],
        capture=True,
    ).stdout.splitlines()

    if "tracker.md" in staged:
        run(["git", "restore", "--staged", "tracker.md"])

    staged = run(
        ["git", "diff", "--cached", "--name-only"],
        capture=True,
    ).stdout.splitlines()

    if not staged:
        fail("Nothing is staged for the release commit.")

    print("\nRelease commit files:")
    for path in staged:
        print("  " + path)

    run(["git", "diff", "--cached", "--check"])
    run(["git", "commit", "-m", f"release: {tag}"])
    run(["git", "tag", "-a", tag, "-m", f"Release {tag}"])

    return tag


def push_git(tag: str) -> None:
    run(["git", "push", "origin", "main"])
    run(["git", "push", "origin", tag])


def github_release_exists(tag: str) -> bool:
    result = subprocess.run(
        ["gh", "release", "view", tag],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    return result.returncode == 0


def github_release(tag: str, artifacts: list[Path]) -> None:
    if github_release_exists(tag):
        print(f"INFO: GitHub Release {tag} already exists; skipping.")
        return

    run([
        "gh",
        "release",
        "create",
        tag,
        *[str(x) for x in artifacts],
        "--title",
        f"general-scraper-engine {tag}",
        "--generate-notes",
    ])


def read_token() -> str:
    if not TOKEN_FILE.exists():
        fail(
            f"Missing {TOKEN_FILE.name}. "
            "Create it with the PyPI API token."
        )

    token = TOKEN_FILE.read_text(encoding="utf-8").strip()

    if not token:
        fail(f"{TOKEN_FILE.name} is empty.")

    if not token.startswith("pypi-"):
        fail("PyPI token must start with pypi-.")

    return token


def upload_pypi(artifacts: list[Path], token: str) -> None:
    env = os.environ.copy()
    env["TWINE_USERNAME"] = "__token__"
    env["TWINE_PASSWORD"] = token

    print("\n$ twine upload dist/*")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "twine",
            "upload",
            *[str(x) for x in artifacts],
        ],
        cwd=ROOT,
        text=True,
        env=env,
    )

    if result.returncode != 0:
        fail(
            "PyPI upload failed. "
            "Fix credentials and rerun; existing Git/tag/release "
            "will be detected automatically."
        )


def verify_pypi(name: str, version: str) -> None:
    print(f"\nVerifying PyPI: {name}=={version}")

    for attempt in range(6):
        if pypi_exists(name, version):
            print(f"PASS: PyPI contains {name}=={version}")
            return

        if attempt < 5:
            print("INFO: PyPI propagation pending; retrying in 5 seconds...")
            time.sleep(5)

    fail(f"PyPI verification failed for {name}=={version}.")


def main() -> None:
    print("=" * 64)
    print("GENERAL SCRAPER ENGINE — AUTOMATED RELEASE")
    print("=" * 64)

    name, version = project_metadata()
    tag = f"v{version}"

    print(f"Project : {name}")
    print(f"Version : {version}")
    print(f"Tag     : {tag}")

    check_tools()
    check_git()

    if pypi_exists(name, version):
        fail(
            f"{name}=={version} already exists on PyPI. "
            "Update the version before releasing."
        )

    token = read_token()

    clean_dist()
    artifacts = build()
    twine_check(artifacts)

    tag = git_release(version)
    push_git(tag)
    github_release(tag, artifacts)

    upload_pypi(artifacts, token)
    verify_pypi(name, version)

    print("\n" + "=" * 64)
    print("RELEASE SUCCESS")
    print("=" * 64)
    print(f"Package : {name}")
    print(f"Version : {version}")
    print(f"Git tag : {tag}")
    print("GitHub  : released")
    print("PyPI    : uploaded and verified")
    print("Tracker : untouched")


if __name__ == "__main__":
    main()
