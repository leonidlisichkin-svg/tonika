"""The HTTP API: a thin, stateless wrapper over :func:`tonika.analyze` and :func:`tonika.render`.

Needs the optional extra ``api`` (FastAPI and uvicorn). The core never imports this package.
The contract is ``docs/specs/api-v1.md``.
"""

from __future__ import annotations

from tonika.server.app import create_app
from tonika.server.settings import Settings

__all__ = ["Settings", "create_app"]
