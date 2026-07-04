"""folderdiff core module.

Provides utilities to compare the contents of directories and/or zip
archives based on file hashes.
"""

import hashlib
import os
import sys
from collections import defaultdict
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


def _group_by_hash(entries: HashList) -> dict[str, list[str]]:
    """Group hash-list entries by digest, preserving duplicate paths."""
    grouped: dict[str, list[str]] = defaultdict(list)
    for path, digest in entries:
        grouped[digest].append(path)
    return grouped


def _pair_by_hash(
    removed_by_hash: dict[str, list[str]],
    added_by_hash: dict[str, list[str]],
) -> tuple[list[tuple[str, str]], set[str], set[str]]:
    """Pair up removed/added paths that share a hash as moves.

    Files with duplicate content may appear multiple times under the same
    hash; only as many pairs as the smaller side allows are reported as
    moved, and the surplus stays classified as removed/added so that no
    entry is silently dropped.
    """
    moved: list[tuple[str, str]] = []
    removed: set[str] = set()
    added: set[str] = set()

    for digest, removed_paths in removed_by_hash.items():
        matched_added_paths = added_by_hash.get(digest, [])
        pair_count = min(len(removed_paths), len(matched_added_paths))
        moved.extend(
            zip(
                removed_paths[:pair_count],
                matched_added_paths[:pair_count],
                strict=True,
            ),
        )
        removed.update(removed_paths[pair_count:])

    for digest, added_paths in added_by_hash.items():
        matched_removed_paths = removed_by_hash.get(digest, [])
        pair_count = min(len(matched_removed_paths), len(added_paths))
        added.update(added_paths[pair_count:])

    return moved, removed, added


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
                relative_path = os.path.relpath(path, self.path)
                if self.prefix and relative_path.startswith(
                    self.prefix.rstrip(os.sep) + os.sep,
                ):
                    relative_path = relative_path[len(self.prefix.rstrip(os.sep)) + 1 :]
                try:
                    digest = sha256sum(path)
                except OSError as exc:
                    print(
                        f"warning: skipping unreadable file {path}: {exc}",
                        file=sys.stderr,
                    )
                    continue
                hashlist.add((relative_path, digest))
        return hashlist

    def get_hashlist_zipfile(self) -> HashList:
        """Return the hash list for all files in a zip archive."""
        hashlist: HashList = set()
        with ZipFile(self.path) as zfile:
            bad_file = zfile.testzip()
            if bad_file is not None:
                msg = f"corrupt zip archive: bad CRC-32 for {bad_file}"
                raise ValueError(msg)
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

        removed_by_hash = _group_by_hash(hash_set_src - hash_set_dest)
        added_by_hash = _group_by_hash(hash_set_dest - hash_set_src)

        moved, removed, added = _pair_by_hash(removed_by_hash, added_by_hash)

        modified = added & removed
        added = added - modified
        removed = removed - modified

        return FileCompareResult(removed, moved, added, modified)

    def __eq__(self, to_compare: object) -> bool:
        """Compare based on file contents rather than identity."""
        if not isinstance(to_compare, FileCompare):
            return NotImplemented
        return bool(self.compare(to_compare))
