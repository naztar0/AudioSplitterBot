from pathlib import Path


class WriteFile:
    def __init__(self, path: Path, mode: str = 'w'):
        self.path = path
        self.mode = mode

    def __enter__(self):
        directory = self.path.parent
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
        self.file = open(self.path, self.mode)
        return self.file

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()
        return True


def ensure_dir(path: Path):
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    return path
