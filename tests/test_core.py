"""Unit tests for the folderdiff core module."""

import hashlib
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

    names = {entry[0] for entry in hashlist}
    assert names == {"a.txt", str(Path("sub") / "b.txt")}


def test_get_hashlist_raises_for_unsupported_path(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    with pytest.raises(ValueError, match="not supported filetype"):
        FileCompare(str(missing)).get_hashlist()


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
