import os
import shutil

class ChDir:
    """A context manager for changing directories"""
    def __init__(self, path: str):
        self.path = path
        self._original_path = None

    def __enter__(self):
        assert self._original_path is None, "ChDir contexts should not be nested, create a new ChDir object if needed."
        self._original_path = os.curdir

        os.chdir(self.path)

    def __exit__(self, exc_type, exc_value, traceback):
        os.chdir(self._original_path)
        self._original_path = None

class WithBackUp:
    def __init__(
        self,
        path: str,
        move: bool = True
    ):
        assert os.path.isfile(path), "Path provided is not valid file"
        self.path = path
        self.move = move
        self._backup_path = None

    def __enter__(self):
        assert self._backup_path is None, "WithBackUp contexts should note be entered multiple times."
        self._backup_path = self.path + '.bak'

        if self.move:
            shutil.move(self.path, self._backup_path)
        else:
            shutil.copy(self.path, self._backup_path)

    def __exit__(self, exc_type, exc_value, traceback):
        assert self._backup_path is not None, "WithBackUp context has not been entered"

        if exc_type is not None:
            # Restore from backup
            shutil.move(self._backup_path, self.path)
        else:
            # Remove backup if no error
            os.remove(self._backup_path)