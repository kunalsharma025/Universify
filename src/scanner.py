import os
from pathlib import Path
from .config import ALL_EXTS


def scan_folder(folder, known_paths):
    return [(full, Path(name).stem) for dirpath, _dirs, files in os.walk(folder) for name in files
            if name.lower().endswith(ALL_EXTS)
            and (full := os.path.join(dirpath, name)) not in known_paths]
