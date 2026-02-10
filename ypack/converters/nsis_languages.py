"""
NSIS-specific language mapping.

Maps ypack canonical language names to NSIS framework identifiers:
- MUI language name (used with ``!insertmacro MUI_LANGUAGE``)
- ``LANG_*`` constant name (used with ``LangString``)
- Windows LCID value (used for fallback ``!define``)

This module is the **only** place where NSIS-specific language metadata
lives.  The generic ``ypack.languages`` module is framework-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from ..languages import resolve_language_name


@dataclass(frozen=True)
class NsisLanguageMapping:
    """NSIS-specific identifiers for a single language."""

    mui_name: str          # MUI language file name (e.g., "SimpChinese")
    lang_constant: str     # LANG_* constant (e.g., "LANG_SIMPCHINESE")
    lcid: int              # Windows locale ID


# ---------------------------------------------------------------------------
# Registry — canonical ypack name → NsisLanguageMapping
# ---------------------------------------------------------------------------

_NSIS_MAP: Dict[str, NsisLanguageMapping] = {}


def _n(name: str, mui: str, lcid: int) -> None:
    """Register an NSIS language mapping."""
    _NSIS_MAP[name] = NsisLanguageMapping(
        mui_name=mui,
        lang_constant=f"LANG_{mui.upper()}",
        lcid=lcid,
    )


# -- Western European -------------------------------------------------------
_n("English",                "English",              1033)
_n("French",                 "French",               1036)
_n("German",                 "German",               1031)
_n("Spanish",                "Spanish",              1034)
_n("SpanishInternational",   "SpanishInternational", 3082)
_n("Portuguese",             "Portuguese",           2070)
_n("BrazilianPortuguese",    "PortugueseBR",         1046)
_n("Italian",                "Italian",              1040)
_n("Dutch",                  "Dutch",                1043)
_n("Catalan",                "Catalan",              1027)

# -- Nordic ------------------------------------------------------------------
_n("Swedish",                "Swedish",              1053)
_n("Norwegian",              "Norwegian",            1044)
_n("NorwegianNynorsk",       "NorwegianNynorsk",     2068)
_n("Danish",                 "Danish",               1030)
_n("Finnish",                "Finnish",              1035)

# -- Eastern European -------------------------------------------------------
_n("Polish",                 "Polish",               1045)
_n("Czech",                  "Czech",                1029)
_n("Hungarian",              "Hungarian",            1038)
_n("Romanian",               "Romanian",             1048)
_n("Bulgarian",              "Bulgarian",            1026)
_n("Croatian",               "Croatian",             1050)
_n("Slovak",                 "Slovak",               1051)
_n("Serbian",                "Serbian",              3098)
_n("SerbianLatin",           "SerbianLatin",         2074)
_n("Slovenian",              "Slovenian",            1060)
_n("Estonian",               "Estonian",             1061)
_n("Latvian",                "Latvian",              1062)
_n("Lithuanian",             "Lithuanian",           1063)
_n("Ukrainian",              "Ukrainian",            1058)
_n("Russian",                "Russian",              1049)

# -- Asian -------------------------------------------------------------------
_n("SimplifiedChinese",      "SimpChinese",          2052)
_n("TraditionalChinese",     "TradChinese",          1028)
_n("Japanese",               "Japanese",             1041)
_n("Korean",                 "Korean",               1042)
_n("Thai",                   "Thai",                 1054)
_n("Vietnamese",             "Vietnamese",           1066)
_n("Indonesian",             "Indonesian",           1057)

# -- Middle Eastern / Other --------------------------------------------------
_n("Turkish",                "Turkish",              1055)
_n("Arabic",                 "Arabic",               1025)
_n("Hebrew",                 "Hebrew",               1037)
_n("Farsi",                  "Farsi",                1065)
_n("Greek",                  "Greek",                1032)
_n("Macedonian",             "Macedonian",           1071)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_nsis_mapping(lang_name: str) -> Optional[NsisLanguageMapping]:
    """Look up NSIS-specific identifiers for a language.

    Accepts canonical ypack names **or** aliases (resolved automatically).
    Returns ``None`` if the language is not in the NSIS mapping.
    """
    canonical = resolve_language_name(lang_name)
    return _NSIS_MAP.get(canonical)


def get_nsis_mapping_or_fallback(lang_name: str) -> NsisLanguageMapping:
    """Look up NSIS mapping, synthesising a best-effort fallback if unknown.

    For unrecognised languages the MUI name is set to the input name
    (which may work if the user typed a valid NSIS MUI language name
    directly), and LCID is set to 0.
    """
    mapping = get_nsis_mapping(lang_name)
    if mapping is not None:
        return mapping
    # Synthesise from the raw name
    canonical = resolve_language_name(lang_name)
    return NsisLanguageMapping(
        mui_name=canonical,
        lang_constant=f"LANG_{canonical.upper()}",
        lcid=0,
    )
