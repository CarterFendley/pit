import os
from typing import Optional
from contextlib import ExitStack

from point_in_time.constants.main import PIT_DIR_NAME

from .os import ChDir
from .git import git_show_toplevel, git_check_ignore

def get_pit_path(git_path: Optional[str] = None) -> str:
    """
    General purpose util for locating the `.pit` directory (which is in the toplevel git folder)

    **NOTE:** This utility does not preform validation on the Pit repo, just points to where the path ~should~ exist.

    Args:
        git_path (Optional[str], optional): Optional path to a git repository, if not provided, the current working directory will be assumed.

    Returns:
        str: The path where the pit directory should ~exist~
    """
    with ExitStack() as e: # For optional ChDir manager
        if git_path is not None:
            e.enter_context(ChDir(git_path))

        git_toplevel = git_show_toplevel()

        return os.path.join(
            git_toplevel,
            PIT_DIR_NAME
        )

def is_pit_path_ignored() -> bool:
    """
    General purpose utility for checking if the pit directory is ignored by git.

    Returns:
        bool: Boolean indicating if the pit dir is ignored by git
    """
    pit_path = get_pit_path()
    return git_check_ignore(pit_path)