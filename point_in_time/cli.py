import os
import sys
import logging
import subprocess

import click

from point_in_time.repo import PITRepo
from point_in_time.constants.return_codes import *
from point_in_time.errors import (
    PITRepoExistsError,
    PITInternalError
)
from point_in_time.utils.main import get_pit_path, is_pit_path_ignored
from point_in_time.utils.git import git_show_toplevel
from point_in_time.utils.logging import pit_get_logger, set_cli_level
from point_in_time.utils.cli import *

logger = pit_get_logger(__name__, cli=True)

@click.group()
@click.option('-v', '--verbose', is_flag=True, help='Enable verbose logging.')
def pit(verbose: bool):
    """
    Lightweight tooling for tracking experiment state in git based repositories.
    """
    if verbose:
        set_cli_level(logging.DEBUG)

@pit.command()
@click.argument('directory', required=False, default=None)
@click.option('--no-ignore', is_flag=True, help="Disables inclusion of '.pit' directory in git ignore")
def init(directory: str, no_ignore: bool):
    """
    Creates an empty Pit repository in your toplevel git folder.
    """
    if directory is None:
        directory = os.curdir

    result_git_check = cli_check_git_repo()
    if result_git_check != 0:
        sys.exit(result_git_check)

    try:
        pit_path = get_pit_path(directory)
        r = PITRepo.create_repo(pit_path)
    except (PITRepoExistsError, PITInternalError, NotADirectoryError) as err:
        if isinstance(err, NotADirectoryError):
            logger.error("Path specified is not a directory: %s" % directory)
        else:
            logger.error(err.msg)

        if isinstance(err, PITRepoExistsError):
            sys.exit(PIT_CODE_REPO_EXISTS)
        sys.exit(PIT_CODE_INIT_FAILED)

    logger.info('Initialized empty Pit repository in %s' % r._path)

    if not no_ignore and not is_pit_path_ignored():
        ignore_path = os.path.join(git_show_toplevel(), '.gitignore')
        logger.debug("Adding .pit to %s" % ignore_path)
        with open(ignore_path, 'a') as f:
            f.write('\n# Pit repo directory')
            f.write('\n.pit/')

    # Run standard checks
    result_checks = cli_check_standard()
    if result_checks != 0:
        sys.exit(result_checks)