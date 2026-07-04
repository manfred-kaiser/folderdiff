"""Unit tests for the folderdiff CLI."""

import sys
from pathlib import Path

import pytest
from conftest import make_zip, write

from folderdiff.cli import main


def test_main_returns_none_for_identical_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    write(src / "a.txt", "hello")
    write(dst / "a.txt", "hello")

    monkeypatch.setattr(sys, "argv", ["folderdiff", str(src), str(dst)])

    assert main() is None


def test_main_exits_one_and_prints_differences(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    write(src / "a.txt", "hello")
    write(dst / "a.txt", "hello")
    write(dst / "webshell.php", "evil")

    monkeypatch.setattr(sys, "argv", ["folderdiff", str(src), str(dst)])

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    assert "+ webshell.php" in capsys.readouterr().out


def test_main_prefix_option_strips_zip_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    zip_root = tmp_path / "zip_root"
    write(zip_root / "wordpress" / "index.php", "index")

    zip_path = tmp_path / "wordpress.zip"
    make_zip(zip_path, zip_root)

    live = tmp_path / "live"
    write(live / "index.php", "index")
    write(live / "webshell.php", "evil")

    monkeypatch.setattr(
        sys,
        "argv",
        ["folderdiff", str(zip_path), str(live), "--prefix", "wordpress/"],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
    assert "+ webshell.php" in capsys.readouterr().out
