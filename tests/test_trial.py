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
from tonika.trial import Reference, check_preserved, load_reference, restore, run_trial

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


# Drift across machines ------------------------------------------------------------------------


def test_the_digest_covers_the_decisions_and_nothing_else() -> None:
    from dataclasses import replace

    from tonika.trial import token_digest

    document = analyze("В старом замке сломался замок.", pack="fake")
    digest = token_digest(document)
    assert len(digest) == 64
    assert token_digest(replace(document, model="other")) == digest
    changed = replace(document.tokens[0], reading=Reading(stress=(1,)))
    assert token_digest(replace(document, tokens=(changed, *document.tokens[1:]))) != digest
    first = run_trial("В старом замке сломался замок.", FakePack("ru"))
    second = run_trial("В старом замке сломался замок.", FakePack("ru"))
    assert first.digest == second.digest == digest


INTEL = """processor\t: 0
vendor_id\t: GenuineIntel
model name\t: Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz
flags\t\t: fpu sse sse2 ssse3 cx16 sse4_1 sse4_2 popcnt lahf_lm avx avx2 bmi1 bmi2 f16c fma abm \
movbe xsave avx512f avx512dq avx512cd avx512bw avx512vl avx512_vnni

processor\t: 1
model name\t: ignored, the first block counts
"""
AMD = """model name\t: AMD EPYC 7763 64-Core Processor
flags\t\t: sse sse2 ssse3 cx16 sse4_1 sse4_2 popcnt lahf_lm avx avx2 bmi1 bmi2 f16c fma abm \
movbe xsave
"""
ARM = """processor\t: 0
BogoMIPS\t: 50.00
Features\t: fp asimd evtstrm aes sve i8mm
"""


@pytest.mark.parametrize(
    ("info", "machine", "expected"),
    [
        (
            INTEL,
            "x86_64",
            (
                "Intel(R) Xeon(R) Platinum 8370C CPU @ 2.80GHz",
                "x86-64-v4 (avx512_vnni)",
            ),
        ),
        (AMD, "x86_64", ("AMD EPYC 7763 64-Core Processor", "x86-64-v3")),
        ("model name : Old\nflags : sse sse2\n", "x86_64", ("Old", "x86-64")),
        (ARM, "aarch64", ("unknown", "aarch64 (sve, i8mm)")),
        ("", "", ("unknown", "unknown")),
    ],
)
def test_the_processor_is_read_from_cpuinfo(
    info: str, machine: str, expected: tuple[str, str]
) -> None:
    from tonika.trial import parse_cpuinfo

    assert parse_cpuinfo(info, machine) == expected


def test_the_report_names_the_processor_and_the_digest() -> None:
    report = run_trial("Замок.", FakePack("ru"))
    data = report.to_dict()
    assert {"digest", "cpu", "isa"} <= set(data)
    assert "document" not in data
    assert f"`{report.digest}`" in report.to_markdown()
    assert "| Processor |" in report.to_markdown()


def test_cli_trial_writes_the_document(tmp_path: Path) -> None:
    text = tmp_path / "text.txt"
    text.write_text("В старом замке сломался замок.\r\n", encoding="utf-8", newline="")
    target = tmp_path / "doc.json"
    assert main(["trial", str(text), "--pack", "fake", "--document", str(target)]) == 0
    document = IntentDocument.from_json(target.read_text(encoding="utf-8"))
    assert document.text == "В старом замке сломался замок.\r\n"


def _reference(words_marked: int, model: str = "fake-0", digest: str = "x" * 64) -> Reference:
    return Reference(model=model, digest=digest, words_marked=words_marked)


def test_the_same_decisions_as_the_reference_pass() -> None:
    first = run_trial("В старом замке сломался замок.", FakePack("ru"))
    report = run_trial(
        "В старом замке сломался замок.",
        FakePack("ru"),
        reference=_reference(first.words_marked, digest=first.digest),
    )
    assert report.compared and report.drift == 0.0 and report.passed
    assert "the same decisions" in report.to_markdown()


DOORS = " ".join(["Дверь."] * 1001)  # the demo pack gives stress to every "дверь"


@pytest.mark.parametrize(
    ("expected", "passed"),
    [(1001, True), (1000, True), (1002, True), (999, False), (1010, False)],
)
def test_drift_beyond_the_limit_fails(expected: int, passed: bool) -> None:
    # 1,001 words given stress: one word off 1,000 is exactly 0.1%, two off 999 is over it.
    report = run_trial(DOORS, FakePack("ru"), reference=_reference(expected))
    assert report.words_marked == 1001
    assert report.passed is passed
    assert ("**OVER**" in report.to_markdown()) is not passed


def test_a_reference_for_another_model_is_not_compared() -> None:
    report = run_trial("Замок.", FakePack("ru"), reference=_reference(99, model="other"))
    assert not report.compared and report.drift is None and report.passed
    assert "not compared" in report.to_markdown()


def test_cli_trial_fails_on_drift(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = tmp_path / "text.txt"
    text.write_text("В старом замке сломался замок.", encoding="utf-8")
    reference = tmp_path / "reference.json"
    entry = {"model": "fake-0", "digest": "x", "words_marked": 40}
    reference.write_text(json.dumps({"text.txt": entry}), encoding="utf-8")
    assert main(["trial", str(text), "--pack", "fake", "--reference", str(reference)]) == 1
    assert "**OVER**" in capsys.readouterr().out
    reference.write_text(json.dumps({"other.txt": entry}), encoding="utf-8")
    assert main(["trial", str(text), "--pack", "fake", "--reference", str(reference)]) == 0


def test_the_reference_file_names_the_trial_text() -> None:
    reference = load_reference(TRIAL.parent.parent / "reference.json", TRIAL.name)
    assert reference is not None
    assert reference.model.startswith("stressonnx-")
    assert len(reference.digest) == 64
