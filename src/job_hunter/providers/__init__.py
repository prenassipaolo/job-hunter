"""Provider registry. Add a class here and it becomes selectable from the CLI."""

from __future__ import annotations

from .adzuna import AdzunaProvider
from .arbeitnow import ArbeitnowProvider
from .ats import ATSProvider
from .base import Provider
from .jobicy import JobicyProvider
from .remoteok import RemoteOKProvider
from .themuse import TheMuseProvider

ALL_PROVIDERS: dict[str, type[Provider]] = {
    "themuse": TheMuseProvider,
    "remoteok": RemoteOKProvider,
    "arbeitnow": ArbeitnowProvider,
    "jobicy": JobicyProvider,
    "ats": ATSProvider,
    "adzuna": AdzunaProvider,
}

__all__ = ["ALL_PROVIDERS", "Provider"]
