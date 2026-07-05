"""Shared test helpers for the folderdiff test suite."""

import tarfile
import zipfile
from pathlib import Path


def write(path: Path, content: str) -> None:
    """Create a text file with the given content, including parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def make_zip(zip_path: Path, source: Path) -> None:
    """Create a zip archive containing all files below source."""
    with zipfile.ZipFile(zip_path, "w") as zf:
        for file in source.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(source))


def make_tar(tar_path: Path, source: Path, mode: str = "w") -> None:
    """Create a tar archive (optionally compressed) containing source's files."""
    with tarfile.open(tar_path, mode) as tf:
        for file in source.rglob("*"):
            if file.is_file():
                tf.add(file, file.relative_to(source))
