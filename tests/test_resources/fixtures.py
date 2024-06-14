import os
import subprocess
from typing import Callable, List
from pathlib import Path
from dataclasses import dataclass

import pytest

@pytest.fixture
def with_empty_dir(tmp_path_factory):
    # Note: Using tmp_path_factory over tmp_path to not collide with tmp_path if used by consuming tests / fixtures
    tmp_path: Path = tmp_path_factory.mktemp("git_dir")
    original_dir = os.curdir
    os.chdir(tmp_path)

    yield tmp_path

    # Restore old directory path
    os.chdir(original_dir)

@dataclass
class GitData:
    path: str
    ignore_path: str
    ignore: List[str] = None

@pytest.fixture
def with_git_repo(with_empty_dir) -> Callable[[], GitData]:
    def inner(
        files: List[str] = None,
        ignore: List[str] = None
    ) -> GitData:
        subprocess.run(
            ['git', 'init'],
            check=True
        )


        if files is not None:
            for file in files:
                parent = os.path.dirname(file)
                if parent != '':
                    os.makedirs(parent, exist_ok=True)
                with open(file, 'w') as f:
                    pass
        if ignore is not None:
            with open('.gitignore', 'w') as f:
                for i in ignore:
                    f.write(f'{i}\n')

        return GitData(
            path=str(with_empty_dir),
            ignore_path=os.path.join(str(with_empty_dir), '.gitignore'),
            ignore=ignore
        )

    return inner

@dataclass
class PitData:
    path: str
    git_data: GitData

@pytest.fixture
def with_pit_repo(with_git_repo) -> Callable[[], PitData]:
    def inner(
        no_ignore: bool = False,
        *args # Git args
    ) -> PitData:
        d = with_git_repo(*args)

        args = ['pit', 'init']
        if no_ignore:
            args.append('--no-ignore')
        subprocess.run(
            args,
            check=True
        )

        return PitData(
            path=d.path,
            git_data=d
        )

    return inner
