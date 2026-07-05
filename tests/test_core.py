"""Unit tests for the folderdiff core module."""

import hashlib
import os
import zipfile
from pathlib import Path

import pytest
from conftest import make_zip, write

from folderdiff import FileCompare, FileCompareResult, sha256sum

# ---------------------------------------------------------------------------
# sha256sum
# ---------------------------------------------------------------------------


def test_sha256sum_matches_hashlib(tmp_path: Path) -> None:
    file_path = tmp_path / "data.bin"
    file_path.write_bytes(b"some binary content" * 1000)
    expected = hashlib.sha256(file_path.read_bytes()).hexdigest()
    assert sha256sum(str(file_path)) == expected


# ---------------------------------------------------------------------------
# FileCompare.get_hashlist - folders
# ---------------------------------------------------------------------------


def test_get_hashlist_folder(tmp_path: Path) -> None:
    write(tmp_path / "a.txt", "hello")
    write(tmp_path / "sub" / "b.txt", "world")

    hashlist = FileCompare(str(tmp_path)).get_hashlist()

    # Relative paths always use "/", regardless of os.sep, so that folder-mode
    # and zip-mode hash lists (zip entries are always "/"-separated) compare
    # equal across platforms.
    names = {entry[0] for entry in hashlist}
    assert names == {"a.txt", "sub/b.txt"}


def test_get_hashlist_raises_for_unsupported_path(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    with pytest.raises(ValueError, match="not supported filetype"):
        FileCompare(str(missing)).get_hashlist()


def test_get_hashlist_folder_strips_prefix(tmp_path: Path) -> None:
    write(tmp_path / "wordpress" / "index.php", "index")
    write(tmp_path / "wordpress" / "sub" / "b.txt", "world")

    hashlist = FileCompare(str(tmp_path), prefix="wordpress/").get_hashlist()

    names = {entry[0] for entry in hashlist}
    assert names == {"index.php", "sub/b.txt"}


def test_get_hashlist_folder_prefix_is_noop_when_not_nested(tmp_path: Path) -> None:
    write(tmp_path / "index.php", "index")

    hashlist = FileCompare(str(tmp_path), prefix="wordpress/").get_hashlist()

    assert {entry[0] for entry in hashlist} == {"index.php"}


def test_get_hashlist_folder_skips_broken_symlink_with_warning(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write(tmp_path / "a.txt", "hello")
    (tmp_path / "broken_link.txt").symlink_to(tmp_path / "does-not-exist")

    hashlist = FileCompare(str(tmp_path)).get_hashlist()

    assert {entry[0] for entry in hashlist} == {"a.txt"}
    assert "broken_link.txt" in capsys.readouterr().err


def test_get_hashlist_folder_skips_unreadable_file_with_warning(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write(tmp_path / "a.txt", "hello")
    locked = tmp_path / "locked.txt"
    write(locked, "secret")
    locked.chmod(0o000)

    try:
        hashlist = FileCompare(str(tmp_path)).get_hashlist()
    finally:
        locked.chmod(0o700)

    assert {entry[0] for entry in hashlist} == {"a.txt"}
    assert "locked.txt" in capsys.readouterr().err


def test_get_hashlist_folder_skips_non_regular_file_with_warning(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write(tmp_path / "a.txt", "hello")
    os.mkfifo(tmp_path / "pipe.fifo")

    # A FIFO blocks on open() until a writer connects; if it were not
    # filtered out before hashing, this call would hang forever.
    hashlist = FileCompare(str(tmp_path)).get_hashlist()

    assert {entry[0] for entry in hashlist} == {"a.txt"}
    assert "pipe.fifo" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# FileCompare.get_hashlist - zip archives
# ---------------------------------------------------------------------------


def test_get_hashlist_zipfile_matches_folder(tmp_path: Path) -> None:
    source = tmp_path / "source"
    write(source / "a.txt", "hello")
    write(source / "sub" / "b.txt", "world")

    zip_path = tmp_path / "source.zip"
    make_zip(zip_path, source)

    zip_hashlist = FileCompare(str(zip_path)).get_hashlist()
    folder_hashlist = FileCompare(str(source)).get_hashlist()
    assert zip_hashlist == folder_hashlist


def test_get_hashlist_zipfile_ignores_directory_entries(tmp_path: Path) -> None:
    zip_path = tmp_path / "with_dirs.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("sub/", "")
        zf.writestr("sub/file.txt", "content")

    hashlist = FileCompare(str(zip_path)).get_hashlist()
    assert {entry[0] for entry in hashlist} == {"sub/file.txt"}


def test_get_hashlist_zipfile_hashes_multi_chunk_entry_correctly(
    tmp_path: Path,
) -> None:
    # Exercises the streaming read path (chunk size is 64 KiB) instead of a
    # single zfile.read() call, to guard against reintroducing a full read
    # of large archive members into memory.
    payload = os.urandom(3 * 65536 + 1000)
    zip_path = tmp_path / "large.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("big.bin", payload)

    hashlist = FileCompare(str(zip_path)).get_hashlist()

    assert dict(hashlist)["big.bin"] == hashlib.sha256(payload).hexdigest()


def test_get_hashlist_zipfile_raises_for_corrupt_archive(tmp_path: Path) -> None:
    zip_path = tmp_path / "corrupt.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("a.txt", "hello world")

    # Corrupt the stored payload in place, leaving the CRC-32 in the local
    # header untouched, so reading the entry fails its integrity check.
    raw = bytearray(zip_path.read_bytes())
    offset = raw.find(b"hello world")
    raw[offset : offset + 5] = b"XXXXX"
    zip_path.write_bytes(raw)

    with pytest.raises(ValueError, match="corrupt zip archive"):
        FileCompare(str(zip_path)).get_hashlist()


# ---------------------------------------------------------------------------
# FileCompare.compare
# ---------------------------------------------------------------------------


def test_compare_detects_added_removed_modified_and_moved(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"

    write(src / "unchanged.txt", "same")
    write(dst / "unchanged.txt", "same")

    write(src / "removed.txt", "gone")

    write(dst / "added.txt", "new")

    write(src / "modified.txt", "before")
    write(dst / "modified.txt", "after")

    write(src / "old_name.txt", "moved content")
    write(dst / "new_name.txt", "moved content")

    result = FileCompare(str(src)).compare(FileCompare(str(dst)))

    assert result.removed == {"removed.txt"}
    assert result.added == {"added.txt"}
    assert result.modified == {"modified.txt"}
    assert result.moved == [("old_name.txt", "new_name.txt")]


def test_compare_identical_directories_has_no_differences(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    write(src / "a.txt", "hello")
    write(dst / "a.txt", "hello")

    result = FileCompare(str(src)).compare(FileCompare(str(dst)))

    assert not result.removed
    assert not result.moved
    assert not result.added
    assert not result.modified
    assert bool(result) is True


def test_compare_with_prefix_strips_zip_root(tmp_path: Path) -> None:
    zip_root = tmp_path / "zip_root"
    write(zip_root / "wordpress" / "index.php", "index")
    write(zip_root / "wordpress" / "wp-config-sample.php", "config")

    zip_path = tmp_path / "wordpress.zip"
    make_zip(zip_path, zip_root)

    live = tmp_path / "live"
    write(live / "index.php", "index")
    write(live / "wp-config-sample.php", "hacked")
    write(live / "webshell.php", "evil")

    result = FileCompare(str(zip_path), prefix="wordpress/").compare(
        FileCompare(str(live)),
    )

    assert result.added == {"webshell.php"}
    assert result.modified == {"wp-config-sample.php"}
    assert not result.removed
    assert not result.moved


def test_compare_with_prefix_on_both_sides_in_folder_mode(tmp_path: Path) -> None:
    extracted = tmp_path / "extracted"
    write(extracted / "wordpress" / "index.php", "index")
    write(extracted / "wordpress" / "wp-config-sample.php", "config")

    live = tmp_path / "live"
    write(live / "index.php", "index")
    write(live / "wp-config-sample.php", "hacked")
    write(live / "webshell.php", "evil")

    result = FileCompare(str(extracted), prefix="wordpress/").compare(
        FileCompare(str(live), prefix="wordpress/"),
    )

    assert result.added == {"webshell.php"}
    assert result.modified == {"wp-config-sample.php"}
    assert not result.removed
    assert not result.moved


def test_compare_detects_multiple_independent_moves(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"

    write(src / "old1.txt", "content one")
    write(dst / "new1.txt", "content one")

    write(src / "old2.txt", "content two")
    write(dst / "new2.txt", "content two")

    result = FileCompare(str(src)).compare(FileCompare(str(dst)))

    assert set(result.moved) == {("old1.txt", "new1.txt"), ("old2.txt", "new2.txt")}
    assert not result.added
    assert not result.removed


def test_compare_both_empty_directories(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()

    result = FileCompare(str(src)).compare(FileCompare(str(dst)))

    assert bool(result) is True


def test_compare_duplicate_removed_content_keeps_surplus_as_removed(
    tmp_path: Path,
) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"

    write(src / "a.txt", "duplicate content")
    write(src / "b.txt", "duplicate content")
    write(dst / "c.txt", "duplicate content")

    result = FileCompare(str(src)).compare(FileCompare(str(dst)))

    # a.txt and b.txt have identical content: exactly one of them is paired
    # as "moved" to c.txt, the other must still be reported as removed -
    # neither file may be silently dropped from the result.
    assert len(result.moved) == 1
    moved_sources = {source for source, _ in result.moved}
    assert moved_sources | result.removed == {"a.txt", "b.txt"}
    assert not result.added


def test_compare_duplicate_added_content_keeps_surplus_as_added(
    tmp_path: Path,
) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"

    write(src / "x.txt", "duplicate content")
    write(dst / "y.txt", "duplicate content")
    write(dst / "z.txt", "duplicate content")

    result = FileCompare(str(src)).compare(FileCompare(str(dst)))

    # y.txt and z.txt have identical content: exactly one of them is paired
    # as "moved" from x.txt, the other must still be reported as added -
    # neither file may be silently dropped from the result.
    assert len(result.moved) == 1
    moved_destinations = {destination for _, destination in result.moved}
    assert moved_destinations | result.added == {"y.txt", "z.txt"}
    assert not result.removed


# ---------------------------------------------------------------------------
# FileCompare.__eq__ / FileCompareResult.__bool__
# ---------------------------------------------------------------------------


def test_eq_true_for_identical_directories(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    write(src / "a.txt", "hello")
    write(dst / "a.txt", "hello")

    assert FileCompare(str(src)) == FileCompare(str(dst))


def test_eq_false_for_differing_directories(tmp_path: Path) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    write(src / "a.txt", "hello")
    write(dst / "a.txt", "changed")

    assert FileCompare(str(src)) != FileCompare(str(dst))


def test_eq_not_implemented_for_other_types() -> None:
    assert FileCompare("some/path").__eq__(object()) is NotImplemented


# ---------------------------------------------------------------------------
# FileCompareResult.print_result
# ---------------------------------------------------------------------------


def test_print_result_output(capsys: pytest.CaptureFixture[str]) -> None:
    result = FileCompareResult(
        removed={"gone.txt"},
        moved=[("old.txt", "new.txt")],
        added={"new_file.txt"},
        modified={"changed.txt"},
    )

    result.print_result()
    output = capsys.readouterr().out

    assert "- gone.txt" in output
    assert "> old.txt -> new.txt" in output
    assert "+ new_file.txt" in output
    assert "* changed.txt" in output


def test_print_result_prints_nothing_when_empty(
    capsys: pytest.CaptureFixture[str],
) -> None:
    result = FileCompareResult(removed=set(), moved=[], added=set(), modified=set())
    result.print_result()
    assert capsys.readouterr().out == ""
