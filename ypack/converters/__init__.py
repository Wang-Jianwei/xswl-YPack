"""Converter implementations for packaging tools."""

from __future__ import annotations

from typing import Dict, Type

from .base import BaseConverter
from .convert_nsis import YamlToNsisConverter

# -----------------------------------------------------------------------
# Converter registry — maps format name → converter class.
# New backends (wix, inno, …) should be registered here.
# -----------------------------------------------------------------------

CONVERTER_REGISTRY: Dict[str, Type[BaseConverter]] = {
    "nsis": YamlToNsisConverter,
}

#: Formats for which ``--build`` is supported and the corresponding
#: external compiler command.
BUILD_COMMANDS: Dict[str, str] = {
    "nsis": "makensis",
}

#: Default output file extension per format.
OUTPUT_EXTENSIONS: Dict[str, str] = {
    "nsis": ".nsi",
    "wix": ".wxs",
    "inno": ".iss",
}

SUPPORTED_FORMATS = list(CONVERTER_REGISTRY.keys())


def get_converter_class(fmt: str) -> Type[BaseConverter]:
    """Return the converter class for *fmt*, or raise :class:`ValueError`."""
    try:
        return CONVERTER_REGISTRY[fmt]
    except KeyError:
        available = ", ".join(sorted(CONVERTER_REGISTRY))
        raise ValueError(
            f"Unknown format '{fmt}'. Available formats: {available}"
        ) from None


__all__ = [
    "BaseConverter",
    "YamlToNsisConverter",
    "CONVERTER_REGISTRY",
    "SUPPORTED_FORMATS",
    "OUTPUT_EXTENSIONS",
    "get_converter_class",
]
