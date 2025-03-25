import os
from pathlib import Path

from point_in_time.utils.fs import ChDir

def test_chdir(tmpdir: Path):
    origin = os.path.abspath(os.path.curdir)
    dst = str(tmpdir)

    with ChDir(dst):
        assert os.path.abspath(os.path.curdir) == dst
    assert os.path.abspath(os.path.curdir) == origin


    try:
        with ChDir(dst):
            assert os.path.abspath(os.path.curdir) == dst
            raise RuntimeError()
    except RuntimeError:
        pass
    assert os.path.abspath(os.path.curdir) == origin