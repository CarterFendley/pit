import os
import subprocess
from typing import Optional, Union, Dict, List, Tuple, Set
from contextlib import ExitStack

from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

from point_in_time.constants.main import PIT_DIR_NAME

from .os import ChDir
from .git import git_show_toplevel, git_check_ignore

GIT_STATUS_CODES_W_TUPLE = (
    ' R',
    'R '
)
"""
Git short form status 'codes' which indicate that there will be two paths separated by '->'. This can be used with `status_filter_pathspec` to know which keys will have a list of tuple with two items (`Set[Tuple[str]]`) instead of a simple list of of strings (`Set[str]`).
"""

GIT_STATUS_CODES_UNMERGED = (
    "DD",
    "AU",
    "UD",
    "UA",
    "DU",
    "AA",
    "UU"
)
"""
Git short form status 'codes' which indicated unmerged files. Although the `U` character is a good indicator of this, the presence of `DD` status and similar which also indicate unmerged trees is harder, so this list is maintained
"""

GIT_STATUS_STRING_MAPPINGS = {
    'A': 'new file',
    'C': 'copied',
    'D': 'deleted',
    'M': 'modified',
    'R': 'renamed',
    'T': 'typechange',
    '!': 'ignored',
    '?': 'untracked'
}
"""
Mappings from git single char status codes to status strings.

**NOTE:** These are non-standard due inclusion of `!` and `?`
"""

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

def find_unescaped_qoute(string: str, start: int) -> int:
    escaped = False
    for i in range(start, len(string)):
        if escaped:
            escaped = False
            continue # Ignore anything escaped
        else:
            if string[i] == '\\': # Evals to a string slash
                escaped = True
            if string[i] == '"':
                return i
    return -1

def status_filter_pathspec(
    pathspec: List[str],
) -> Dict[str, List[Union[str, Tuple[str]]]]:
    """
    This utility parses the output of `git status --short` and filters based on a git [pathspec](https://git-scm.com/docs/gitglossary#Documentation/gitglossary.txt-aiddefpathspecapathspec). See an example return below.

    ```python
    >>> status_filter_pathspec(...)
    {
        'M ': ['README.md'],
        ' M': ['path/to/modified/file.py', 'file_two.py'],
        'R ': [('original.py', 'renamed.py')]
    }
    ```

    As shown above, this function will either return a dictionary with a list of tuple with two items (`Set[Tuple[str]]`) OR a simple list of of strings (`Set[str]`). The git status codes (which are the dictionary keys) which return `Tuple[str]` are indicated by `GIT_STATUS_CODES_W_TUPLE`. Read more about the short form git status [here](https://git-scm.com/docs/git-status#_short_format).

    **NOTE:** Pathspecs are parsed by [cpburnz/python-pathspec](https://github.com/cpburnz/python-pathspec).

    Args:
        pathspec (List[str]): The pathspec to filter by.

    Returns:
        Dict[str]: The git status filtered by the pathspec file (including ignored files).
    """
    status = subprocess.run(
        args=['git', 'status', '--short', '--ignored'],
        check=True,
        capture_output=True,
    )
    status = status.stdout.decode().split('\n')

    # Parse status into two lists
    files_by_code: Dict[List] = {}
    for line in status:
        if line == '':
            continue
        code, rest = line[:2], line[3:]

        if rest.startswith('"'):
            pos = find_unescaped_qoute(rest, 1)
            assert pos != -1, "Found unclosed quote in line: %s" % line
            path_one, rest = rest[1:pos], rest[pos+2:]

            # Process any escape sequences in the quoted string
            path_one = bytes(path_one, 'utf-8').decode('unicode_escape')
        else:
            pos = rest.find(' ')
            if pos == -1:
                pos = len(rest)
            path_one, rest = rest[0:pos], rest[pos+1:]

        if not rest.startswith('->'):
            path_two = None
        else:
            if rest[3] == '"':
                assert rest.endswith('"'), "Found unclosed quote on line: %s" % line
                path_two = rest[4:-1]

                # Process any escape sequences in the quoted string
                path_two = bytes(path_two, 'utf-8').decode('unicode_escape')
            else:
                path_two = rest[3:]

        if code not in files_by_code:
            files_by_code[code] = []

        if path_two is not None:
            assert code in (' R', 'R '), "Assumption about '->' broken."
            files_by_code[code].append((path_one, path_two))
        else:
            files_by_code[code].append(path_one)

    # Filter based on specified pathspec
    spec = PathSpec.from_lines(GitWildMatchPattern, pathspec)
    for code in files_by_code.keys():
        if code in GIT_STATUS_CODES_W_TUPLE:
            # Note: There is a design decision here to include both paths if one side is matched.
            matched = set()
            for file_one, file_two in files_by_code[code]:
                if spec.match_file(file_one) or spec.match_file(file_two):
                    matched.add((file_one, file_two))

            files_by_code[code] = matched
        else:
            files_by_code[code] = set(
                spec.match_files(files_by_code[code])
            )

    # Normalize by removing codes no items and sorting
    files_by_code = {
        k:sorted(v)
        for k, v in files_by_code.items()
        if v != set()
    }

    return files_by_code

def code_to_status_string(code: str) -> str:
    """
    This method will transform the short form status codes into status strings. When the status of the index differs from the worktree, both will be returned

    This method transforms the short form status codes into status strings. It will prefer the status of the worktree over the index because the worktree is what will be included in snapshots.

    Examples:
    ```python
    >>> code_to_status_string('A ')
    'added:'
    >>> code_to_status_string(' M')
    'modified:'
    >>> code_to_status_string('AM')
    'added & modified:'
    >>> # Unmerged will simply return unmerged
    >>> code_to_status_string('AU')
    'unmerged:'
    ```

    References:
        - [wt_status_diff_status_string(...)](https://github.com/git/git/blob/9005149a4a77e2d3409c6127bf4fd1a0893c3495/wt-status.c#L300)

    Args:
        code (str): A git short form status code.

    Returns:
        str: The status string.
    """
    assert len(code) == 2, "Invalid git status code"

    if code in GIT_STATUS_CODES_UNMERGED:
        return "unmerged:"

    index_status = code[0]
    worktree_status = code[1]

    worktree_string = GIT_STATUS_STRING_MAPPINGS.get(
        worktree_status,
        None
    )
    index_string = GIT_STATUS_STRING_MAPPINGS.get(
        index_status,
        None
    )

    if index_status != worktree_status and (index_string is not None and worktree_string is not None):
        # If we have different statuses for index / worktree, combine
        return f'{index_string} & {worktree_string}:'
    elif worktree_string is not None:
        return f'{worktree_string}:'
    elif index_string is not None:
        return f'{index_string}:'

    raise RuntimeError("Unable to map either index or worktree status to string: '%s'" % code)