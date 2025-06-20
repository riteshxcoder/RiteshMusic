import asyncio
import shlex
from typing import Tuple

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError

import config
from ..logging import LOGGER


def install_req(cmd: str) -> Tuple[str, str, int, int]:
    async def install_requirements():
        args = shlex.split(cmd)
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return (
            stdout.decode("utf-8", "replace").strip(),
            stderr.decode("utf-8", "replace").strip(),
            process.returncode,
            process.pid,
        )

    return asyncio.get_event_loop().run_until_complete(install_requirements())


def git():
    LOGGER(__name__).info("🔁 Git update function called.")
    REPO_LINK = config.UPSTREAM_REPO

    if config.GIT_TOKEN:
        GIT_USERNAME = REPO_LINK.split("com/")[1].split("/")[0]
        TEMP_REPO = REPO_LINK.split("https://")[1]
        UPSTREAM_REPO = f"https://{GIT_USERNAME}:{config.GIT_TOKEN}@{TEMP_REPO}"
    else:
        UPSTREAM_REPO = REPO_LINK

    try:
        repo = Repo()
        LOGGER(__name__).info(f"[+] Git repo found at: {repo.working_tree_dir}")
    except (InvalidGitRepositoryError, NoSuchPathError):
        LOGGER(__name__).warning("⚠️ No valid git repo found. Skipping git setup.")
        return

    try:
        origin = repo.remote("origin")
    except ValueError:
        origin = repo.create_remote("origin", UPSTREAM_REPO)

    try:
        origin.fetch()
        if config.UPSTREAM_BRANCH in origin.refs:
            ref = origin.refs[config.UPSTREAM_BRANCH]
            if config.UPSTREAM_BRANCH not in repo.heads:
                repo.create_head(config.UPSTREAM_BRANCH, ref)
            repo.heads[config.UPSTREAM_BRANCH].set_tracking_branch(ref).checkout(force=True)
        else:
            LOGGER(__name__).warning(f"⚠️ Branch '{config.UPSTREAM_BRANCH}' not found in origin.")
            return

        origin.pull(config.UPSTREAM_BRANCH)
        LOGGER(__name__).info("✅ Repo updated from upstream successfully.")

        # Install latest requirements
        install_req("pip3 install --no-cache-dir -r requirements.txt")

    except GitCommandError as e:
        LOGGER(__name__).error(f"❌ Git error: {e}")
        repo.git.reset("--hard", "FETCH_HEAD")
