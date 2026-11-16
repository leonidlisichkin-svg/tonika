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


def test_engine_target_dictionary_output_and_review(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    script = tmp_path / "script.txt"
    names = tmp_path / "names.dic"
    out = tmp_path / "out.txt"
    checklist = tmp_path / "review.md"
    script.write_text("Окленд. В старом замке сломался замок.\n", encoding="utf-8")
    names.write_text("+Окленд\n", encoding="utf-8")
    args = ["annotate", "-f", str(script), "--target", "yandex-speechkit", "--pack", "fake"]
    assert main([*args, "--dict", str(names), "-o", str(out), "--review", str(checklist)]) == 0
    assert capsys.readouterr().out == ""
    assert out.read_text(encoding="utf-8") == "+Окленд. В старом з+амке сломался зам+ок.\n"
    review = checklist.read_text(encoding="utf-8")
    assert review.startswith("Words to check: 2")
    assert "**з+амке**" in review and "(or: замк+е)" in review


def test_engines_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["engines"]) == 0
    out = capsys.readouterr().out
    assert "yandex-speechkit" in out and "notation plus" in out


def test_eval_command(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    golden = tmp_path / "golden.txt"
    golden.write_text("# demo\nВ старом з+амке сломался зам+ок.\nСтарого замк+а нет.\n", "utf-8")
    assert main(["eval", str(golden), "--pack", "fake"]) == 0
    assert "| Correct | 2 (66.7%) |" in capsys.readouterr().out

    assert main(["eval", str(golden), "--pack", "fake", "--min-accuracy", "0.9"]) == 1
    assert "**below** the floor of 90.0%" in capsys.readouterr().out

    baseline = tmp_path / "baseline.json"
    baseline.write_text('{"ru": {"min_accuracy": 0.5}}', "utf-8")
    command = ["eval", str(golden), "--pack", "fake", "--baseline", str(baseline)]
    assert main([*command, "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert (data["total"], data["correct"], data["passed"]) == (3, 2, True)
    assert data["failures"][0]["expected"] == "замк+а"


def test_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["annotate", "--lang", "xx", "hello"]) == 1
    assert "no language pack" in capsys.readouterr().err
    assert main(["annotate", "-f", str(tmp_path / "missing.txt")]) == 1
    assert "missing.txt: No such file" in capsys.readouterr().err
    assert main(["annotate", "text", "-f", "file.txt"]) == 2
    capsys.readouterr()
    assert main(["annotate", "--target", "ssml", "text"]) == 1
    assert "unknown target" in capsys.readouterr().err
    bad = tmp_path / "bad.dic"
    bad.write_text("Окленд\n", encoding="utf-8")
    assert main(["annotate", "--dict", str(bad), "--pack", "fake", "text"]) == 1
    assert "bad.dic:1: no stress mark" in capsys.readouterr().err
    empty = tmp_path / "empty.txt"
    empty.write_text("Без меток.\n", encoding="utf-8")
    assert main(["eval", str(empty), "--pack", "fake"]) == 1
    assert "no word carries a stress mark" in capsys.readouterr().err


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert __version__ in capsys.readouterr().out
