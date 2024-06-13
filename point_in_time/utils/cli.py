from .git import (
    git_is_command,
    git_is_inside_working_tree,
)
from .logging import pit_get_logger

from point_in_time.constants.strings import WARN_PIT_NOT_IGNORED
from point_in_time.constants.return_codes import *

from .main import is_pit_path_ignored

logger = pit_get_logger(__name__, cli=True)


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