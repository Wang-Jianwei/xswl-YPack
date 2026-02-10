"""
YAML → NSIS script converter.

This is the main entry point that assembles the output from
the various sub-modules (header, sections, packages, helpers).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..config import PackageConfig
from .base import BaseConverter
from .context import BuildContext
from .nsis_header import (
    generate_custom_includes,
    generate_general_settings,
    generate_header,
    generate_modern_ui,
)
from .nsis_helpers import generate_checksum_helper, generate_log_macros, generate_path_helpers
from .nsis_packages import (
    generate_existing_install_helpers,
    generate_oninit,
    generate_uninit,
    generate_package_sections,
    generate_signing_section,
    generate_update_section,
    generate_oninstsuccess,
    generate_package_descriptions,
)
from .nsis_sections import generate_installer_section, generate_uninstaller_section


class YamlToNsisConverter(BaseConverter):
    """Converts a :class:`PackageConfig` into a complete NSIS script."""

    tool_name = "nsis"
    output_extension = ".nsi"

    def __init__(self, config: PackageConfig, raw_config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(config, raw_config)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def convert(self) -> str:  # noqa: D102
        parts: List[str] = []

        # Header (unicode, defines, icons)
        parts.extend(generate_header(self.ctx))
        parts.extend(generate_custom_includes(self.ctx))
        parts.extend(generate_general_settings(self.ctx))
        parts.extend(generate_modern_ui(self.ctx))

        # Signing & update
        parts.extend(generate_signing_section(self.ctx))
        parts.extend(generate_update_section(self.ctx))

        # Logging macros (must come before sections that use them)
        if self.config.logging and self.config.logging.enabled:
            parts.extend(generate_log_macros())

        # PATH helpers (only when needed)
        needs_path_helpers = any(
            e.append for e in self.config.install.env_vars
        )
        if needs_path_helpers:
            parts.extend(generate_path_helpers(self.ctx))

        # Main install / uninstall
        parts.extend(generate_installer_section(self.ctx))
        parts.extend(generate_package_sections(self.ctx))
        
        # Package descriptions (must come after sections to reference SEC_PKG_X)
        parts.extend(generate_package_descriptions(self.ctx))
        
        parts.extend(generate_uninstaller_section(self.ctx))

        # Existing-install helper functions (may be referenced by UI callbacks)
        parts.extend(generate_existing_install_helpers(self.ctx))

        # .onInstSuccess: final logging (must be emitted after package sections)
        parts.extend(generate_oninstsuccess(self.ctx))

        # .onInit / un.onInit
        parts.extend(generate_oninit(self.ctx))
        parts.extend(generate_uninit(self.ctx))

        # Checksum / extract helpers (always emitted — lightweight stubs)
        has_remote = any(fe.is_remote for fe in self.config.files)
        has_checksum = any(fe.checksum_type for fe in self.config.files)
        if has_remote or has_checksum:
            parts.extend(generate_checksum_helper())

        # Final cleanup: remove any legacy MUI_FINISHPAGE_RUN defines that could
        # cause makensis 6010 warnings in some environments. We implement
        # launch-on-finish with our own custom finish page above.
        filtered_parts: List[str] = []
        for line in parts:
            if line.strip().startswith('!define MUI_FINISHPAGE_RUN'):
                continue
            if line.strip().startswith('!define MUI_FINISHPAGE_RUN_TEXT'):
                continue
            filtered_parts.append(line)

        # Post-process: Reorder MUI_LANGUAGE and LangString definitions to appear
        # after all MUI_PAGE_* and MUI_UNPAGE_* macros (NSIS MUI requirement).
        script_lines = "\n".join(filtered_parts).split("\n")
        reordered_lines = self._reorder_mui_language(script_lines)

        return "\n".join(reordered_lines)
    
    def _reorder_mui_language(self, lines: List[str]) -> List[str]:
        """Reorder script lines so MUI_LANGUAGE and LangString come after UI pages.
        
        NSIS MUI requires:
        1. ``!insertmacro MUI_LANGUAGE`` comes AFTER all ``MUI_PAGE_*`` macros.
        2. ``LangString`` definitions come AFTER ``MUI_LANGUAGE`` (so that the
           ``LANG_*`` constants are already defined).

        The reordered section after the last page directive becomes::

            ; ... pages ...
            !insertmacro MUI_LANGUAGE "English"
            !insertmacro MUI_LANGUAGE "SimpChinese"
            LangString SHORTCUTS_PAGE_TITLE ${LANG_ENGLISH} "..."
            LangString SHORTCUTS_PAGE_TITLE ${LANG_SIMPCHINESE} "..."
            ; ... rest of script ...
        """
        language_directives = []  # MUI_LANGUAGE macros
        langstring_defs = []       # LangString definitions
        other_lines = []
        found_last_page = -1
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Track the last MUI_PAGE or MUI_UNPAGE macro or custom page
            if stripped.startswith('!insertmacro MUI_PAGE') or \
               stripped.startswith('!insertmacro MUI_UNPAGE') or \
               stripped.startswith('Page custom'):
                found_last_page = len(other_lines)
            
            # Collect language directives to move
            if stripped.startswith('!insertmacro MUI_LANGUAGE'):
                language_directives.append(line)
            elif stripped.startswith('LangString '):
                langstring_defs.append(line)
            else:
                other_lines.append(line)
        
        # If we have language directives, reorder them
        if found_last_page >= 0 and language_directives:
            # Insert pattern: ...pages... + MUI_LANGUAGE + LangStrings + ...rest...
            # MUI_LANGUAGE must come before LangString so LANG_* constants exist.
            result = other_lines[:found_last_page + 1] + \
                     language_directives + \
                     langstring_defs + \
                     other_lines[found_last_page + 1:]
            return result
        
        # Otherwise return as-is (either no pages or no language directives)
        return lines


    def save(self, output_path: str) -> None:  # noqa: D102
        import os
        self.ctx.output_dir = os.path.dirname(os.path.abspath(output_path))
        script = self.convert()

        # Post-process: resolve any remaining configuration-style variables
        # (e.g. ${app.name}) that may appear in the final text. We only
        # resolve lowercase/dotted references to avoid touching NSIS defines
        # such as ${APP_NAME}.
        import re
        pattern = re.compile(r"\$\{([a-z][a-z0-9_.]*)\}")
        def _repl(m: re.Match) -> str:
            return self.ctx.resolve(m.group(0))
        script = pattern.sub(_repl, script)

        # NSIS requires the script file to be encoded as UTF-8 with BOM
        # when it contains Unicode characters. Use 'utf-8-sig' so Python
        # writes the BOM automatically at the start of the file.
        with open(output_path, "w", encoding="utf-8-sig") as fh:
            fh.write(script)
