from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from tonika import __version__
from tonika.cli import main

PROOF = ["annotate", "--lang", "ru", "--target", "plus", "В старом замке сломался замок."]


def test_proof_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(PROOF) == 0
    captured = capsys.readouterr()
    assert captured.out == "В старом з+амке сломался зам+ок.\n"
    assert "demo pack" in captured.err


def test_explicit_fake_pack_is_quiet(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([*PROOF, "--pack", "fake"]) == 0
    assert capsys.readouterr().err == ""


def test_json_output(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([*PROOF, "--format", "json", "--pack", "fake"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["model"] == "fake-0"
    assert [t["form"] for t in data["tokens"]] == ["старом", "замке", "сломался", "замок"]


def test_file_input_keeps_layout(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    script = tmp_path / "script.txt"
    script.write_text("Глава 1\n\nСтарый замок.\n", encoding="utf-8")
    assert main(["annotate", "-f", str(script), "--target", "plus", "--pack", "fake"]) == 0
    assert capsys.readouterr().out == "Глава 1\n\nСтарый зам+ок.\n"


def test_stdin_input(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO("замок"))
    assert main(["annotate", "--target", "upper", "--pack", "fake"]) == 0
    assert capsys.readouterr().out == "замОк"


def test_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["annotate", "--lang", "xx", "hello"]) == 1
    assert "no language pack" in capsys.readouterr().err
    assert main(["annotate", "-f", str(tmp_path / "missing.txt")]) == 1
    assert "cannot read" in capsys.readouterr().err
    assert main(["annotate", "text", "-f", "file.txt"]) == 2


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert __version__ in capsys.readouterr().out
