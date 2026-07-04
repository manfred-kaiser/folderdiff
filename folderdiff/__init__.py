"""folderdiff core module.

Provides utilities to compare the contents of directories and/or zip
archives based on file hashes.
"""

import hashlib
import os
from pathlib import Path
from zipfile import ZipFile, is_zipfile

HashList = set[tuple[str, str]]


def sha256sum(filename: str) -> str:
    """Calculate the sha256 checksum of a file."""
    hash_sha256 = hashlib.sha256()
    with Path(filename).open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


class FileCompareResult:
    """Result of comparing the file sets of two paths."""

    def __init__(
        self,
        removed: set[str],
        moved: list[tuple[str, str]],
        added: set[str],
        modified: set[str],
    ) -> None:
        """Store the differences found between two file sets."""
        self.removed = removed
        self.moved = moved
        self.added = added
        self.modified = modified

    def print_result(self) -> None:
        """Print the comparison result to stdout."""
        if self.removed:
            print("==================== Removed =====================")
            for fileentry in sorted(self.removed, key=str.lower):
                print(f"- {fileentry}")

        if self.moved:
            print("=========== Moved (origin -> current) ============")
            for source, destination in sorted(self.moved, key=lambda el: el[1].lower()):
                print(f"> {source} -> {destination}")

        if self.added:
            print("===================== Added ======================")
            for fileentry in sorted(self.added, key=str.lower):
                print(f"+ {fileentry}")

        if self.modified:
            print("==================== Modified ====================")
            for fileentry in sorted(self.modified, key=str.lower):
                print(f"* {fileentry}")

    def __bool__(self) -> bool:
        """Return True if no differences were found."""
        return not bool(self.removed or self.moved or self.added or self.modified)


class FileCompare:
    """Compute and compare file hash lists of a directory or zip archive."""

    __hash__ = None  # type: ignore[assignment]

    def __init__(self, path: str, prefix: str | None = None) -> None:
        """Store the path to compare and an optional path prefix to strip."""
        self.path = path
        self.prefix = prefix

    def get_hashlist(self) -> HashList:
        """Return the hash list for the configured path."""
        if Path(self.path).is_dir():
            return self.get_hashlist_folder()
        if Path(self.path).is_file() and is_zipfile(self.path):
            return self.get_hashlist_zipfile()
        msg = "not supported filetype - only zip files and dirctories are supported!"
        raise ValueError(msg)

    def get_hashlist_folder(self) -> HashList:
        """Return the hash list for all files in a folder tree."""
        hashlist: HashList = set()
        for directory, _, files in os.walk(self.path):
            for f in files:
                path = str(Path(directory) / f)
                filepath = self.path
                if self.prefix and path.startswith(self.prefix.rstrip(os.sep) + os.sep):
                    filepath = str(Path(self.path) / self.prefix)
                hashlist.add((os.path.relpath(path, filepath), sha256sum(path)))
        return hashlist

    def get_hashlist_zipfile(self) -> HashList:
        """Return the hash list for all files in a zip archive."""
        hashlist: HashList = set()
        with ZipFile(self.path) as zfile:
            zfile.testzip()
            for fileentry in zfile.namelist():
                if fileentry.endswith("/"):
                    continue
                hashfunc = hashlib.sha256()
                hashfunc.update(zfile.read(fileentry))
                filepath = fileentry
                if self.prefix and fileentry.startswith(
                    self.prefix.rstrip(os.sep) + os.sep,
                ):
                    filepath = filepath[len(self.prefix.rstrip(os.sep)) + 1 :]
                hashlist.add((filepath, hashfunc.hexdigest()))
        return hashlist

    def compare(self, to_compare: "FileCompare") -> FileCompareResult:
        """Compare this file set against another and return the differences."""
        hash_set_src = self.get_hashlist()
        hash_set_dest = to_compare.get_hashlist()

        hash_set_added = hash_set_dest - hash_set_src
        hash_set_removed = hash_set_src - hash_set_dest

        hash_dict_added = {entry[1]: entry[0] for entry in hash_set_added}
        hash_dict_removed = {entry[1]: entry[0] for entry in hash_set_removed}

        moved_keys = set(hash_dict_added.keys()) & set(hash_dict_removed.keys())

        added = {e[0] for e in hash_set_added if e[1] not in moved_keys}
        moved = [(hash_dict_removed[key], hash_dict_added[key]) for key in moved_keys]
        removed = {e[0] for e in hash_set_removed if e[1] not in moved_keys}

        modified = added & removed
        added = added - modified
        removed = removed - modified

        return FileCompareResult(removed, moved, added, modified)

    def __eq__(self, to_compare: object) -> bool:
        """Compare based on file contents rather than identity."""
        if not isinstance(to_compare, FileCompare):
            return NotImplemented
        return bool(self.compare(to_compare))
