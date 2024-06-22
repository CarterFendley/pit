from __future__ import annotations
import os
import re
import json
from json import JSONDecodeError
from datetime import datetime
from typing import Dict, List, Set, Tuple, Union

from pydantic import BaseModel, TypeAdapter
from pydantic_core import ValidationError
from colorama import (
    just_fix_windows_console,
    Fore
)

from point_in_time.constants.main import (
    PIT_LOG_NAME,
    PIT_INCLUDE_NAME
)
from point_in_time.errors import (
    PITInternalError,
    PITRepoExistsError,
    PITLogLoadError,
    PITIncludeLoadError
)
from point_in_time.utils.main import (
    status_filter_pathspec,
    code_to_status_string
)

__all__ = ['PITRepo']
just_fix_windows_console()

class PITRepo:
    @classmethod
    def create_repo(cls, path: str) -> PITRepo:
        """
        Given a directory, this function will initialize a empty repo and return the path to the `.pit/` directory.

        Args:
            path (str): The directory to initialize as an empty Pit repository.

        Raises:
            PITInternalError: If the specified path does not exist or `.pit/` already exists under the path.

        Returns:
            PITRepo: The initialized PITRepo.
        """
        parent_dir = os.path.dirname(path)
        if not os.path.isdir(parent_dir):
            raise PITInternalError("Path specified is not a directory: %s" % parent_dir)

        if os.path.exists(path):
            raise PITRepoExistsError()
        os.mkdir(path)

        # Initialize files
        log_data = {}
        log_path = os.path.join(
            path,
            PIT_LOG_NAME
        )
        with open(log_path, 'w') as f:
            json.dump(log_data, f)

        include_path = os.path.join(
            path,
            PIT_INCLUDE_NAME
        )
        with open(include_path, 'w') as f:
            f.write('# Pit include files are treated written in the git pathspec syntax\n')
            f.write('# See more here: https://git-scm.com/docs/gitglossary#Documentation/gitglossary.txt-aiddefpathspecapathspec\n')
            f.write('*\n')

        return cls(path)

    def __init__(self, path: str):
        self._path = path
        self._log_path = os.path.join(
            self._path,
            PIT_LOG_NAME
        )
        self._include_path = os.path.join(
            self._path,
            PIT_INCLUDE_NAME
        )

        self._load_log()

    def _load_log(self):
        if not os.path.isfile(self._log_path):
            raise PITLogLoadError("Malformed pit directory: Log file does not exist")

        try:
            with open(self._log_path, 'r') as f:
                log_data = json.load(f)
        except JSONDecodeError as err:
            raise PITLogLoadError("Malformed pit log: %s" % err.msg)

        try:
            ta = TypeAdapter(Dict[str, PITLogEntry])
            self.log = ta.validate_python(log_data)
        except ValidationError as err:
            raise PITLogLoadError("Malformed pit log: %s" % str(err))

    def get_snapshot_paths(self) -> Dict[str, Set[Union[str, Tuple[str]]]]:
        with open(self._include_path, 'r') as f:
            lines = f.read()

        force_comments = list(re.finditer(r"^#\s*[fF]orce\s*$", lines))
        if len(force_comments) > 1:
            raise PITIncludeLoadError("Found multiple 'force' comments in include file. Only one 'force' section can be included.")
        elif len(force_comments) == 0:
            included = status_filter_pathspec(lines.split('\n'))

            # No force block so remove those paths
            del included['!!']
        else:
            include_lines = lines[:force_comments[0].span[0]]
            force_lines = lines[-force_comments[0].span[1]:]

            included = status_filter_pathspec(include_lines.split('\n'))

            # Replace ignored files with those matched by the force block
            del included['!!']
            included['!!'] = status_filter_pathspec(force_lines.split('\n'))['!!']

        return included

    def get_snapshot_paths_status(
        self,
        cli: bool = False,
    ) -> List[str]:
        included = self.get_snapshot_paths()

        # Match all paths to get a diff of paths not included
        all_paths = status_filter_pathspec(['*'])
        not_included = {}
        for code, paths in all_paths.items():
            not_included[code] = set(all_paths[code]) - set(included.get(code, []))

            if len(not_included[code]) == 0:
                del not_included[code]
        # Don't display ignored files
        if '!!' in not_included:
            del not_included['!!']

        status: List[str] = []
        if len(included) != 0:
            if cli:
                c = Fore.GREEN
            else:
                c = ''

            status.append(f'Changes included in snapshots:{c}')
            for code, paths in included.items():
                status_string = code_to_status_string(code)
                for path in sorted(paths):
                    status.append(f"\t{status_string} {path}")

            if cli:
                c = Fore.RESET
            status.append(c)
        if len(not_included) != 0:
            if cli:
                c = Fore.RED
            else:
                c = ''

            status.append(f'Changes not included in snapshots:{c}')
            for code, paths in not_included.items():
                for path in sorted(paths):
                    status.append(f"\t{status_string} {path}")

            if cli:
                c = Fore.RESET
            status.append(c)

        return status


    def snapshot(self):
        pass



class PITLogEntry(BaseModel):
    id: str
    git_hash: str
    created_at: datetime