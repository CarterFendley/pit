import os
import sys

from point_in_time.utils.main import (
    is_pit_path_ignored,
    get_pit_path
)
from point_in_time.utils.git import (
    git_is_command,
    git_is_inside_working_tree,
)
from point_in_time.utils.logging import get_logger

from point_in_time.errors import PITRepoLoadError
from point_in_time.repo import PITRepo
from point_in_time.constants.strings import WARN_PIT_NOT_IGNORED
from point_in_time.constants.return_codes import *

logger = get_logger(__name__, cli=True)

def cli_load_pit_repo() -> PITRepo:
    """
    Utility for loading pit repos or detecting failure and exiting with the proper error code

    Returns:
        PITRepo: The loaded Pit repo
    """
    pit_path = get_pit_path()

    if not os.path.isdir(pit_path):
        logger.error("Could not find .pit repo next to .git, are you in a Pit repository?")
        sys.exit(PIT_CODE_REPO_NOT_FOUND)

    try:
        repo = PITRepo(pit_path)
    except PITRepoLoadError as err:
        logger.error(err.msg)
        sys.exit(PIT_CODE_REPO_LOAD_FAILED)

    return repo

def cli_check_git_repo() -> int:
    """
    Preform standard checks on git repo.

    Returns:
        int: Return code, zero if passed
    """
    if not git_is_command():
        logger.error("Unable to find git cli, which Pit depends on, please make sure git is installed and accessible to Pit's python interpreter." )
        return PIT_CODE_GIT_NOT_FOUND
    if not git_is_inside_working_tree():
        logger.error("Not a git repository (or any of the parent directories), pit is only accessible within .git repositories")
        return PIT_CODE_GIT_NO_REPO
    return 0


def cli_check_standard() -> int:
    """
    Preform standard CLI checks.

    Returns:
        int: Return code, zero if passed
    """
    git_checks = cli_check_git_repo()
    if git_checks != 0:
        return git_checks

    if not is_pit_path_ignored():
        logger.warn(WARN_PIT_NOT_IGNORED)

    return 0