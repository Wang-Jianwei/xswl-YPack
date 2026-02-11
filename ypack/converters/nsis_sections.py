"""
NSIS Install / Uninstall section generation.

Fixes over the original implementation:
- Correct ``SetOutPath`` before every ``File`` directive.
- Proper uninstall manifest (tracks what was installed).
- inetc plugin include for remote downloads.
- Correct helper function calls for PATH append/remove.
"""

from __future__ import annotations

import os
import re
from typing import List, NamedTuple, Optional

from .context import BuildContext
from ..config import LangText, ShortcutConfig


class ShortcutEntry(NamedTuple):
    """Describes a single shortcut definition for per-shortcut checkbox support."""
    idx: int            # Unique sequential index across all shortcuts
    sc_type: str        # "desktop", "startmenu", "quicklaunch", or "custom"
    config: ShortcutConfig      # ShortcutConfig instance
    section: str        # "global" or "SEC_PKG_<n>"
    resolved_name: str  # Resolved .lnk display name


# -----------------------------------------------------------------------
# Path utilities
# -----------------------------------------------------------------------

def _normalize_path(path: str) -> str:
    """Convert glob-style paths to NSIS-compatible Windows paths."""
    path = path.replace("/**/", "\\")
    path = path.replace("**/", "")
    path = path.replace("/", "\\")
    return path


def _escape_nsis(value: str) -> str:
    return value.replace('"', '$\\"')


def _resolve_shortcut_path(ctx: BuildContext, path: str) -> str:
    if not path:
        return ""
    resolved = ctx.resolve(path).replace("/", "\\")
    if not (resolved.startswith("$") or re.match(r"^[A-Za-z]:\\", resolved)):
        resolved = f"$INSTDIR\\{resolved}"
    return resolved


def _shortcut_kind(location: str) -> str:
    loc = (location or "Desktop").strip().lower()
    if loc in ("desktop", "desk"):
        return "desktop"
    if loc in ("startmenu", "start_menu", "start menu"):
        return "startmenu"
    if loc in ("quicklaunch", "quick_launch", "quick launch"):
        return "quicklaunch"
    return "custom"


def _shortcut_base_dir(ctx: BuildContext, sc: ShortcutEntry) -> str:
    if sc.sc_type == "desktop":
        return "$DESKTOP"
    if sc.sc_type == "startmenu":
        return "$SMPROGRAMS\\${APP_NAME}"
    if sc.sc_type == "quicklaunch":
        return "$QUICKLAUNCH"
    return _resolve_shortcut_path(ctx, sc.config.location)


def _shortcut_link_path(ctx: BuildContext, sc: ShortcutEntry) -> str:
    base_dir = _shortcut_base_dir(ctx, sc).rstrip("\\")
    return f"{base_dir}\\{sc.resolved_name}.lnk"


def _should_use_recursive(source: str) -> bool:
    return bool(source) and "**" in source


# -----------------------------------------------------------------------
# Installer Section
# -----------------------------------------------------------------------

def generate_installer_section(ctx: BuildContext) -> List[str]:
    """Emit the main ``Section "Install"``."""
    cfg = ctx.config
    has_logging = cfg.logging and cfg.logging.enabled
    lines: List[str] = [
        "; ===========================================================================",
        '; Installer Section',
        "; ===========================================================================",
        'Section "-Install" SEC_INSTALL',
        "",
    ]

    # --- Logging: begin ---
    if has_logging:
        lines.append('  !insertmacro LogInit "Install"')
        lines.append('  !insertmacro LogWrite "Install directory: $INSTDIR"')
        lines.append("")

    # Track whether we need the inetc plugin
    has_remote = any(fe.is_remote for fe in cfg.files)
    if has_remote:
        lines.insert(0, '!include "inetc.nsh"')
        lines.insert(0, "; Plugin: inetc for HTTP downloads")

    # --- Files ---
    if has_logging:
        lines.append('  !insertmacro LogWrite "Copying files ..."')
    current_outpath: Optional[str] = None
    for fe in cfg.files:
        dest = fe.destination or "$INSTDIR"

        if fe.is_remote:
            # Remote download
            url = fe.source
            filename = url.rsplit("/", 1)[-1] or "download"
            if dest != current_outpath:
                lines.append(f'  SetOutPath "{dest}"')
                current_outpath = dest
            lines.append(f"  ; Download: {url}")
            lines.append(f'  inetc::get /SILENT "{url}" "$OUTDIR\\{filename}" /END')
            lines.append("  Pop $0")
            lines.append('  StrCmp $0 "OK" +3 0')
            lines.append('  MessageBox MB_OK|MB_ICONSTOP "Download failed: $0"')
            lines.append("  Abort")
            if fe.checksum_type:
                lines.append(f"  ; Verify checksum: {fe.checksum_type} {fe.checksum_value}")
                lines.append(f'  Push "$OUTDIR\\{filename}"')
                lines.append(f'  Push "{fe.checksum_type}"')
                lines.append(f'  Push "{fe.checksum_value}"')
                lines.append("  Call VerifyChecksum")
                lines.append("  Pop $0")
                lines.append('  StrCmp $0 "0" +3 0')
                lines.append('  MessageBox MB_OK|MB_ICONSTOP "Checksum verification failed"')
                lines.append("  Abort")
            if fe.decompress:
                lines.append(f'  Push "$OUTDIR\\{filename}"')
                lines.append(f'  Push "{dest}"')
                lines.append("  Call ExtractArchive")
        else:
            # Local file / directory
            if dest != current_outpath:
                lines.append(f'  SetOutPath "{dest}"')
                current_outpath = dest
            norm = _normalize_path(fe.source)
            if _should_use_recursive(fe.source):
                lines.append(f'  File /r "{norm}"')
            else:
                lines.append(f'  File "{norm}"')

    lines.append("")

    # --- Uninstaller ---
    lines.extend([
        "  ; Write uninstaller",
        "  SetOutPath $INSTDIR",
        '  WriteUninstaller "$INSTDIR\\Uninstall.exe"',
        "",
    ])
    if has_logging:
        lines.append('  !insertmacro LogWrite "Uninstaller created."')
        lines.append("")

    # --- Standard registry (Add/Remove Programs) ---
    reg_view = ctx.effective_reg_view
    lines.extend([
        f"  ; Application registry entries (using {reg_view}-bit registry view)",
        f'  SetRegView {reg_view}',
        '  WriteRegStr HKLM "${REG_KEY}" "InstallPath" "$INSTDIR"',
        '  WriteRegStr HKLM "${REG_KEY}" "Version" "${APP_VERSION}"',
        '',
        '  ; Add/Remove Programs (ARP) registry entries',
        '  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "DisplayName" "${APP_NAME}"',
        '  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "DisplayVersion" "${APP_VERSION}"',
        '  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "Publisher" "${APP_PUBLISHER}"',
        '  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "UninstallString" "$\\\"$INSTDIR\\Uninstall.exe$\\\""',
        '  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "QuietUninstallString" "$\\\"$INSTDIR\\Uninstall.exe$\\\" /S"',
        '  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "InstallLocation" "$INSTDIR"',
        '  WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "NoModify" 1',
        '  WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "NoRepair" 1',
    ])
    # DisplayIcon — use uninstaller's embedded icon (MUI_ICON is embedded during compilation)
    lines.append('  WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "DisplayIcon" "$INSTDIR\\Uninstall.exe,0"')
    lines.append('  SetRegView lastused')
    lines.append('')

    if has_logging:
        lines.append('  !insertmacro LogWrite "Registry entries written."')
        lines.append("")

    # --- Custom registry entries ---
    _emit_registry_writes(ctx, lines)

    # --- Environment variables ---
    _emit_env_var_writes(ctx, lines)

    # --- Shortcuts ---
    _emit_shortcuts(ctx, lines)
    if has_logging and collect_all_shortcuts(ctx):
        lines.append('  !insertmacro LogWrite "Shortcuts created."')
        lines.append("")

    # --- File associations ---
    _emit_file_associations(ctx, lines)

    # Estimated install size
    lines.append("  ; Calculate installed size")
    lines.append('  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2')
    lines.append('  IntFmt $0 "0x%08X" $0')
    lines.append(f'  SetRegView {reg_view}')
    lines.append('  WriteRegDWORD HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}" "EstimatedSize" $0')
    lines.append('  SetRegView lastused')
    lines.append("")



    lines.append("SectionEnd")
    lines.append("")
    return lines


# -----------------------------------------------------------------------
# Uninstaller Section
# -----------------------------------------------------------------------

def generate_uninstaller_section(ctx: BuildContext) -> List[str]:
    """Emit ``Section "Uninstall"``."""
    cfg = ctx.config
    has_logging = cfg.logging and cfg.logging.enabled
    lines: List[str] = [
        "; ===========================================================================",
        "; Uninstaller Section",
        "; ===========================================================================",
        'Section "Uninstall"',
        "",
    ]

    # --- Logging: begin ---
    if has_logging:
        lines.append('  !insertmacro LogInit "Uninstall"')
        lines.append("")

    # Remove files (reverse order)
    if has_logging:
        lines.append('  !insertmacro LogWrite "Removing installed files ..."')
    lines.append("  ; Remove installed files")
    for fe in reversed(cfg.files):
        dest = fe.destination or "$INSTDIR"
        if fe.is_remote:
            filename = fe.source.rsplit("/", 1)[-1] or "download"
            lines.append(f'  Delete "{dest}\\{filename}"')
        elif _should_use_recursive(fe.source):
            dirname = os.path.basename(_normalize_path(fe.source).rstrip("\\*"))
            if dirname and dirname != "*":
                lines.append(f'  RMDir /r "{dest}\\{dirname}"')
            else:
                lines.append(f'  RMDir /r "{dest}"')
        else:
            filename = os.path.basename(_normalize_path(fe.source))
            lines.append(f'  Delete "{dest}\\{filename}"')

    # Remove packages files
    if cfg.packages:
        lines.append("")
        lines.append("  ; Remove package files")
        for pkg in _flatten_packages(cfg.packages):
            for src_entry in pkg.sources:
                dest = src_entry.get("destination", "$INSTDIR")
                lines.append(f'  RMDir /r "{dest}"')

    lines.extend([
        "",
        "  ; Remove uninstaller",
        '  Delete "$INSTDIR\\Uninstall.exe"',
        "",
        "  ; Remove install directory (only if empty)",
        '  RMDir "$INSTDIR"',
        "",
    ])

    # Remove shortcuts
    _emit_shortcut_removes(ctx, lines)

    if has_logging and collect_all_shortcuts(ctx):
        lines.append('  !insertmacro LogWrite "Shortcuts removed."')
        lines.append("")

    # Remove standard registry keys
    if has_logging:
        lines.append('  !insertmacro LogWrite "Removing registry entries ..."')
    reg_view = ctx.effective_reg_view
    lines.extend([
        "  ; Remove registry entries",
        f'  SetRegView {reg_view}',
        '  DeleteRegKey HKLM "${REG_KEY}"',
        '  DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${APP_NAME}"',
        '  SetRegView lastused',
        "",
    ])

    # Remove custom registry values
    if cfg.install.registry_entries:
        lines.append("  ; Remove custom registry entries")
        current_view: Optional[str] = None
        # Track which keys we've deleted values from, so we can clean empty keys
        keys_to_clean: List[tuple] = []  # (hive, key)
        for entry in cfg.install.registry_entries:
            key = ctx.resolve(entry.key)
            target_view = entry.view if entry.view in ("32", "64") else None
            if target_view != current_view:
                if current_view is not None:
                    lines.append("  SetRegView lastused")
                if target_view is not None:
                    lines.append(f"  SetRegView {target_view}")
                current_view = target_view
            lines.append(f'  DeleteRegValue {entry.hive} "{key}" "{entry.name}"')
            if (entry.hive, key) not in keys_to_clean:
                keys_to_clean.append((entry.hive, key))
        if current_view is not None:
            lines.append("  SetRegView lastused")
        # Clean up empty registry keys left behind
        if keys_to_clean:
            lines.append("  ; Remove empty registry keys (only if no remaining values)")
            for hive, key in keys_to_clean:
                lines.append(f'  DeleteRegKey /ifempty {hive} "{key}"')
        lines.append("")

    # Remove file associations
    for fa in cfg.install.file_associations:
        hive, prefix = _fa_hive_prefix(fa)
        lines.append(f"  ; Remove file association: {fa.extension}")
        lines.append(f'  DeleteRegKey {hive} "{prefix}{fa.extension}"')
        if fa.prog_id:
            lines.append(f'  DeleteRegKey {hive} "{prefix}{fa.prog_id}"')

    # Remove environment variables
    _emit_env_var_removes(ctx, lines)

    # --- Per-package cleanup ---
    if cfg.packages:
        _emit_per_package_uninstall(ctx, lines)

    # --- Logging: end ---
    if has_logging:
        lines.append('  !insertmacro LogWrite "Uninstallation completed."')
        lines.append('  !insertmacro LogClose')
        lines.append("")

    lines.extend([
        "SectionEnd",
        "",
    ])
    return lines


# -----------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------

def _emit_per_package_uninstall(ctx: BuildContext, lines: List[str]) -> None:
    """Emit cleanup for per-package registry, env vars, shortcuts, file associations."""
    for pkg in _flatten_packages(ctx.config.packages):
        has_actions = (pkg.registry_entries or pkg.env_vars or
                       pkg.desktop_shortcut or pkg.start_menu_shortcut or pkg.shortcuts or
                       pkg.file_associations)
        if not has_actions:
            continue

        lines.append(f"  ; Cleanup for package: {pkg.name}")

        # Remove per-package registry entries
        for entry in pkg.registry_entries:
            key = ctx.resolve(entry.key)
            lines.append(f'  DeleteRegValue {entry.hive} "{key}" "{entry.name}"')

        # Remove per-package file associations
        for fa in pkg.file_associations:
            hive, prefix = _fa_hive_prefix(fa)
            lines.append(f'  DeleteRegKey {hive} "{prefix}{fa.extension}"')
            if fa.prog_id:
                lines.append(f'  DeleteRegKey {hive} "{prefix}{fa.prog_id}"')

        # Remove per-package environment variables
        for env in pkg.env_vars:
            if not env.remove_on_uninstall:
                continue
            hive, key = _env_hive_key(env)
            if env.append and env.name.upper() == "PATH":
                env_value = ctx.resolve(env.value)
                lines.extend([
                    f"  ; Remove PATH entry: {env_value}",
                    f'  ReadRegStr $0 {hive} "{key}" "{env.name}"',
                    f'  StrCpy $1 "{env_value}"',
                    "  Call un._RemovePathEntry",
                    f'  WriteRegExpandStr {hive} "{key}" "{env.name}" "$0"',
                    '  SendMessage ${HWND_BROADCAST} ${WM_SETTINGCHANGE} 0 "STR:Environment" /TIMEOUT=500',
                ])
            else:
                lines.append(f'  DeleteRegValue {hive} "{key}" "{env.name}"')
        lines.append("")


def _emit_registry_writes(ctx: BuildContext, lines: List[str]) -> None:
    """Emit WriteRegStr / WriteRegDWORD for custom registry entries.

    Groups entries by registry view to minimize ``SetRegView`` toggles.
    """
    entries = ctx.config.install.registry_entries
    if not entries:
        return

    lines.append("  ; Custom registry entries")
    current_view: Optional[str] = None
    for entry in entries:
        key = ctx.resolve(entry.key)
        value = ctx.resolve(entry.value)
        target_view = entry.view if entry.view in ("32", "64") else None
        if target_view != current_view:
            if current_view is not None:
                lines.append("  SetRegView lastused")
            if target_view is not None:
                lines.append(f"  SetRegView {target_view}")
            current_view = target_view
        if entry.type == "dword":
            lines.append(f'  WriteRegDWORD {entry.hive} "{key}" "{entry.name}" {value}')
        elif entry.type == "expand":
            lines.append(f'  WriteRegExpandStr {entry.hive} "{key}" "{entry.name}" "{value}"')
        else:
            lines.append(f'  WriteRegStr {entry.hive} "{key}" "{entry.name}" "{value}"')
    if current_view is not None:
        lines.append("  SetRegView lastused")
    lines.append("")


def _emit_env_var_writes(ctx: BuildContext, lines: List[str]) -> None:
    """Emit environment variable writes (installer side)."""
    for env in ctx.config.install.env_vars:
        env_value = ctx.resolve(env.value)
        hive, key = _env_hive_key(env)
        lines.append(f"  ; Environment variable: {env.name} ({env.scope})")

        if env.append and env.name.upper() == "PATH":
            lines.extend([
                f'  ReadRegStr $0 {hive} "{key}" "{env.name}"',
                f'  StrCpy $1 "{env_value}"',
                "",
                '  ; Check whether the entry already exists',
                '  Push $0',
                '  Push $1',
                "  Call _StrContains",
                '  StrCmp $R9 "1" _skip_path_append',
                "",
                '  ; Append entry',
                '  StrCmp $0 "" 0 +2',
                f'    StrCpy $0 "{env_value}"',
                '  Goto +2',
                f'    StrCpy $0 "$0;{env_value}"',
                f'  WriteRegExpandStr {hive} "{key}" "{env.name}" "$0"',
                "",
                '  ; Broadcast WM_SETTINGCHANGE',
                '  SendMessage ${HWND_BROADCAST} ${WM_SETTINGCHANGE} 0 "STR:Environment" /TIMEOUT=500',
                "",
                "_skip_path_append:",
            ])
        else:
            lines.append(f'  WriteRegStr {hive} "{key}" "{env.name}" "{env_value}"')
        lines.append("")


def _emit_env_var_removes(ctx: BuildContext, lines: List[str]) -> None:
    """Emit environment variable removal (uninstaller side)."""
    for env in ctx.config.install.env_vars:
        if not env.remove_on_uninstall:
            continue
        hive, key = _env_hive_key(env)

        if env.append and env.name.upper() == "PATH":
            env_value = ctx.resolve(env.value)
            lines.extend([
                f"  ; Remove PATH entry: {env_value}",
                f'  ReadRegStr $0 {hive} "{key}" "{env.name}"',
                f'  StrCpy $1 "{env_value}"',
                "  Call un._RemovePathEntry",
                f'  WriteRegExpandStr {hive} "{key}" "{env.name}" "$0"',
                '  SendMessage ${HWND_BROADCAST} ${WM_SETTINGCHANGE} 0 "STR:Environment" /TIMEOUT=500',
                "",
            ])
        else:
            lines.append(f'  DeleteRegValue {hive} "{key}" "{env.name}"')


def collect_all_shortcuts(ctx: BuildContext) -> List[ShortcutEntry]:
    """Enumerate all shortcut definitions (global + per-package) with stable indices.

    The index determines the NSIS variable name ($CREATE_SC_<index>) and the
    checkbox control variable ($_SC_CTRL_<index>) used on the shortcut options page.
    """
    cfg = ctx.config
    entries: List[ShortcutEntry] = []
    idx = 0

    def _append(sc_cfg: ShortcutConfig, section: str) -> None:
        nonlocal idx
        if not sc_cfg or not sc_cfg.target:
            return
        name = ctx.resolve(sc_cfg.name) if sc_cfg.name else "${APP_NAME}"
        sc_type = _shortcut_kind(sc_cfg.location)
        entries.append(ShortcutEntry(idx, sc_type, sc_cfg, section, name))
        idx += 1

    # Global install shortcuts (legacy)
    if cfg.install.desktop_shortcut and cfg.install.desktop_shortcut.target:
        cfg.install.desktop_shortcut.location = "Desktop"
        _append(cfg.install.desktop_shortcut, "global")
    if cfg.install.start_menu_shortcut and cfg.install.start_menu_shortcut.target:
        cfg.install.start_menu_shortcut.location = "StartMenu"
        _append(cfg.install.start_menu_shortcut, "global")

    # Global install shortcuts (new list)
    for sc in cfg.install.shortcuts:
        _append(sc, "global")

    # Per-package shortcuts (ordered by _flatten_packages)
    flat = _flatten_packages(cfg.packages)
    for pkg_idx, pkg in enumerate(flat):
        sec_name = f"SEC_PKG_{pkg_idx}"
        if pkg.desktop_shortcut and pkg.desktop_shortcut.target:
            pkg.desktop_shortcut.location = "Desktop"
            _append(pkg.desktop_shortcut, sec_name)
        if pkg.start_menu_shortcut and pkg.start_menu_shortcut.target:
            pkg.start_menu_shortcut.location = "StartMenu"
            _append(pkg.start_menu_shortcut, sec_name)
        for sc in pkg.shortcuts:
            _append(sc, sec_name)

    return entries


def _emit_single_shortcut(ctx: BuildContext, lines: List[str],
                          sc: ShortcutEntry,
                          add_uninstaller_link: bool = False) -> None:
    """Emit conditional CreateShortCut for a single shortcut, guarded by $CREATE_SC_<index>."""
    i = sc.idx
    target = _escape_nsis(_resolve_shortcut_path(ctx, sc.config.target))
    name = sc.resolved_name
    link_path = _escape_nsis(_shortcut_link_path(ctx, sc))
    base_dir = _escape_nsis(_shortcut_base_dir(ctx, sc))
    args = _escape_nsis(ctx.resolve(sc.config.args)) if sc.config.args else ""
    icon = _resolve_shortcut_path(ctx, sc.config.icon) if sc.config.icon else ""
    icon = _escape_nsis(icon) if icon else ""
    workdir = _resolve_shortcut_path(ctx, sc.config.workdir) if sc.config.workdir else ""
    workdir = _escape_nsis(workdir) if workdir else ""

    create_dir = "" if base_dir in ("$DESKTOP", "$QUICKLAUNCH") else f'  CreateDirectory "{base_dir}"'
    # NOTE: NSIS CreateShortCut does not support specifying a working directory.
    # If a workdir is requested, emit a warning comment and do not pass it as an argument
    if sc.config.workdir:
        workdir_raw = ctx.resolve(sc.config.workdir)
        lines.append(f'  ; WARNING: requested workdir "{workdir_raw}" cannot be set by CreateShortCut and will be ignored')
    if args or icon:
        args_part = f'"{args}"' if args else '""'
        icon_part = f'"{icon}"' if icon else '""'
        # Use icon index 0 when icon is provided, otherwise omit
        if icon:
            create_line = f'  CreateShortCut "{link_path}" "{target}" {args_part} {icon_part} 0'
        else:
            create_line = f'  CreateShortCut "{link_path}" "{target}" {args_part}'
    else:
        create_line = f'  CreateShortCut "{link_path}" "{target}"'

    lines.append(f"  ; Shortcut ({name})")
    if sc.config.optional:
        lines.extend([
            f'  StrCmp $CREATE_SC_{i} "1" SC_Create_{i}',
            f'  Goto SC_Skip_{i}',
            f'SC_Create_{i}:',
        ])
    if create_dir:
        lines.append(create_dir)
    lines.append(create_line)
    if add_uninstaller_link and sc.sc_type == "startmenu":
        lines.append(f'  CreateShortCut "{base_dir}\\Uninstall.lnk" "$INSTDIR\\Uninstall.exe"')
    if sc.config.optional:
        lines.append(f'SC_Skip_{i}:')
    lines.append("")


def _emit_shortcuts(ctx: BuildContext, lines: List[str]) -> None:
    """Emit CreateShortCut for global desktop and start menu shortcuts."""
    all_sc = collect_all_shortcuts(ctx)
    for sc in all_sc:
        if sc.section != "global":
            continue
        # Add Uninstall.lnk only for global start menu shortcuts
        _emit_single_shortcut(ctx, lines, sc,
                              add_uninstaller_link=(sc.sc_type == "startmenu"))


def _emit_shortcut_removes(ctx: BuildContext, lines: List[str]) -> None:
    all_sc = collect_all_shortcuts(ctx)
    if not all_sc:
        return
    lines.append("  ; Remove shortcuts")
    remove_dirs = set()
    remove_uninstall = set()
    for sc in all_sc:
        link_path = _escape_nsis(_shortcut_link_path(ctx, sc))
        lines.append(f'  Delete "{link_path}"')
        if sc.sc_type == "startmenu" and sc.section == "global":
            base_dir = _escape_nsis(_shortcut_base_dir(ctx, sc))
            remove_uninstall.add(base_dir)
            remove_dirs.add(base_dir)
    for base_dir in sorted(remove_uninstall):
        lines.append(f'  Delete "{base_dir}\\Uninstall.lnk"')
    for base_dir in sorted(remove_dirs):
        lines.append(f'  RMDir "{base_dir}"')
    lines.append("")


def _emit_file_associations(ctx: BuildContext, lines: List[str]) -> None:
    """Emit WriteRegStr for file associations."""
    fa_list = ctx.config.install.file_associations
    if not fa_list:
        return

    if not ctx.config.languages:
        for fa in fa_list:
            desc_text = LangText.from_value(fa.description)
            if desc_text.translations:
                raise ValueError(
                    "file_associations.description requires languages when using per-language values."
                )

    for idx, fa in enumerate(fa_list):
        hive, prefix = _fa_hive_prefix(fa)
        lines.append(f"  ; File association: {fa.extension} -> {fa.application}")
        lines.append(f'  WriteRegStr {hive} "{prefix}{fa.extension}" "" "{fa.prog_id}"')
        if fa.prog_id:
            desc_text = LangText.from_value(fa.description)
            if desc_text.translations:
                desc_value = f'$(FA_DESC_{idx})'
            else:
                desc_value = ctx.resolve(desc_text.text).replace('"', '$\\"')
            lines.append(f'  WriteRegStr {hive} "{prefix}{fa.prog_id}" "" "{desc_value}"')
        if fa.default_icon:
            lines.append(f'  WriteRegStr {hive} "{prefix}{fa.prog_id}\\DefaultIcon" "" "{fa.default_icon}"')
        verbs = fa.verbs or {}
        if verbs:
            for verb, cmd in verbs.items():
                lines.append(f'  WriteRegStr {hive} "{prefix}{fa.prog_id}\\Shell\\{verb}\\Command" "" "{cmd}"')
        elif fa.application:
            lines.append(f'  WriteRegStr {hive} "{prefix}{fa.prog_id}\\Shell\\Open\\Command" "" "{fa.application} \\"%1\\""')
        lines.append("")


# -----------------------------------------------------------------------
# Tiny shared utilities
# -----------------------------------------------------------------------

def _env_hive_key(env) -> tuple[str, str]:
    scope = (env.scope or "system").lower()
    if scope == "system":
        return "HKLM", "SYSTEM\\CurrentControlSet\\Control\\Session Manager\\Environment"
    return "HKCU", "Environment"


def _fa_hive_prefix(fa) -> tuple[str, str]:
    if getattr(fa, "register_for_all_users", True):
        return "HKCR", ""
    return "HKCU", "Software\\Classes\\"


def _flatten_packages(packages) -> list:
    flat = []
    for pkg in packages:
        if pkg.children:
            flat.extend(_flatten_packages(pkg.children))
        else:
            flat.append(pkg)
    return flat


# -----------------------------------------------------------------------
# Per-package helper variants (accept explicit data lists)
# -----------------------------------------------------------------------

def _emit_registry_writes_for(ctx: BuildContext, lines: List[str],
                               entries: list) -> None:
    """Emit WriteRegStr / WriteRegDWORD for a list of RegistryEntry objects."""
    if not entries:
        return
    lines.append("  ; Registry entries")
    current_view: Optional[str] = None
    for entry in entries:
        key = ctx.resolve(entry.key)
        value = ctx.resolve(entry.value)
        target_view = entry.view if entry.view in ("32", "64") else None
        if target_view != current_view:
            if current_view is not None:
                lines.append("  SetRegView lastused")
            if target_view is not None:
                lines.append(f"  SetRegView {target_view}")
            current_view = target_view
        if entry.type == "dword":
            lines.append(f'  WriteRegDWORD {entry.hive} "{key}" "{entry.name}" {value}')
        elif entry.type == "expand":
            lines.append(f'  WriteRegExpandStr {entry.hive} "{key}" "{entry.name}" "{value}"')
        else:
            lines.append(f'  WriteRegStr {entry.hive} "{key}" "{entry.name}" "{value}"')
    if current_view is not None:
        lines.append("  SetRegView lastused")
    lines.append("")


def _emit_env_var_writes_for(ctx: BuildContext, lines: List[str],
                              env_vars: list) -> None:
    """Emit environment variable writes for a list of EnvVarEntry objects."""
    for env in env_vars:
        env_value = ctx.resolve(env.value)
        hive, key = _env_hive_key(env)
        lines.append(f"  ; Environment variable: {env.name} ({env.scope})")

        if env.append and env.name.upper() == "PATH":
            lines.extend([
                f'  ReadRegStr $0 {hive} "{key}" "{env.name}"',
                f'  StrCpy $1 "{env_value}"',
                "",
                '  ; Check whether the entry already exists',
                '  Push $0',
                '  Push $1',
                "  Call _StrContains",
                '  StrCmp $R9 "1" _skip_path_append',
                "",
                '  ; Append entry',
                '  StrCmp $0 "" 0 +2',
                f'    StrCpy $0 "{env_value}"',
                '  Goto +2',
                f'    StrCpy $0 "$0;{env_value}"',
                f'  WriteRegExpandStr {hive} "{key}" "{env.name}" "$0"',
                "",
                '  ; Broadcast WM_SETTINGCHANGE',
                '  SendMessage ${HWND_BROADCAST} ${WM_SETTINGCHANGE} 0 "STR:Environment" /TIMEOUT=500',
                "",
                "_skip_path_append:",
            ])
        else:
            lines.append(f'  WriteRegStr {hive} "{key}" "{env.name}" "{env_value}"')
        lines.append("")


def _emit_shortcuts_for(ctx: BuildContext, lines: List[str],
                         section_id: str) -> None:
    """Emit shortcut creation for a specific package section.

    Uses ``collect_all_shortcuts`` to find the correct per-shortcut
    variable ($CREATE_SC_<i>) for each shortcut in this package.
    """
    all_sc = collect_all_shortcuts(ctx)
    for sc in all_sc:
        if sc.section == section_id:
            _emit_single_shortcut(ctx, lines, sc, add_uninstaller_link=False)


def _emit_file_associations_for(ctx: BuildContext, lines: List[str],
                                  fa_list: list, prefix_id: str) -> None:
    """Emit WriteRegStr for a list of file associations."""
    if not fa_list:
        return
    for idx, fa in enumerate(fa_list):
        hive, prefix = _fa_hive_prefix(fa)
        lines.append(f"  ; File association: {fa.extension} -> {fa.application}")
        lines.append(f'  WriteRegStr {hive} "{prefix}{fa.extension}" "" "{fa.prog_id}"')
        if fa.prog_id:
            desc_text = LangText.from_value(fa.description)
            desc_value = ctx.resolve(desc_text.text).replace('"', '$\\"') if desc_text.text else ""
            lines.append(f'  WriteRegStr {hive} "{prefix}{fa.prog_id}" "" "{desc_value}"')
        if fa.default_icon:
            lines.append(f'  WriteRegStr {hive} "{prefix}{fa.prog_id}\\DefaultIcon" "" "{fa.default_icon}"')
        verbs = fa.verbs or {}
        if verbs:
            for verb, cmd in verbs.items():
                lines.append(f'  WriteRegStr {hive} "{prefix}{fa.prog_id}\\Shell\\{verb}\\Command" "" "{cmd}"')
        elif fa.application:
            lines.append(f'  WriteRegStr {hive} "{prefix}{fa.prog_id}\\Shell\\Open\\Command" "" "{fa.application} \\"%1\\""')
        lines.append("")
