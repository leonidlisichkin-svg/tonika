"""Command line: ``tonika annotate``."""

from __future__ import annotations

import argparse
import sys
import warnings
from collections.abc import Sequence
from pathlib import Path

from tonika import __version__
from tonika.document import IntentDocumentError
from tonika.packs import DemoPackWarning, UnknownPackError
from tonika.pipeline import analyze
from tonika.render import MODES, NOTATIONS, render


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
    annotate.add_argument("--lang", default="ru", help="language tag (default: ru)")
    annotate.add_argument(
        "--target", choices=NOTATIONS, default="acute", help="output notation (default: acute)"
    )
    annotate.add_argument(
        "--mode", choices=MODES, default="ambiguous", help="what to mark (default: ambiguous)"
    )
    annotate.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="text for TTS, or the Intent Document as JSON (default: text)",
    )
    annotate.add_argument("--pack", default="auto", help="language pack (default: auto)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    if args.command == "annotate":
        return _annotate(args)
    return 2  # pragma: no cover - argparse enforces a command


def _annotate(args: argparse.Namespace) -> int:
    if args.text is not None and args.file is not None:
        print("tonika: give text or --file, not both", file=sys.stderr)
        return 2
    if args.text is not None:
        text, from_argument = args.text, True
    elif args.file is not None:
        try:
            text = args.file.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"tonika: cannot read {args.file}: {exc.strerror}", file=sys.stderr)
            return 1
        from_argument = False
    else:
        text, from_argument = sys.stdin.read(), False

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", DemoPackWarning)
            document = analyze(text, lang=args.lang, pack=args.pack)
        for warning in caught:
            if issubclass(warning.category, DemoPackWarning):
                print(f"tonika: warning: {warning.message}", file=sys.stderr)
        if args.format == "json":
            output = document.to_json() + "\n"
        else:
            output = render(document, target=args.target, mode=args.mode)
            if from_argument:
                output += "\n"
    except (UnknownPackError, IntentDocumentError, ValueError) as exc:
        print(f"tonika: {exc}", file=sys.stderr)
        return 1

    sys.stdout.write(output)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
