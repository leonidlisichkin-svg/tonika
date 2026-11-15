"""Tonika: an open pronunciation layer for any TTS engine."""

from tonika.document import IntentDocument, IntentDocumentError, Reading, Token
from tonika.pipeline import analyze, annotate
from tonika.render import MODES, NOTATIONS, render

__version__ = "0.0.1"

__all__ = [
    "MODES",
    "NOTATIONS",
    "IntentDocument",
    "IntentDocumentError",
    "Reading",
    "Token",
    "__version__",
    "analyze",
    "annotate",
    "render",
]
