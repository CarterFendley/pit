import os
import sys
import socket
import getpass
import logging
from functools import reduce
from typing import List, Tuple, Union

import click

from point_in_time.repo import PITRepo
from point_in_time.constants.return_codes import *
from point_in_time.errors import (
    PITRepoExistsError,
    PITInternalError,
    PITStashFailedError,
    PITStashPopFailedError,
    PITCommitParseFailed
)
from point_in_time.utils.main import (
    get_pit_path,
    is_pit_path_ignored,
    status_filter_pathspec
)
from point_in_time.utils.git import (
    git_show_toplevel
)
from point_in_time.utils.logging import (
    get_logger,
    set_cli_level,
)
from point_in_time.cli.util import *

from .extension import MultiCommandGroup


logger = get_logger(__name__, cli=True)

@click.group(cls=MultiCommandGroup)
@click.option('-v', '--verbose', count=True, help='Enable verbose logging.')
def pit(verbose: int):
    """
    Lightweight tooling for tracking experiment state in git based repositories.
    """
    print("Log level: ", verbose)
    set_cli_level(verbose)

@pit.command('init')
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

@pit.command('status')
def status():
    # Run standard checks
    result_checks = cli_check_standard()
    if result_checks != 0:
        sys.exit(result_checks)

    repo = cli_load_pit_repo()
    status = repo.get_snapshot_paths_status(cli=True)
    print('\n'.join(status))

@pit.command('show')
@click.argument('id')
@click.option('--verbose', is_flag=True, help="Displays more details.")
def show(id: str, verbose: bool):
    # Run standard checks
    result_checks = cli_check_standard()
    if result_checks != 0:
        sys.exit(result_checks)

    repo = cli_load_pit_repo()
    log = repo._load_log()

    if id not in log:
        logger.error("Specified Pit id does not exist in log.")
        sys.exit(PIT_CODE_ID_NOT_FOUND)

    details = repo.get_details(log[id])

    print(details.format(cli=True, verbose=verbose))

@pit.command('log')
@click.option('--limit', required=False, default=50, help="Set the limit of number of logs displayed")
def log(limit: int):
    # Run standard checks
    result_checks = cli_check_standard()
    if result_checks != 0:
        sys.exit(result_checks)

    repo = cli_load_pit_repo()
    log = repo._load_log()

    keys = list(log.keys())[:limit]
    keys.reverse()
    for id in keys:
        details = repo.get_details(log[id])
        print(details.format(cli=True, verbose=False))
        print()



@pit.command(['snapshot', 'snap'])
@click.option('--no-untracked', is_flag=True, help="Disables inclusion of '.pit' directory in git ignore")
@click.option('--no-metadata', is_flag=True, help="Disable recording of metadata such as user and hostname")
@click.option('-y', '--yes', is_flag=True, help="Skip the acceptance prompt")
def snapshot(
    no_untracked: bool,
    no_metadata: bool,
    yes: bool
):
    # Run standard checks
    result_checks = cli_check_standard()
    if result_checks != 0:
        sys.exit(result_checks)

    repo = cli_load_pit_repo()
    paths = repo.get_snapshot_paths()

    if no_untracked and '??' in paths:
        del paths['??']
    
    if no_metadata:
        metadata = None
    else:
        metadata = {
            'username': getpass.getuser(),
            'hostname': socket.gethostname()
        }

    if not yes:
        status = repo.get_snapshot_paths_status(paths, cli=True)
        print('\n'.join(status))

        r = input('Create snapshot with the contents above [Y/n]: ')
        if r.lower() not in ('', 'yes', 'y'):
            logger.error('Snapshot aborted.')
            sys.exit(PIT_CODE_SNAPSHOT_ABORTED)

    # Flatten paths
    def flatten_pathspec(a: List[str], b: List[Union[str, Tuple[str]]]):
        if isinstance(b[0], tuple):
            for t in b:
                a += t
        else:
            a += b
        return a
    flattened = reduce(
        flatten_pathspec,
        paths.values(),
        []
    )

    logger.debug('Creating snapshots with following paths:')
    for p in flattened:
        logger.debug("\t'%s'" % p)

    try:
        s = repo.snapshot(
            paths=flattened,
            metadata=metadata
        )
    except PITStashFailedError as err:
        logger.error('Git stash failed: \n%s', err.msg)
        sys.exit(PIT_CODE_STASH_PUSH_FAILED)
    except PITStashPopFailedError as err:
        logger.error('Git stash pop failed: \n%s', err.msg)
        sys.exit(PIT_CODE_STASH_POP_FAILED)
    except PITCommitParseFailed as err:
        logger.error('Failed to parse commit hash: %s', err.msg)
        sys.exit(PIT_CODE_COMMIT_PARSE_FAILED)

    logger.info(f"Created new snapshot: {s.pit_id}")