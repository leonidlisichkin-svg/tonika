from __future__ import annotations

import json
from pathlib import Path

import pytest

from tonika import analyze, render
from tonika.cli import main
from tonika.document import IntentDocument, Reading, Token
from tonika.packs import FakePack
from tonika.render import MODES, NOTATIONS
from tonika.text import COMBINING_ACUTE
from tonika.trial import check_preserved, restore, run_trial

TRIAL = Path(__file__).parent.parent / "data" / "trials" / "ru" / "chekhov-lady-with-the-dog.txt"
COMBINATIONS = [(notation, mode) for notation in NOTATIONS for mode in MODES]


def _read(path: Path) -> str:
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


# The whole trial text with the demo pack -------------------------------------------------


@pytest.fixture(scope="module")
def trial_text() -> str:
    return _read(TRIAL)


def test_the_trial_text_is_preserved_in_every_notation_and_mode(trial_text: str) -> None:
    report = run_trial(trial_text, FakePack("ru"), name=TRIAL.name)
    assert report.preserved, report.difference
    assert report.first_difference is None
    assert set(report.checked) == set(COMBINATIONS)
    assert report.characters == len(trial_text)
    # The demo pack knows "все" and "еще", which the text spells with е, so ё is restored and
    # the check has respellings to undo.
    assert report.yo_respellings > 0
    assert report.model == "fake-0"


def test_the_trial_text_gives_the_same_output_twice(trial_text: str) -> None:
    first = analyze(trial_text, pack="fake")
    second = analyze(trial_text, pack="fake")
    assert first.to_json() == second.to_json()
    for notation, mode in COMBINATIONS:
        assert render(first, notation, mode) == render(second, notation, mode)


def test_the_trial_text_is_as_documented(trial_text: str) -> None:
    import unicodedata

    assert unicodedata.is_normalized("NFC", trial_text)
    assert 30_000 <= len(trial_text) <= 45_000
    assert "\r" not in trial_text
    # No footnote anchors, wiki markup or editors' notes survived the cleaning.
    for leftover in ("{{", "}}", "[[", "]]", "''", "<ref", "&nbsp;", "Примечание"):
        assert leftover not in trial_text


# The check itself ---------------------------------------------------------------------------

TRICKY = (
    "ВСЕ знали: 2+2 = 4, а A+B не слово.\r\n"
    "В старом замке сломался замок, — и з+амок, и замо́к; ещё еще.\n\n"
    "\tВсе ушли…  "
)


@pytest.mark.parametrize(("notation", "mode"), COMBINATIONS)
def test_layout_case_plus_and_author_marks_survive(notation: str, mode: str) -> None:
    document = analyze(TRICKY, pack="fake")
    assert check_preserved(TRICKY, document, [(notation, mode)]) is None


def test_a_literal_plus_is_not_taken_for_a_mark() -> None:
    document = analyze("2+2 и з+амок", pack="fake")
    output = render(document, "plus", "all")
    assert restore(document, output, "plus") == "2+2 и з+амок"


def _document(text: str, *tokens: Token) -> IntentDocument:
    return IntentDocument(lang="ru", model="test", text=text, tokens=tokens)


ZAMOK = _document(
    "Новый замок.",
    Token(6, 11, "замок", Reading(stress=(3,)), alternatives=(Reading(stress=(1,)),)),
)
VSE = _document("Все тут.", Token(0, 3, "Все", Reading(stress=(2,), respell="Всё"), kind="yo"))


@pytest.mark.parametrize(
    ("document", "notation", "output", "position"),
    [
        # A mark where the document puts none.
        (ZAMOK, "plus", "Новый з+амок.", 7),
        (ZAMOK, "acute", f"Новый за{COMBINING_ACUTE}мок.", 8),
        # Upper case outside the stressed letter.
        (ZAMOK, "upper", "Новый ЗамОк.", 6),
        (ZAMOK, "upper", "НОвый замОк.", 1),
        # A space, a line break or a punctuation mark lost or added.
        (ZAMOK, "plus", "Новый  зам+ок.", 6),
        (ZAMOK, "plus", "Новый\nзам+ок.", 5),
        (ZAMOK, "plus", "Новый зам+ок", 11),
        (ZAMOK, "plus", "Новый зам+ок!", 11),
        # A letter changed, inside or outside a token.
        (ZAMOK, "acute", f"Новый замо{COMBINING_ACUTE}г.", 10),
        (ZAMOK, "acute", f"Новий замо{COMBINING_ACUTE}к.", 3),
        # A respelling that is not the one recorded.
        (VSE, "plus", "Всю тут.", 2),
        (VSE, "yo", "Вс тут.", 2),
    ],
)
def test_a_change_beyond_the_marks_is_caught(
    document: IntentDocument, notation: str, output: str, position: int
) -> None:
    restored = restore(document, output, notation)
    assert restored != document.text
    first = next(
        (i for i, (a, b) in enumerate(zip(document.text, restored, strict=False)) if a != b),
        min(len(document.text), len(restored)),
    )
    assert first == position


@pytest.mark.parametrize(
    ("document", "notation", "output"),
    [
        (ZAMOK, "plus", "Новый зам+ок."),
        (ZAMOK, "plus", "Новый замок."),
        (ZAMOK, "acute", f"Новый замо{COMBINING_ACUTE}к."),
        (ZAMOK, "upper", "Новый замОк."),
        (ZAMOK, "yo", "Новый замок."),
        (VSE, "plus", "Вс+ё тут."),
        (VSE, "upper", "ВсЁ тут."),
        (VSE, "yo", "Всё тут."),
        (VSE, "yo", "Все тут."),
    ],
)
def test_the_marks_and_respellings_the_document_records_are_undone(
    document: IntentDocument, notation: str, output: str
) -> None:
    assert restore(document, output, notation) == document.text


def test_a_broken_renderer_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(document: IntentDocument, target: str = "acute", mode: str = "ambiguous") -> str:
        out = render(document, target, mode)
        return out.replace(" ", "  ", 1) if (target, mode) == ("upper", "all") else out

    monkeypatch.setattr("tonika.trial.render", broken)
    report = run_trial("В старом замке сломался замок.", FakePack("ru"))
    assert not report.preserved
    assert report.difference is not None
    assert (report.difference.notation, report.difference.mode) == ("upper", "all")
    assert report.first_difference == 2  # "В " then the extra space
    assert "NO" in report.to_markdown()


def test_text_that_is_not_nfc_counts_as_changed() -> None:
    text = "ёще"  # ё typed as е plus a combining diaeresis
    report = run_trial(text, FakePack("ru"))
    assert not report.preserved
    assert report.first_difference == 0


# Numbers and the command line ---------------------------------------------------------------


def test_report_numbers() -> None:
    report = run_trial("В старом замке сломался замок. Все еще тут.", FakePack("ru"))
    assert report.words == 8
    assert report.words_marked == 6  # старом замке сломался замок все еще
    assert report.words_to_review == 3  # замке замок все
    assert report.review_per_1000_words == pytest.approx(375.0)
    assert report.yo_respellings == 2  # всё ещё
    data = report.to_dict()
    assert data["preserved"] is True
    assert data["first_difference"] is None
    assert json.loads(json.dumps(data)) == data


def test_cli_trial(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "text.txt"
    path.write_bytes(TRICKY.encode("utf-8"))
    assert main(["trial", str(path), "--pack", "fake"]) == 0
    out = capsys.readouterr().out
    assert "### Tonika trial: `text.txt`" in out
    assert "| Text preserved | yes, in all 4 notations × 3 modes |" in out

    assert main(["trial", str(path), "--pack", "fake", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["preserved"] is True
    assert data["characters"] == len(TRICKY)


def test_cli_trial_fails_when_the_text_changes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("tonika.trial.render", lambda document, target, mode: "")
    path = tmp_path / "text.txt"
    path.write_text("Замок.", encoding="utf-8")
    assert main(["trial", str(path), "--pack", "fake"]) == 1
    assert "**NO**" in capsys.readouterr().out
