"""The stressonnx pack, driven by a scripted backend instead of real models."""

from __future__ import annotations

import pytest

from helpers import PROOF_TEXT, ScriptedBackend
from tonika.document import Reading, Token
from tonika.packs import LanguagePack, PackError, StressonnxPack
from tonika.pipeline import analyze_with, default_mode
from tonika.render import render

READINGS = {
    "старом": "ст+аром",
    "замке": "з+амке",
    "сломался": "слом+ался",
    "замок": "зам+ок",
    "стоял": "сто+ял",
    "дверь": "дв+ерь",
    "еще": "ещ+ё",
}
HOMOGRAPHS = {"замок": ["з+амок", "зам+ок"], "замке": ["з+амке", "замк+е"]}


def pack(
    backend: ScriptedBackend, lang: str = "ru", *, lowercase: bool | None = None
) -> StressonnxPack:
    return StressonnxPack(lang, backend=backend, lowercase=lowercase)


def shown(tokens: list[Token]) -> list[tuple[str, tuple[int, ...], tuple[Reading, ...]]]:
    return [(t.form, t.reading.stress, t.alternatives) for t in tokens]


def test_follows_the_protocol() -> None:
    russian = pack(ScriptedBackend({}))
    assert isinstance(russian, LanguagePack)
    assert (russian.lang, russian.tier, russian.demo) == ("ru", "A", False)
    assert russian.model == "stressonnx:custom"
    assert default_mode(russian) == "ambiguous"


def test_marks_become_tokens_and_homographs_get_alternatives() -> None:
    backend = ScriptedBackend(READINGS, homographs=HOMOGRAPHS)
    assert shown(pack(backend).analyze(PROOF_TEXT)) == [
        ("старом", (2,), ()),
        ("замке", (1,), (Reading(stress=(4,)),)),
        ("сломался", (4,), ()),
        ("замок", (3,), (Reading(stress=(1,)),)),
    ]


def test_render_through_the_pipeline() -> None:
    backend = ScriptedBackend(READINGS, homographs=HOMOGRAPHS)
    document = analyze_with(pack(backend), PROOF_TEXT)
    assert document.model == "stressonnx:custom"
    assert render(document, "plus", "ambiguous") == "В старом з+амке сломался зам+ок."
    assert render(document, "plus", "all") == "В ст+аром з+амке слом+ался зам+ок."


def test_russian_text_is_fed_lowercased_and_case_survives() -> None:
    backend = ScriptedBackend(READINGS, homographs=HOMOGRAPHS)
    document = analyze_with(pack(backend), "Замок стоял. ЗАМОК!")
    assert backend.calls == ["замок стоял. ", "замок!"]
    assert render(document, "plus", "all") == "Зам+ок сто+ял. ЗАМ+ОК!"


def test_lowercasing_can_be_turned_off() -> None:
    backend = ScriptedBackend(READINGS)
    pack(backend, lowercase=False).analyze("Замок стоял.")
    assert backend.calls == ["Замок стоял."]


def test_a_mark_on_the_only_vowel_is_dropped() -> None:
    assert pack(ScriptedBackend(READINGS)).analyze("Дверь.") == []


def test_yo_is_restored_with_the_case_of_the_text() -> None:
    document = analyze_with(pack(ScriptedBackend(READINGS)), "Еще раз и еще.")
    assert [(t.form, t.surface, t.kind, t.reading.stress) for t in document.tokens] == [
        ("Еще", "Ещё", "yo", (2,)),
        ("еще", "ещё", "yo", (2,)),
    ]
    assert render(document, "plus", "yo") == "Ещё раз и ещё."


def test_an_unmarked_word_with_yo_is_stressed_on_it() -> None:
    backend = ScriptedBackend(
        {"звезды": "звёзды", "звёзды": "звёзды", "трехколесный": "трёхколёсный"}
    )
    tokens = pack(backend).analyze("Звезды и звёзды, трехколесный.")
    assert [(t.form, t.surface, t.reading.stress) for t in tokens] == [
        ("Звезды", "Звёзды", (2,)),
        ("звёзды", "звёзды", (2,)),
        # Two ё: the pack does not guess which one carries the main stress.
        ("трехколесный", "трёхколёсный", ()),
    ]


def test_yo_homograph_kept_as_written_offers_the_other_spelling() -> None:
    backend = ScriptedBackend({}, yo_homographs={"все": "всё", "берет": "берёт"})
    tokens = pack(backend).analyze("Все берет.")
    assert shown(tokens) == [
        ("Все", (), (Reading(respell="Всё"),)),
        ("берет", (), (Reading(stress=(3,), respell="берёт"),)),
    ]
    # Nothing is decided, so nothing is marked.
    assert render(analyze_with(pack(backend), "Все берет."), "plus") == "Все берет."


def test_yo_homograph_restored_offers_the_spelling_as_written() -> None:
    backend = ScriptedBackend({"все": "вс+ё"}, yo_homographs={"все": "всё"})
    tokens = pack(backend).analyze("Он знал все.")
    assert [(t.form, t.surface, t.reading.stress, t.alternatives) for t in tokens] == [
        ("все", "всё", (), (Reading(),))
    ]


def test_reading_outside_the_dictionary_keeps_every_variant_as_alternative() -> None:
    backend = ScriptedBackend({"замок": "зам+ок"}, homographs={"замок": ["з+амок"]})
    tokens = pack(backend).analyze("замок")
    assert shown(tokens) == [("замок", (3,), (Reading(stress=(1,)),))]


def test_unmarked_homograph_is_still_reported() -> None:
    backend = ScriptedBackend({}, homographs=HOMOGRAPHS)
    assert shown(pack(backend).analyze("замок")) == [
        ("замок", (), (Reading(stress=(1,)), Reading(stress=(3,))))
    ]


def test_variants_with_stress_on_a_consonant_are_ignored() -> None:
    backend = ScriptedBackend(READINGS, homographs={"замок": ["з+амок", "зам+ок", "замо+к"]})
    assert shown(pack(backend).analyze("замок")) == [("замок", (3,), (Reading(stress=(1,)),))]


def test_without_private_dictionaries_there_are_no_alternatives() -> None:
    tokens = pack(ScriptedBackend(READINGS)).analyze(PROOF_TEXT)
    assert all(not token.is_ambiguous for token in tokens)
    assert len(tokens) == 4


def test_malformed_private_dictionaries_are_ignored() -> None:
    backend = ScriptedBackend(READINGS)
    backend._omographs = {"замок": "not a list", "замке": [1, "зам+ке", "другое+"]}  # type: ignore[dict-item]
    backend._yo_homographs = ["not a mapping"]  # type: ignore[assignment]
    tokens = pack(backend).analyze(PROOF_TEXT)
    assert shown(tokens)[1] == ("замке", (1,), ())


def test_backend_that_drops_characters() -> None:
    backend = ScriptedBackend(READINGS, homographs=HOMOGRAPHS, lossy=True)
    text = "Замок… стоял , как прежде 🙂! Еще замок — и всё."
    document = analyze_with(pack(backend), text)
    assert render(document, "plus", "all") == (
        "Зам+ок… сто+ял , как прежде 🙂! Ещ+ё зам+ок — и всё."
    )


def test_long_text_goes_sentence_by_sentence() -> None:
    backend = ScriptedBackend(READINGS, homographs=HOMOGRAPHS)
    text = "Замок стоял. " * 50
    document = analyze_with(pack(backend), text)
    assert len(backend.calls) == 50
    assert len(document.tokens) == 100
    assert render(document, "plus", "ambiguous") == "Зам+ок стоял. " * 50


def test_chunks_without_letters_skip_the_model() -> None:
    backend = ScriptedBackend(READINGS)
    assert pack(backend).analyze("123... 456!\n\n— — —") == []
    assert backend.calls == []


def test_other_languages_are_tier_b_and_keep_their_case() -> None:
    backend = ScriptedBackend({"привіт": "прив+іт", "світ": "св+іт", "қазақстан": "қазақст+ан"})
    ukrainian = pack(backend, "uk")
    assert (ukrainian.tier, default_mode(ukrainian)) == ("B", "all")
    document = analyze_with(ukrainian, "Привіт світ")
    assert backend.calls == ["Привіт світ"]
    assert render(document, "acute", "all") == "Приві́т світ"

    kazakh = pack(backend, "kk")
    assert render(analyze_with(kazakh, "Қазақстан"), "plus", "all") == "Қазақст+ан"


def test_backend_failure_becomes_a_pack_error() -> None:
    def broken(text: str) -> str:
        raise OSError("no network")

    with pytest.raises(PackError, match="no network"):
        StressonnxPack("ru", backend=broken).analyze("замок")
