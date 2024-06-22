import os
import subprocess
from typing import Callable, Optional, List, Dict, Set
from pathlib import Path
from dataclasses import dataclass
from functools import reduce

import pytest

from point_in_time.repo import PITRepo

@pytest.fixture
def with_empty_dir(tmp_path_factory):
    # Note: Using tmp_path_factory over tmp_path to not collide with tmp_path if used by consuming tests / fixtures
    tmp_path: Path = tmp_path_factory.mktemp("git_dir")
    original_dir = os.curdir
    os.chdir(tmp_path)

    yield tmp_path

    # Restore old directory path
    os.chdir(original_dir)


GIT_CODE_COMMITTED = '99'
"""Non-standard status code to assure allow for associated fixtures to commit files."""
@dataclass
class GitSpec:
    """
    A dataclass accepted by associated fixtures which informs the fixtures how to initialize the git repo and contains helper properties for tests utilizing those fixtures.
    """

    spec_dict: Dict[str, List[str]]
    """
    The spec which the fixture was invoked with.
    """

    @property
    def git_status_spec(self) -> Dict[str, List[str]]:
        """
        **IMPORTANT NOTE:** This method is very much a *WIP*, only built atm to work with specs known to be defined by tests in this repo.

        Utility to map specs used to define the files should be in the git fixture to those which would be returned by `git status`. Specifically, git status will return some directories, like untracked directories

        Args:
            spec (Dict[str, Set[str]]): The spec to transform.
        Returns:
            Dict[str, Set[str]]: The spec that should be expected by `git status` returns
        """
        if hasattr(self, '_git_status_spec'):
            return self._git_status_spec

        spec = self.spec_dict.copy()

        def top_level_only(path):
            s = os.path.split(path)
            if s[0] != '':
                return s[0] + '/'
            return s[1]

        for code, paths in spec.items():
            if code in ('!!', '??'):
                spec[code] = set(map(
                    top_level_only,
                    paths
                ))

            # Sort all paths alphabetically 
            spec[code] = sorted(spec[code])

        self._git_status_spec = spec
        return spec

    def spec_fattened(
        self,
        exclude_codes: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None
    ) -> Set[str]:
        """
        A flattened list of files inside of the spec.

        **NOTE:** This will not always contain the paths returned by `git status` and associated commands. The `git status` command will often truncate the file paths to the top level directory or similar. Use `expected_initial_status` instead for that use case.

        Returns:
            Set[str]: The list of file paths in `self.spec`
        """
        if exclude_codes is None:
            exclude_codes = []
        if exclude_paths is None:
            exclude_paths = []

        spec = self.spec_dict.copy()

        for code in exclude_codes:
            del spec[code]

        flattened = reduce(
            lambda a, b: a.union(b),
            spec.values(),
            set()
        )

        flattened = filter(
            lambda p: p not in exclude_paths,
            flattened
        )

        return set(flattened)

    def expected_initial_status(
        self,
        include_ignores: bool = True
    ) -> Dict[str, List[str]]:
        """
        The expected return of `git status --short` (as parsed by utilities).

        Args:
            include_ignores (bool, optional): If the ignored files should be included

        Returns:
            Dict[str, Set[str]]: The `spec` which should be expected at the start.
        """
        expected = self.git_status_spec.copy()

        # Committed code is non-standard, will never show up in the status.
        del expected[GIT_CODE_COMMITTED]

        # If ignores excluded, exclude
        if not include_ignores:
            del expected['!!']

        return expected

@dataclass
class GitData:
    """
    A dataclass returned by the `with_git_repo` fixture containing information about the associated git repository setup by that fixture.
    """
    spec: GitSpec
    path: str
    ignore_path: str

@pytest.fixture
def with_git_repo(with_empty_dir) -> Callable[[], GitData]:
    def inner(
        git_spec: GitSpec = None,
    ) -> GitData:
        if git_spec is None:
            git_spec = GitSpec({})

        subprocess.run(
            ['git', 'init'],
            check=True
        )

        # Configure user email / name for any commit actions
        subprocess.run(
            ['git', 'config', 'user.email', '"fixture@pytest.com"'],
            check=True
        )
        subprocess.run(
            ['git', 'config', 'user.name', '"Pytest Fixture"'],
            check=True
        )

        # Create all files specified
        for _, files in git_spec.spec_dict.items():
            for file in files:
                parent = os.path.dirname(file)
                if parent != '':
                    os.makedirs(parent, exist_ok=True)

                # Create empty file
                with open(file, 'w') as f:
                    pass

        # Files which should be committed, commit
        # Note: `99` is not valid git status code, just making up one here for use with the fixture
        if '99' in git_spec.spec_dict:
            subprocess.run(
                ['git', 'add'] + list(git_spec.spec_dict['99']),
                check=True
            )
            subprocess.run(
                ['git', 'commit', '-m', 'Initial commit.'],
                check=True
            )

        # Files which should be staged, stage
        if 'A ' in git_spec.spec_dict:
            subprocess.run(
                ['git', 'add'] + list(git_spec.spec_dict['A ']),
                check=True
            )

        if '!!' in git_spec.spec_dict:
            with open('.gitignore', 'w') as f:
                for file in git_spec.spec_dict['!!']:
                    f.write(f'{file}\n')

        return GitData(
            spec=git_spec,
            path=str(with_empty_dir),
            ignore_path=os.path.join(str(with_empty_dir), '.gitignore'),
        )

    return inner

@dataclass
class PitData:
    path: str
    pit_repo: PITRepo
    git_data: GitData

@pytest.fixture
def with_pit_repo(with_git_repo) -> Callable[[], PitData]:
    def inner(
        no_ignore: bool = False,
        include_lines: Optional[List[str]] = None,
        **kwargs # Git args
    ) -> PitData:
        d = with_git_repo(**kwargs)

        args = ['pit', 'init']
        if no_ignore:
            args.append('--no-ignore')
        subprocess.run(
            args,
            check=True
        )


        pit_repo = PITRepo(os.path.join(d.path, '.pit'))
        if include_lines is not None:
            with open(pit_repo._include_path, 'w') as f:
                f.write('\n'.join(include_lines))

        return PitData(
            path=d.path,
            pit_repo=pit_repo,
            git_data=d
        )

    return inner
