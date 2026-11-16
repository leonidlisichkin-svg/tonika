from __future__ import annotations

from tonika import IntentDocument, analyze, review


def test_review_lists_ambiguous_words(proof_document: IntentDocument) -> None:
    assert review(proof_document) == (
        "Words to check: 2\n\n"
        "- …В старом **з+амке** сломался замок.… (or: замк+е)\n"
        "- …В старом замке сломался **зам+ок**.… (or: з+амок)\n"
    )


def test_review_shows_respelling_and_flattens_line_breaks() -> None:
    document = analyze("Он знал\nвсе.", pack="fake")
    assert review(document) == "Words to check: 1\n\n- …Он знал **вс+ё**.… (or: вс+е)\n"


def test_review_with_nothing_to_check() -> None:
    assert review(analyze("Дверь.", pack="fake")) == "No ambiguous words.\n"
