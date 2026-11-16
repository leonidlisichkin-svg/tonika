"""Command line: ``tonika annotate``, ``tonika eval``, ``tonika trial``, ``tonika engines``."""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from collections.abc import Sequence
from pathlib import Path

from tonika import __version__
from tonika.dictionary import DictionaryError, UserDictionary
from tonika.document import IntentDocumentError
from tonika.engines import UnknownEngineError, list_engines, resolve_target
from tonika.evaluate import ExampleError, evaluate, load_examples, minimum_accuracy
from tonika.packs import DemoPackWarning, LanguagePack, PackError, UnknownPackError, get_pack
from tonika.pipeline import analyze_with, default_mode
from tonika.render import MODES, NOTATIONS, render
from tonika.review import review
from tonika.trial import run_trial

_ERRORS = (
    UnknownPackError,
    UnknownEngineError,
    PackError,
    DictionaryError,
    ExampleError,
    IntentDocumentError,
    ValueError,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tonika",
        description="Open pronunciation layer for any TTS engine.",
    )
    parser.add_argument("--version", action="version", version=f"tonika {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    annotate = commands.add_parser(
        "annotate",
        help="mark pronunciation in text for a TTS engine",
        description=(
            "Read text from an argument, a file or standard input and print it marked for a TTS "
            "engine. Everything outside the marked words is copied unchanged."
        ),
    )
    annotate.add_argument("text", nargs="?", help="text to annotate; omit to use --file or stdin")
    annotate.add_argument("-f", "--file", type=Path, help="read UTF-8 text from this file")
    annotate.add_argument("-o", "--output", type=Path, help="write the result to this file")
    annotate.add_argument("--lang", default="ru", help="language tag (default: ru)")
    annotate.add_argument(
        "--target",
        default="acute",
        help=f"a notation ({', '.join(NOTATIONS)}) or an engine id, see 'tonika engines' "
        "(default: acute)",
    )
    annotate.add_argument(
        "--mode",
        choices=MODES,
        help="what to mark: ambiguous words, all words, or only ё "
        "(default: ambiguous when the language pack knows ambiguity, else all)",
    )
    annotate.add_argument(
        "--dict",
        dest="dictionaries",
        action="append",
        type=Path,
        default=[],
        metavar="FILE",
        help="user dictionary of forced readings; may be given more than once",
    )
    annotate.add_argument(
        "--review",
        type=Path,
        metavar="FILE",
        help="also write a checklist of ambiguous words to this file",
    )
    annotate.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="text for TTS, or the Intent Document as JSON (default: text)",
    )
    annotate.add_argument("--pack", default="auto", help="language pack (default: auto)")

    evaluation = commands.add_parser(
        "eval",
        help="measure a language pack against sentences with known readings",
        description="Measure accuracy on a .txt file of marked sentences or a .jsonl example file.",
    )
    evaluation.add_argument("examples", type=Path, help="file of examples")
    evaluation.add_argument("--lang", default="ru", help="language tag (default: ru)")
    evaluation.add_argument("--pack", default="auto", help="language pack (default: auto)")
    evaluation.add_argument(
        "--format", choices=("md", "json"), default="md", help="report format (default: md)"
    )
    evaluation.add_argument(
        "--baseline", type=Path, help="JSON file with the accuracy floor per language"
    )
    evaluation.add_argument("--min-accuracy", type=float, help="fail below this accuracy (0 to 1)")

    trial = commands.add_parser(
        "trial",
        help="run a long text through Tonika and check that only pronunciation marks change",
        description=(
            "Analyse a text once, render it in every notation and mode, and check that undoing "
            "the marks and ё gives the text back exactly. Prints speed, memory and the number "
            "of words to review. Exits with 1 when the text is not preserved."
        ),
    )
    trial.add_argument("file", type=Path, help="UTF-8 text file")
    trial.add_argument("--lang", default="ru", help="language tag (default: ru)")
    trial.add_argument("--pack", default="auto", help="language pack (default: auto)")
    trial.add_argument(
        "--format", choices=("md", "json"), default="md", help="report format (default: md)"
    )
    trial.add_argument(
        "--document",
        type=Path,
        metavar="FILE",
        help="also write the Intent Document the trial checked to this file (JSON)",
    )

    commands.add_parser("engines", help="list TTS engine presets")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    # Text passes through unchanged, line endings included: newline="" stops Python from turning
    # CR LF into LF on input and LF into the system's line ending on output.
    reconfigure = getattr(sys.stdin, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(newline="")
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", newline="")
    args = build_parser().parse_args(argv)
    try:
        if args.command == "annotate":
            return _annotate(args)
        if args.command == "eval":
            return _eval(args)
        if args.command == "trial":
            return _trial(args)
        return _engines()
    except OSError as exc:
        print(f"tonika: {exc.filename or 'file'}: {exc.strerror or exc}", file=sys.stderr)
        return 1
    except _ERRORS as exc:
        print(f"tonika: {exc}", file=sys.stderr)
        return 1


def _pack(lang: str, name: str) -> LanguagePack:
    """Get a pack, turning the demo-pack warning into a line on stderr."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DemoPackWarning)
        pack = get_pack(lang, name)
    for warning in caught:
        if issubclass(warning.category, DemoPackWarning):
            print(f"tonika: warning: {warning.message}", file=sys.stderr)
    return pack


def _read(path: Path) -> str:
    """Read a UTF-8 file with every line ending kept as it is."""
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


def _annotate(args: argparse.Namespace) -> int:
    if args.text is not None and args.file is not None:
        print("tonika: give text or --file, not both", file=sys.stderr)
        return 2
    notation = resolve_target(args.target)
    dictionary = UserDictionary.load(*args.dictionaries) if args.dictionaries else None
    if args.text is not None:
        text, from_argument = args.text, True
    elif args.file is not None:
        text, from_argument = _read(args.file), False
    else:
        text, from_argument = sys.stdin.read(), False

    pack = _pack(args.lang, args.pack)
    document = analyze_with(pack, text, dictionary)
    if args.format == "json":
        output = document.to_json() + "\n"
    else:
        output = render(document, notation, args.mode or default_mode(pack))
        if from_argument:
            output += "\n"

    if args.review is not None:
        args.review.write_text(review(document), encoding="utf-8")
    if args.output is not None:
        with args.output.open("w", encoding="utf-8", newline="") as handle:
            handle.write(output)
    else:
        sys.stdout.write(output)
    return 0


def _eval(args: argparse.Namespace) -> int:
    examples = load_examples(args.examples)
    report = evaluate(examples, _pack(args.lang, args.pack))
    floor = args.min_accuracy
    if floor is None and args.baseline is not None:
        floor = minimum_accuracy(args.baseline, args.lang)
    passed = floor is None or report.accuracy >= floor

    if args.format == "json":
        data = report.to_dict()
        data["min_accuracy"] = floor
        data["passed"] = passed
        sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(report.to_markdown())
        if floor is not None:
            verdict = "at or above" if passed else "**below**"
            sys.stdout.write(f"\nAccuracy is {verdict} the floor of {floor:.1%}.\n")
    return 0 if passed else 1


def _trial(args: argparse.Namespace) -> int:
    text = _read(args.file)
    report = run_trial(text, _pack(args.lang, args.pack), name=args.file.name)
    if args.document is not None and report.document is not None:
        with args.document.open("w", encoding="utf-8", newline="") as handle:
            handle.write(report.document.to_json() + "\n")
    if args.format == "json":
        sys.stdout.write(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(report.to_markdown())
    return 0 if report.preserved else 1


def _engines() -> int:
    for engine in list_engines():
        checked = (
            "unverified"
            if engine.verified_by == "unverified"
            else f"verified by {engine.verified_by} on {engine.verified_on}"
        )
        languages = ", ".join(engine.languages)
        sys.stdout.write(
            f"{engine.id}\n  {engine.name}: notation {engine.notation}; "
            f"languages {languages}; {checked}\n"
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
