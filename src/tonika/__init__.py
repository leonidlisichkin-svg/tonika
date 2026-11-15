"""Tonika: an open pronunciation layer for any TTS engine."""

from tonika.dictionary import DictionaryError, UserDictionary
from tonika.document import IntentDocument, IntentDocumentError, Reading, Token
from tonika.pipeline import analyze, annotate
from tonika.render import MODES, NOTATIONS, render
from tonika.review import review

__version__ = "0.0.1"

__all__ = [
    "MODES",
    "NOTATIONS",
    "DictionaryError",
    "IntentDocument",
    "IntentDocumentError",
    "Reading",
    "Token",
    "UserDictionary",
    "__version__",
    "analyze",
    "annotate",
    "render",
    "review",
]
