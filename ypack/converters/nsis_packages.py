"""
NSIS component / package section generation.

Handles SectionGroup nesting, optional/default flags, post_install
commands, and the .onInit section-flag setup.
"""

from __future__ import annotations

import os
from typing import List

from .context import BuildContext
from .nsis_languages import get_nsis_mapping
from .nsis_sections import _normalize_path, _should_use_recursive, _flatten_packages
from .nsis_sections import (
    _emit_registry_writes_for,
    _emit_env_var_writes_for,
    _emit_file_associations_for,
    _emit_shortcuts_for,
    collect_all_shortcuts,
)


def generate_package_sections(ctx: BuildContext) -> List[str]:
    """Emit ``Section`` / ``SectionGroup`` blocks for every package."""
    if not ctx.config.packages:
        return []

    has_logging = ctx.config.logging and ctx.config.logging.enabled
    lines: List[str] = [
        "; ===========================================================================",
        "; Package / Component Sections",
        "; ===========================================================================",
        "",
    ]

    idx_ref = [0]  # mutable counter shared across recursion
    group_idx_ref = [0]  # counter for SectionGroup IDs

    def _emit(pkg_list: list) -> None:
        for pkg in pkg_list:
            if pkg.children:
                # Assign ID to SectionGroup if it has a description
                if not pkg.description.is_empty():
                    group_id = f"SEC_GROUP_{group_idx_ref[0]}"
                    group_idx_ref[0] += 1
                    lines.append(f'SectionGroup /e "{pkg.name}" {group_id}')
                else:
                    lines.append(f'SectionGroup "{pkg.name}"')
                _emit(pkg.children)
                lines.append("SectionGroupEnd")
                lines.append("")
            else:
                sec_name = f"SEC_PKG_{idx_ref[0]}"
                idx_ref[0] += 1
                lines.append(f'Section "{pkg.name}" {sec_name}')

                if has_logging:
                    lines.append(f'  !insertmacro LogWrite "Installing component: {pkg.name}"')

                for src_entry in pkg.sources:
                    src_val = src_entry.get("source", "")
                    dest = src_entry.get("destination", "$INSTDIR")
                    lines.append(f'  SetOutPath "{dest}"')

                    if isinstance(src_val, list):
                        for s in src_val:
                            lines.append(_file_line(ctx, s))
                    else:
                        lines.append(_file_line(ctx, src_val))

                if pkg.post_install:
                    lines.append("")
                    lines.append("  ; Post-install commands")
                    for cmd in pkg.post_install:
                        if has_logging:
                            # Escape double quotes for NSIS string context
                            log_msg = cmd.replace('"', '$\\"')
                            lines.append(f'  !insertmacro LogWrite "Running: {log_msg}"')
                        # Escape double quotes in ExecWait command
                        exec_cmd = cmd.replace('"', '$\\"')
                        lines.append(f'  ExecWait "{exec_cmd}"')

                # Per-package registry entries
                if pkg.registry_entries:
                    lines.append("")
                    _emit_registry_writes_for(ctx, lines, pkg.registry_entries)

                # Per-package environment variables
                if pkg.env_vars:
                    _emit_env_var_writes_for(ctx, lines, pkg.env_vars)

                # Per-package shortcuts
                if pkg.desktop_shortcut or pkg.start_menu_shortcut or pkg.shortcuts:
                    _emit_shortcuts_for(ctx, lines, sec_name)

                # Per-package file associations
                if pkg.file_associations:
                    _emit_file_associations_for(ctx, lines, pkg.file_associations, f"pkg_{idx_ref[0] - 1}")

                if has_logging:
                    lines.append(f'  !insertmacro LogWrite "Component {pkg.name} done."')
                lines.append("SectionEnd")
                lines.append("")

    _emit(ctx.config.packages)
    return lines


def _collect_all_packages_with_ids(packages) -> list:
    """Collect all packages (including groups) with their assigned IDs.
    Returns list of tuples: (pkg, id_str, is_group)
    """
    result = []
    pkg_idx = [0]
    group_idx = [0]
    
    def _collect(pkg_list):
        for pkg in pkg_list:
            if pkg.children:
                # SectionGroup
                if not pkg.description.is_empty():
                    group_id = f"SEC_GROUP_{group_idx[0]}"
                    group_idx[0] += 1
                    result.append((pkg, group_id, True))
                _collect(pkg.children)
            else:
                # Regular Section
                sec_id = f"SEC_PKG_{pkg_idx[0]}"
                pkg_idx[0] += 1
                result.append((pkg, sec_id, False))
    
    _collect(packages)
    return result


def generate_package_descriptions(ctx: BuildContext) -> List[str]:
    """Emit LangString definitions and MUI_DESCRIPTIONS_TABLE for package descriptions.
    
    This allows the Components page to display detailed descriptions of each
    section (and section group) in the right panel when selected.
    """
    if not ctx.config.packages:
        return []
    
    all_pkgs = _collect_all_packages_with_ids(ctx.config.packages)
    has_descriptions = any(not pkg.description.is_empty() for pkg, _, _ in all_pkgs)
    
    if not has_descriptions:
        return []
    
    lines: List[str] = [
        "; ===========================================================================",
        "; Component Descriptions (displayed in Components page)",
        "; ===========================================================================",
        "",
    ]
    
    # Generate LangString definitions for each component/group with a description
    desc_idx = 0
    desc_map = {}  # Maps section_id to DESC_xxx variable name

    langs = ctx.config.languages or []
    if not langs:
        for pkg, _, _ in all_pkgs:
            if pkg.description.translations:
                raise ValueError(
                    "packages.description requires languages when using per-language values."
                )

    for pkg, sec_id, is_group in all_pkgs:
        if not pkg.description.is_empty():
            desc_var = f"DESC_{desc_idx}"
            desc_idx += 1
            desc_map[sec_id] = desc_var

            if langs:
                # Emit a LangString for each configured language.
                # Use per-language description when provided, otherwise fall
                # back to the default description.
                for lang_cfg in langs:
                    mapping = get_nsis_mapping(lang_cfg.name)
                    if mapping:
                        lang_const = f'${{{mapping.lang_constant}}}'
                    else:
                        lang_const = f'${{LANG_{lang_cfg.name.upper()}}}'
                    lang_desc = pkg.description.get_for_language(
                        lang_cfg.name,
                        f"packages.{pkg.name}.description",
                    )
                    lang_desc = ctx.resolve(lang_desc).replace('"', '$\\"')
                    lines.append(f'LangString {desc_var} {lang_const} "{lang_desc}"')
            else:
                # No configured languages: emit an English LangString as a fallback
                desc = ctx.resolve(pkg.description.text).replace('"', '$\\"')
                lines.append(f'LangString {desc_var} ${{LANG_ENGLISH}} "{desc}"')
    lines.extend([
        "",
        "; Bind descriptions to sections",
        "!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN",
    ])

    # Bind each description to its section or group
    for pkg, sec_id, is_group in all_pkgs:
        if not pkg.description.is_empty():
            if sec_id in desc_map:
                desc_var = desc_map[sec_id]
                lines.append(f'  !insertmacro MUI_DESCRIPTION_TEXT ${{{sec_id}}} $({desc_var})')
            else:
                # Already emitted literal description above
                pass

    lines.extend([
        "!insertmacro MUI_FUNCTION_DESCRIPTION_END",
        "",
    ])

    return lines


def generate_signing_section(ctx: BuildContext) -> List[str]:
    """Emit ``!finalize`` code-signing directive."""
    signing = ctx.config.signing
    if not signing or not signing.enabled:
        return []
    return [
        "; --- Code Signing ---",
        f"; Certificate: {signing.certificate}",
        f"; Timestamp:   {signing.timestamp_url}",
        f"; Verify after build: {signing.verify_signature}",
        f"; Checksum: {signing.checksum_type} {signing.checksum_value}",
        f'!finalize \'signtool sign /f "{signing.certificate}" /p "{signing.password}" /t "{signing.timestamp_url}" "%1"\'',
        "",
    ]


def generate_update_section(ctx: BuildContext) -> List[str]:
    """Emit update-metadata registry writes."""
    upd = ctx.config.update
    if not upd or not upd.enabled:
        return []
    return [
        "; --- Auto-Update Configuration ---",
        f'!define UPDATE_URL "{upd.update_url}"',
        f'!define DOWNLOAD_URL "{upd.download_url}"',
        f'!define CHECK_ON_STARTUP "{str(upd.check_on_startup).lower()}"',
        f'!define BACKUP_ON_UPGRADE "{str(upd.backup_on_upgrade).lower()}"',
        f'!define REPAIR_ENABLED "{str(upd.repair_enabled).lower()}"',
        "",
        'Section "Update Configuration"',
        f'  WriteRegStr {upd.registry_hive} "{upd.registry_key}" "UpdateURL" "${{UPDATE_URL}}"',
        f'  WriteRegStr {upd.registry_hive} "{upd.registry_key}" "DownloadURL" "${{DOWNLOAD_URL}}"',
        f'  WriteRegStr {upd.registry_hive} "{upd.registry_key}" "CheckOnStartup" "${{CHECK_ON_STARTUP}}"',
        f'  WriteRegStr {upd.registry_hive} "{upd.registry_key}" "BackupOnUpgrade" "${{BACKUP_ON_UPGRADE}}"',
        f'  WriteRegStr {upd.registry_hive} "{upd.registry_key}" "RepairEnabled" "${{REPAIR_ENABLED}}"',
        "SectionEnd",
        "",
    ]


def generate_oninstsuccess(ctx: BuildContext) -> List[str]:
    """Emit ``.onInstSuccess`` — final logging/cleanup after installation.

    Adds "Skipping component: <name>" log entries for optional packages that
    were not selected by the user. This runs after all sections have executed
    so sections that were run will have already logged their own messages.
    """
    cfg = ctx.config
    if not (cfg.logging and cfg.logging.enabled):
        return []

    lines: List[str] = [
        "; ------------------------------------------------------------------",
        "; Installer success callback (runs after all sections complete)",
        "; ------------------------------------------------------------------",
        "Function .onInstSuccess",
    ]

    # Emit skip logs for optional packages that were not selected
    flat = _flatten_packages(cfg.packages)
    for idx, pkg in enumerate(flat):
        if pkg.optional:
            sec = f"SEC_PKG_{idx}"
            # SectionGetFlags <section> $0 ; IntOp $0 $0 & ${SF_SELECTED}
            # If result == 0 then section was not selected => log skipping
            lines.append(f'  SectionGetFlags ${{{sec}}} $0')
            lines.append('  IntOp $0 $0 & ${SF_SELECTED}')
            lines.append(f'  StrCmp $0 "0" _pkg_{idx}_skipped _pkg_{idx}_installed')
            lines.append(f'_pkg_{idx}_skipped:')
            lines.append(f'  !insertmacro LogWrite "Skipping component: {pkg.name}"')
            lines.append(f'  Goto _pkg_{idx}_done')
            lines.append(f'_pkg_{idx}_installed:')
            lines.append(f'  ; Component {pkg.name} selected/installed (no skip log)')
            lines.append(f'_pkg_{idx}_done:')

    lines.extend([
        '  !insertmacro LogWrite "Installation completed successfully."',
        '  !insertmacro LogClose',
        'FunctionEnd',
        '',
    ])

    return lines


def generate_oninit(ctx: BuildContext) -> List[str]:
    """Emit ``.onInit`` — mutex, signature, sysreq, existing-install, section flags."""
    cfg = ctx.config
    lines: List[str] = [
        "; ===========================================================================",
        "; Initialization",
        "; ===========================================================================",
        "Function .onInit",
        "",
    ]

    # ------------------------------------------------------------------
    # Installer Mutex — prevent running two installers at the same time
    # ------------------------------------------------------------------
    installer_running_text = '$(INSTALLER_RUNNING)' if cfg.languages else 'The installer is already running.'
    lines.extend([
        '  ; Prevent multiple installer instances',
        '  System::Call \'kernel32::CreateMutex(p 0, i 0, t "${APP_NAME}_InstallerMutex") p .r1 ?e\'',
        '  Pop $R0',
        '  StrCmp $R0 "0" +3 0',
        f'  MessageBox MB_OK|MB_ICONEXCLAMATION "{installer_running_text}"',
        '  Abort',
        '',
    ])

    if len(cfg.languages) > 1:
        lines.extend([
            '  ; Language selection dialog before UI initialization',
            '  !insertmacro MUI_LANGDLL_DISPLAY',
            '',
        ])

    # Signature verification
    if cfg.signing and cfg.signing.verify_signature:
        lines.extend([
            "  ; Verify installer digital signature",
            '  nsExec::ExecToStack \'powershell -NoProfile -Command "& { $s = Get-AuthenticodeSignature -LiteralPath $env:__COMPAT_LAYER; if ($s.Status -ne [System.Management.Automation.SignatureStatus]::Valid) { exit 1 } }"\'',
            "  Pop $0",
            '  StrCmp $0 "0" _sig_ok',
        ])
        sig_failed_text = '$(SIGNATURE_FAILED)' if cfg.languages else 'Signature verification failed. Installation aborted.'
        lines.append(f'  MessageBox MB_OK|MB_ICONSTOP "{sig_failed_text}"')
        lines.extend([
            "  Abort",
            "_sig_ok:",
            "",
        ])

    # System requirements
    sysreq = cfg.install.system_requirements
    if sysreq:
        if sysreq.min_windows_version:
            mv = sysreq.min_windows_version
            lines.extend([
                f"  ; Check minimum Windows version: {mv}",
                f'  nsExec::ExecToStack \'powershell -NoProfile -Command "& {{ $v = (Get-CimInstance Win32_OperatingSystem).Version; if ([Version]$v -lt [Version]\'{mv}\') {{ exit 1 }} }}"\'',
                "  Pop $0",
                '  StrCmp $0 "0" +3 0',
            ])
            req_win_text = '$(REQUIRES_WINDOWS)' if cfg.languages else f'Requires Windows {mv} or higher.'
            lines.append(f'  MessageBox MB_OK|MB_ICONSTOP "{req_win_text}"')
            lines.extend([
                "  Abort",
                "",
            ])
        if sysreq.min_free_space_mb:
            mb = sysreq.min_free_space_mb
            lines.extend([
                f"  ; Check free disk space >= {mb} MB",
                f'  nsExec::ExecToStack \'powershell -NoProfile -Command "& {{ $d = (Get-PSDrive ($env:SystemDrive[0])); if ($d.Free / 1MB -lt {mb}) {{ exit 1 }} }}"\'',
                "  Pop $0",
                '  StrCmp $0 "0" +3 0',
            ])
            space_text = '$(NOT_ENOUGH_SPACE)' if cfg.languages else f'Not enough free disk space. Require at least {mb} MB.'
            lines.append(f'  MessageBox MB_OK|MB_ICONSTOP "{space_text}"')
            lines.extend([
                "  Abort",
                "",
            ])
        if sysreq.min_ram_mb:
            mb = sysreq.min_ram_mb
            lines.extend([
                f"  ; Check physical memory >= {mb} MB",
                f'  nsExec::ExecToStack \'powershell -NoProfile -Command "& {{ $m = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1MB; if ($m -lt {mb}) {{ exit 1 }} }}"\'',
                "  Pop $0",
                '  StrCmp $0 "0" +3 0',
            ])
            mem_text = '$(NOT_ENOUGH_MEMORY)' if cfg.languages else f'Not enough physical memory. Require at least {mb} MB.'
            lines.append(f'  MessageBox MB_OK|MB_ICONSTOP "{mem_text}"')
            lines.extend([
                "  Abort",
                "",
            ])
        if sysreq.require_admin:
            lines.extend([
                "  ; Ensure running as administrator (UAC check)",
                "  UserInfo::GetAccountType",
                "  Pop $0",
                '  StrCmp $0 "Admin" +3 0',
            ])
            admin_text = '$(NEED_ADMIN)' if cfg.languages else 'This installer requires administrator privileges.'
            lines.append(f'  MessageBox MB_OK|MB_ICONSTOP "{admin_text}"')
            lines.extend([
                "  Abort",
                "",
            ])

    # Installer logging — LogSet is only available when NSIS was compiled
    # with NSIS_CONFIG_LOG.
    if cfg.logging and cfg.logging.enabled:
        lines.extend([
            '!ifdef NSIS_CONFIG_LOG',
            '  LogSet on',
            '!endif',
        ])

    # ------------------------------------------------------------------
    # Existing-install detection and behavior
    # ------------------------------------------------------------------
    lines.extend(_generate_existing_install_check(ctx))

    # Default shortcut checkbox states (for silent installs where the
    # ShortcutOptions page is skipped)
    all_sc = collect_all_shortcuts(ctx)
    if all_sc:
        lines.append('  ; Default shortcut states (overridden by ShortcutOptions page)')
        for sc in all_sc:
            if not sc.config.optional:
                state = "1"
            else:
                state = "1" if sc.config.default else "0"
            lines.append(f'  StrCpy $CREATE_SC_{sc.idx} "{state}"')
        lines.append('')

    # Section flags for packages
    flat = _flatten_packages(cfg.packages)
    for idx, pkg in enumerate(flat):
        sec = f"SEC_PKG_{idx}"
        if pkg.optional and not pkg.default:
            lines.append(f"  SectionSetFlags ${{{sec}}} 0")
        elif not pkg.optional:
            # When not optional, make it selected AND read-only (unselectable)
            # SF_SELECTED | SF_RO = 1 | 16 = 17
            lines.append(f"  SectionSetFlags ${{{sec}}} 17")

    lines.extend([
        "FunctionEnd",
        "",
    ])
    return lines


def _generate_existing_install_check(ctx: BuildContext) -> List[str]:
    """Generate NSIS code for existing-install detection and handling.

    Uses ``ExistingInstallConfig`` to drive the behavior.  Supports:
    * version comparison (skip detection when same version is installed)
    * allow_multiple (only detect if same $INSTDIR)
    * configurable uninstaller args
    * proper _wait_uninstall loop
    * show_version_info in prompt
    """
    ei = ctx.config.install.existing_install
    if not ei or ei.mode == "none":
        return []

    cfg = ctx.config
    has_logging = bool(cfg.logging and cfg.logging.enabled)
    prompt_text = '$(UNINSTALL_NOT_FINISHED)' if cfg.languages else \
        'The previous uninstaller did not finish.  Retry or cancel installation?'

    # When allow_multiple is True we intentionally DO NOT perform a
    # directory-specific existence check in .onInit (because $INSTDIR is
    # still the default path). Instead we defer the check until the user
    # has chosen an installation directory (directory page leave callback).
    if ei.allow_multiple:
        lines: List[str] = [
            "",
            "  ; ------------------------------------------------------------------",
            "  ; Existing-install detection (deferred to directory page because allow_multiple=true)",
            "  ; ------------------------------------------------------------------",
            "  ; NOTE: Actual path collision detection will run in Function ExistingInstall_DirLeave",
        ]
        return lines

    lines: List[str] = [
        "",
        "  ; ------------------------------------------------------------------",
        "  ; Existing-install detection",
        "  ; ------------------------------------------------------------------",
        f'  SetRegView {ctx.effective_reg_view}',
        '  ReadRegStr $R0 HKLM "${REG_KEY}" "InstallPath"',
        '  StrCmp $R0 "" _ei_done  ; No previous install registered',
    ]

    # $R1 = install path for messages / uninstaller call
    lines.extend([
        '  StrCpy $R1 $R0',
    ])

    # Check for uninstaller
    lines.extend([
        '  IfFileExists "$R1\\Uninstall.exe" _ei_has_uninst _ei_overwrite_only',
    ])

    # --- _ei_has_uninst ---
    lines.append('_ei_has_uninst:')

    # Only read/show installed package version when we have confirmed a real installation
    # (i.e., the uninstaller exists in the registered install directory).
    if ei.version_check or ei.show_version_info:
        lines.extend([
            '  ; Derive installed package version from Uninstall.exe ProductVersion (WinAPI)',
            '  StrCpy $R6 "ProductVersion"',
            '  Push "$R1\\Uninstall.exe"',
            '  Call _YPACK_GetFileProductVersion',
            '  Pop $R2',
            '  StrCmp $R2 "" 0 _ei_ver_done',
            '  ; Fallback: use numeric file version (VS_FIXEDFILEINFO)',
            '  StrCpy $R6 "FileVersionFixed"',
            '  GetDLLVersion "$R1\\Uninstall.exe" $0 $1',
            '  StrCmp $0 0 +2 0',
            '  Goto +3',
            '  StrCmp $1 0 +2 0',
            '  Goto +1',
            '  StrCpy $R2 ""',
            '  IntOp $2 $0 >> 16',
            '  IntOp $3 $0 & 0xFFFF',
            '  IntOp $4 $1 >> 16',
            '  IntOp $5 $1 & 0xFFFF',
            '  StrCpy $R2 "$2.$3.$4.$5"',
            '  StrCmp $R2 "0.0.0.0" 0 +2',
            '    StrCpy $R2 ""',
            '_ei_ver_done:',
        ])

        if has_logging:
            lines.extend([
                '  !insertmacro _YPACK_DebugLog "[YPACK] ExistingInstall: resolved version=$R2 source=$R6 (path=$R1)"',
            ])

    # Version check: skip detection when installed version matches
    if ei.version_check:
        lines.extend([
            '  ; Skip if same version is already installed',
            '  StrCmp $R2 "${APP_VERSION}" _ei_done 0',
            '  StrCmp $R2 "${APP_VERSION_VI}" _ei_done',
        ])

    if ei.mode == "prompt_uninstall":
        if ei.show_version_info:
            prompt_ver = '$(EXISTING_INSTALL_PROMPT)' if cfg.languages else 'An existing installation (version $R2) was found at:$\\r$\\n$R1$\\r$\\n$\\r$\\nUninstall it first and continue?'
            prompt_no_ver = '$(EXISTING_INSTALL_PROMPT_NO_VER)' if cfg.languages else 'An existing installation was found at:$\\r$\\n$R1$\\r$\\n$\\r$\\nUninstall it first and continue?'
            lines.append('  StrCmp $R2 "" _ei_prompt_no_ver 0')
            lines.append(f'  MessageBox MB_YESNO|MB_ICONQUESTION "{prompt_ver}" IDYES _ei_do_uninstall IDNO _ei_cancel')
            lines.append('  Goto _ei_prompt_done')
            lines.append('_ei_prompt_no_ver:')
            lines.append(f'  MessageBox MB_YESNO|MB_ICONQUESTION "{prompt_no_ver}" IDYES _ei_do_uninstall IDNO _ei_cancel')
            lines.append('_ei_prompt_done:')
        else:
            prompt_no_ver = '$(EXISTING_INSTALL_PROMPT_NO_VER)' if cfg.languages else 'An existing installation was found at:$\\r$\\n$R1$\\r$\\n$\\r$\\nUninstall it first and continue?'
            lines.append(f'  MessageBox MB_YESNO|MB_ICONQUESTION "{prompt_no_ver}" IDYES _ei_do_uninstall IDNO _ei_cancel')
    elif ei.mode == "auto_uninstall":
        lines.append('  Goto _ei_do_uninstall')
    elif ei.mode == "abort":
        if ei.show_version_info:
            abort_ver = '$(EXISTING_INSTALL_ABORT)' if cfg.languages else 'An existing installation (version $R2) was found at $R1. Installation aborted.'
            abort_no_ver = '$(EXISTING_INSTALL_ABORT_NO_VER)' if cfg.languages else 'An existing installation was found at $R1. Installation aborted.'
            lines.append('  StrCmp $R2 "" _ei_abort_no_ver 0')
            lines.append(f'  MessageBox MB_OK|MB_ICONSTOP "{abort_ver}"')
            lines.append('  Goto _eid_cancel')
            lines.append('_ei_abort_no_ver:')
            lines.append(f'  MessageBox MB_OK|MB_ICONSTOP "{abort_no_ver}"')
            lines.append('  Goto _eid_cancel')
        else:
            abort_no_ver = '$(EXISTING_INSTALL_ABORT_NO_VER)' if cfg.languages else 'An existing installation was found at $R1. Installation aborted.'
            lines.append(f'  MessageBox MB_OK|MB_ICONSTOP "{abort_no_ver}"')
            lines.append('  Goto _eid_cancel')
    elif ei.mode == "overwrite":
        lines.append('  Goto _ei_done  ; Overwrite mode: skip uninstall')

    # --- _ei_do_uninstall ---
    uninst_args = ei.uninstaller_args or "/S"
    wait_ms = ei.uninstall_wait_ms

    # If wait_ms < 0, perform an infinite wait (no timeout). Otherwise use a timed loop.
    if wait_ms is not None and int(wait_ms) < 0:
        lines.extend([
            '_ei_do_uninstall:',
        ])
        if has_logging:
            lines.append(f'  !insertmacro LogWrite "Running existing uninstaller: $R1\\Uninstall.exe {uninst_args}"')
            lines.append('  !insertmacro LogWrite "Waiting for uninstaller to finish (no timeout)"')
        lines.extend([
            f'  ExecWait \'$R1\\Uninstall.exe {uninst_args}\' $R4',
            '  ; Wait for uninstaller to finish (no timeout)',
            '  StrCpy $R3 0',
            '_ei_wait_loop:',
            '  Sleep 500',
            '  IntOp $R3 $R3 + 500',
            '  IfFileExists "$R1\\Uninstall.exe" _ei_wait_loop _ei_wait_done',
            '_ei_wait_done:',
            '  ; Verify uninstaller is gone',
            '  IfFileExists "$R1\\Uninstall.exe" 0 _ei_done',
        ])
        if has_logging:
            lines.append('  !insertmacro LogWrite "Uninstaller finished."')
        lines.extend([
            f'  MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "{prompt_text}" IDRETRY _ei_do_uninstall',
            '  ; Fall through to cancel',
        ])
    else:
        # Timed wait loop (default behaviour)
        lines.extend([
            '_ei_do_uninstall:',
        ])
        if has_logging:
            lines.append(f'  !insertmacro LogWrite "Running existing uninstaller: $R1\\Uninstall.exe {uninst_args}"')
            lines.append(f'  !insertmacro LogWrite "Waiting for uninstaller to finish (up to {wait_ms}ms)"')
        lines.extend([
            f'  ExecWait \'$R1\\Uninstall.exe {uninst_args}\' $R4',
            '  StrCmp $R4 "0" _ei_done',
            f'  ; Wait for uninstaller to finish (up to {wait_ms}ms)',
            '  StrCpy $R3 0',
            '_ei_wait_loop:',
            f'  ; Loop: if $R3 >= {wait_ms} goto _ei_wait_done, else continue waiting',
            f'  IntCmp $R3 {wait_ms} _ei_wait_done _ei_wait_done _ei_wait_continue',
            '_ei_wait_continue:',
            '  Sleep 500',
            '  IntOp $R3 $R3 + 500',
            '  IfFileExists "$R1\\Uninstall.exe" _ei_wait_loop _ei_wait_done',
            '_ei_wait_done:',
            '  ; Verify uninstaller is gone',
            '  IfFileExists "$R1\\Uninstall.exe" 0 _ei_done',
        ])
        if has_logging:
            lines.append('  !insertmacro LogWrite "Uninstaller finished."')
            lines.append('  !insertmacro LogWrite "Uninstaller returned a non-zero exit code."')
        lines.extend([
            f'  MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "{prompt_text}" IDRETRY _ei_do_uninstall',
            '  ; Fall through to cancel',
        ])

    # --- _ei_cancel ---
    lines.extend([
        '_ei_cancel:',
        '  Abort',
    ])

    # --- _ei_overwrite_only ---
    lines.extend([
        '_ei_overwrite_only:',
        '  ; No uninstaller found \u2014 files will be overwritten',
    ])

    lines.append('_ei_done:')
    lines.append(f'  SetRegView lastused')
    lines.append('')
    return lines


def generate_existing_install_helpers(ctx: BuildContext) -> List[str]:
    """Emit helper functions for existing-install handling.

    When ``allow_multiple`` is true we generate a directory-page leave
    callback function that checks the *selected* $INSTDIR for an existing
    installation and performs the same prompting/uninstall logic used in
    the .onInit flow.
    """
    cfg = ctx.config
    has_logging = bool(cfg.logging and cfg.logging.enabled)

    ei = cfg.install.existing_install
    if not ei or ei.mode == "none":
        return []

    needs_version = bool(ei.version_check or ei.show_version_info)
    lines: List[str] = []

    # Define _YPACK_DebugLog macro if it will be used anywhere in this helper section.
    # This includes both version-checking code AND allow_multiple logging.
    # Prevents "macro not found" errors when logging or version checking is needed.
    if needs_version or ei.allow_multiple:
        # Always define _YPACK_DebugLog macro (either with implementation if logging is on,
        # or as empty stub if logging is off). This prevents "macro not found" errors
        # when the function that calls it is generated.
        # Use a macro (inline expansion) instead of a Function to avoid
        # stack-interaction issues when called from nested helper functions
        # like _YPACK_GetFileProductVersion.
        # Use high registers ($R7-$R9) to minimize conflicts with function code.
        
        if has_logging:
            lines.extend([
                '',
                '  ; ------------------------------------------------------------------',
                '  ; Early debug log macro (independent from install log; works in .onInit)',
                '  ; Writes to: $TEMP\\ypack-debug.log',
                '  ; Implemented as !macro to avoid nested-function stack conflicts.',
                '  ; Uses $R7/$R8 (high registers) to avoid conflicts with main code.',
                '  ; ------------------------------------------------------------------',
                '!macro _YPACK_DebugLog _msg',
                '  Push $R7',
                '  Push $R8',
                '  StrCpy $R7 `${_msg}`',
                '  FileOpen $R8 "$TEMP\\ypack-debug.log" a',
                '  IntCmp $R8 0 +4',
                '  FileSeek $R8 0 END',
                '  FileWrite $R8 "$R7$\\r$\\n"',
                '  FileClose $R8',
                '  Pop $R8',
                '  Pop $R7',
                '!macroend',
                '',
            ])
        else:
            # Logging disabled: define empty stub macro to prevent "macro not found" errors
            lines.extend([
                '',
                '  ; ------------------------------------------------------------------',
                '  ; Debug log macro stub (logging disabled)',
                '  ; ------------------------------------------------------------------',
                '!macro _YPACK_DebugLog _msg',
                '  ; (logging disabled)',
                '!macroend',
                '',
            ])

    if needs_version:
        lines.extend([
            '',
            '  ; ------------------------------------------------------------------',
            '  ; VersionInfo helper: read ProductVersion from a file (WinAPI)',
            '  ; ------------------------------------------------------------------',
            'Function _YPACK_GetFileProductVersion',
            '  Exch $0  ; file path',
            '  Push $1',
            '  Push $2',
            '  Push $3',
            '  Push $4',
            '  Push $5',
            '  Push $6',
            '  Push $7',
            '  Push $8',
            '  StrCpy $9 ""',
            '  !insertmacro _YPACK_DebugLog "[YPACK] VerInfo: reading ProductVersion from: $0"',
            '  ; DWORD GetFileVersionInfoSizeW(LPCWSTR lptstrFilename, LPDWORD lpdwHandle);',
            '  System::Call \'version::GetFileVersionInfoSizeW(w r0, *i .r1) i .r2\'',
            '  !insertmacro _YPACK_DebugLog "[YPACK] VerInfo: GetFileVersionInfoSizeW -> size=$2"',
            '  StrCmp $2 0 _ypack_ver_done',
            '  System::Alloc $2',
            '  Pop $3',
            '  !insertmacro _YPACK_DebugLog "[YPACK] VerInfo: Alloc -> ptr=$3"',
            '  StrCmp $3 0 _ypack_ver_done',
            '  ; BOOL GetFileVersionInfoW(LPCWSTR, DWORD, DWORD, LPVOID);',
            '  System::Call \'version::GetFileVersionInfoW(w r0, i 0, i r2, i r3) i .r4\'',
            '  !insertmacro _YPACK_DebugLog "[YPACK] VerInfo: GetFileVersionInfoW -> ok=$4"',
            '  StrCmp $4 0 _ypack_ver_free',
            '  ; BOOL VerQueryValueW(LPCVOID, LPCWSTR, LPVOID*, PUINT);',
            '  System::Call \'version::VerQueryValueW(i r3, w "\\VarFileInfo\\Translation", *p .r5, *i .r6) i .r7\'',
            '  !insertmacro _YPACK_DebugLog "[YPACK] VerInfo: Translation query -> ok=$7 ptr=$5 len=$6"',
            '  StrCmp $7 0 _ypack_ver_fallback_lang',
            '  ; Read first LANGANDCODEPAGE as a DWORD (low WORD=lang, high WORD=codepage)',
            '  System::Call "*$5(&i .r8)"',
            '  IntOp $6 $8 & 0xFFFF',
            '  IntOp $7 $8 >> 16',
            '  IntFmt $1 "%04X" $6',
            '  IntFmt $2 "%04X" $7',
            '  StrCpy $1 "$1$2"',
            '  ; If Translation returned 0x00000000, skip it and use common fallbacks',
            '  StrCmp $1 "00000000" _ypack_ver_fallback_lang',
            '  Goto _ypack_ver_query',
            '_ypack_ver_fallback_lang:',
            '  ; Fallback to common language/codepage combinations',
            '  ; Try 0409/04B0 (English/Unicode), most common for installers',
            '  StrCpy $1 "040904B0"',
            '  Goto _ypack_ver_query',
            '_ypack_ver_query:',
            '  StrCpy $2 "\\StringFileInfo\\$1\\ProductVersion"',
            '  !insertmacro _YPACK_DebugLog "[YPACK] VerInfo: Query ProductVersion with langcp=$1"',
            '  System::Call \'version::VerQueryValueW(i r3, w r2, *p .r5, *i .r6) i .r7\'',
            '  StrCmp $7 0 _ypack_ver_try_next_lang',
            '  System::Call "*$5(&t${NSIS_MAX_STRLEN} .r9)"',
            '  !insertmacro _YPACK_DebugLog "[YPACK] VerInfo: ProductVersion=$9"',
            '  StrCmp $9 "" 0 _ypack_ver_ok',
            '  ; ProductVersion missing: try FileVersion string key',
            '  StrCpy $2 "\\StringFileInfo\\$1\\FileVersion"',
            '  !insertmacro _YPACK_DebugLog "[YPACK] VerInfo: ProductVersion empty; trying FileVersion string"',
            '  System::Call \'version::VerQueryValueW(i r3, w r2, *p .r5, *i .r6) i .r7\'',
            '  StrCmp $7 0 _ypack_ver_try_next_lang',
            '  System::Call "*$5(&t${NSIS_MAX_STRLEN} .r9)"',
            '  Goto _ypack_ver_ok',
            '_ypack_ver_try_next_lang:',
            '  !insertmacro _YPACK_DebugLog "[YPACK] VerInfo: Query failed; trying next langcp..."',
            '  ; Cycle through common langcp values: 040904B0 -> 080404B0 -> 000004B0 -> give up',
            '  StrCmp $1 "040904B0" 0 +3',
            '  StrCpy $1 "080404B0"',
            '  Goto _ypack_ver_query',
            '  StrCmp $1 "080404B0" 0 +3',
            '  StrCpy $1 "000004B0"',
            '  Goto _ypack_ver_query',
            '  Goto _ypack_ver_free',
            '_ypack_ver_ok:',
            '  ; $9 now contains ProductVersion/FileVersion (or empty)',
            '  StrCpy $9 $9',
            '_ypack_ver_free:',
            '  StrCmp $3 0 _ypack_ver_done',
            '  System::Free $3',
            '_ypack_ver_done:',
            '  Pop $8',
            '  Pop $7',
            '  Pop $6',
            '  Pop $5',
            '  Pop $4',
            '  Pop $3',
            '  Pop $2',
            '  Pop $1',
            '  Exch $9',
            'FunctionEnd',
            '',
        ])

    if not ei.allow_multiple:
        return lines

    prompt_text = '$(UNINSTALL_NOT_FINISHED)' if cfg.languages else \
        'The previous uninstaller did not finish.  Retry or cancel installation?'

    entry_log: List[str] = []
    if has_logging:
        entry_log = [
            '  !insertmacro _YPACK_DebugLog "[YPACK] ExistingInstall_DirLeave: ENTRY user-selected INSTDIR=$INSTDIR"',
        ]

    lines.extend([
        "",
        "  ; ------------------------------------------------------------------",
        "  ; Existing-install helpers (directory page leave callback)",
        "  ; ------------------------------------------------------------------",
        "Function ExistingInstall_DirLeave",
        "",
        *entry_log,
        f'  SetRegView {ctx.effective_reg_view}',
        "  ; Check the user-selected directory ($INSTDIR) for an uninstaller",
        '  StrCpy $R1 $INSTDIR',
    ])

    if has_logging:
        lines.append('  !insertmacro _YPACK_DebugLog "[YPACK] ExistingInstall_DirLeave: checking path=$R1"')

    lines.extend([
        '  IfFileExists "$R1\\Uninstall.exe" _eid_has_uninst _eid_check_reg',
    ])

    if has_logging:
        lines.append('  !insertmacro _YPACK_DebugLog "[YPACK] ExistingInstall_DirLeave: no Uninstall.exe found at selected path, checking registry..."')

    lines.extend([
        '  Goto _eid_done',
        '',
        '_eid_check_reg:',
    ])

    if has_logging:
        lines.append('  !insertmacro _YPACK_DebugLog "[YPACK] ExistingInstall_DirLeave: Uninstall.exe found; checking registry match..."')

    lines.extend([
        '  ; Also consider the registered install path as a match',
        '  ReadRegStr $R0 HKLM "${REG_KEY}" "InstallPath"',
    ])

    if has_logging:
        lines.append('  !insertmacro _YPACK_DebugLog "[YPACK] ExistingInstall_DirLeave: registry InstallPath=$R0"')

    lines.extend([
        '  StrCmp $R0 "$R1" 0 _eid_done',
        '  ; Path matches registry; still require an actual uninstaller at that path',
        '  IfFileExists "$R1\\Uninstall.exe" _eid_has_uninst _eid_done',
        '',
        '_eid_has_uninst:',
    ])

    # Optionally read installed version for prompts / version check
    if ei.version_check or ei.show_version_info:
        pre_call_logs: List[str] = []
        post_call_logs: List[str] = []
        fallback_logs: List[str] = []
        if has_logging:
            pre_call_logs = [
                '  !insertmacro _YPACK_DebugLog "[YPACK] ExistingInstall_DirLeave: entering ProductVersion branch (target=$R1\\Uninstall.exe)"',
            ]
            post_call_logs = [
                '  !insertmacro _YPACK_DebugLog "[YPACK] ExistingInstall_DirLeave: ProductVersion raw result=$R2"',
            ]
            fallback_logs = [
                '  !insertmacro _YPACK_DebugLog "[YPACK] ExistingInstall_DirLeave: ProductVersion empty -> fallback GetDLLVersion"',
            ]

        lines.extend([
            '  ; Derive installed package version from Uninstall.exe ProductVersion (WinAPI)',
            '  StrCpy $R6 "ProductVersion"',
            *pre_call_logs,
            '  Push "$R1\\Uninstall.exe"',
            '  Call _YPACK_GetFileProductVersion',
            '  Pop $R2',
            *post_call_logs,
            '  StrCmp $R2 "" 0 _eid_ver_done',
            '  ; Fallback: use numeric file version (VS_FIXEDFILEINFO)',
            *fallback_logs,
            '  StrCpy $R6 "FileVersionFixed"',
            '  GetDLLVersion "$R1\\Uninstall.exe" $0 $1',
            '  StrCmp $0 0 +2 0',
            '  Goto +3',
            '  StrCmp $1 0 +2 0',
            '  Goto +1',
            '  StrCpy $R2 ""',
            '  IntOp $2 $0 >> 16',
            '  IntOp $3 $0 & 0xFFFF',
            '  IntOp $4 $1 >> 16',
            '  IntOp $5 $1 & 0xFFFF',
            '  StrCpy $R2 "$2.$3.$4.$5"',
            '  StrCmp $R2 "0.0.0.0" 0 +2',
            '    StrCpy $R2 ""',
            '_eid_ver_done:',
        ])

        if has_logging:
            lines.extend([
                '  !insertmacro _YPACK_DebugLog "[YPACK] ExistingInstall_DirLeave: resolved version=$R2 source=$R6 (path=$R1)"',
            ])

    # Version check: skip prompting/uninstall when installed version matches
    if ei.version_check:
        lines.extend([
            '  ; Skip if same version is already installed',
            '  StrCmp $R2 "${APP_VERSION}" _eid_done 0',
            '  StrCmp $R2 "${APP_VERSION_VI}" _eid_done',
        ])

    # Prompt / behavior
    if ei.mode == "prompt_uninstall":
        if ei.show_version_info:
            prompt_ver = '$(EXISTING_INSTALL_PROMPT)' if cfg.languages else 'An existing installation (version $R2) was found at:$\\r$\\n$R1$\\r$\\n$\\r$\\nUninstall it first and continue?'
            prompt_no_ver = '$(EXISTING_INSTALL_PROMPT_NO_VER)' if cfg.languages else 'An existing installation was found at:$\\r$\\n$R1$\\r$\\n$\\r$\\nUninstall it first and continue?'
            lines.append('  StrCmp $R2 "" _eid_prompt_no_ver 0')
            lines.append(f'  MessageBox MB_YESNO|MB_ICONQUESTION "{prompt_ver}" IDYES _eid_do_uninstall IDNO _eid_cancel')
            lines.append('  Goto _eid_prompt_done')
            lines.append('_eid_prompt_no_ver:')
            lines.append(f'  MessageBox MB_YESNO|MB_ICONQUESTION "{prompt_no_ver}" IDYES _eid_do_uninstall IDNO _eid_cancel')
            lines.append('_eid_prompt_done:')
        else:
            prompt_no_ver = '$(EXISTING_INSTALL_PROMPT_NO_VER)' if cfg.languages else 'An existing installation was found at:$\\r$\\n$R1$\\r$\\n$\\r$\\nUninstall it first and continue?'
            lines.append(f'  MessageBox MB_YESNO|MB_ICONQUESTION "{prompt_no_ver}" IDYES _eid_do_uninstall IDNO _eid_cancel')
    elif ei.mode == "auto_uninstall":
        lines.append('  Goto _eid_do_uninstall')
    elif ei.mode == "abort":
        if ei.show_version_info:
            abort_ver = '$(EXISTING_INSTALL_ABORT)' if cfg.languages else 'An existing installation (version $R2) was found at $R1. Installation aborted.'
            abort_no_ver = '$(EXISTING_INSTALL_ABORT_NO_VER)' if cfg.languages else 'An existing installation was found at $R1. Installation aborted.'
            lines.append('  StrCmp $R2 "" _eid_abort_no_ver 0')
            lines.append(f'  MessageBox MB_OK|MB_ICONSTOP "{abort_ver}"')
            lines.append('  Goto _eid_cancel')
            lines.append('_eid_abort_no_ver:')
            lines.append(f'  MessageBox MB_OK|MB_ICONSTOP "{abort_no_ver}"')
            lines.append('  Goto _eid_cancel')
        else:
            abort_no_ver = '$(EXISTING_INSTALL_ABORT_NO_VER)' if cfg.languages else 'An existing installation was found at $R1. Installation aborted.'
            lines.append(f'  MessageBox MB_OK|MB_ICONSTOP "{abort_no_ver}"')
            lines.append('  Goto _eid_cancel')
    elif ei.mode == "auto_uninstall":
        lines.append('  Goto _eid_do_uninstall')
    elif ei.mode == "abort":
        if ei.show_version_info:
            lines.extend([
                '  StrCmp $R2 "" _eid_abort_no_ver 0',
                '  MessageBox MB_OK|MB_ICONSTOP "An existing installation (version $R2) was found at $R1. Installation aborted."',
                '  Goto _eid_cancel',
                '_eid_abort_no_ver:',
                '  MessageBox MB_OK|MB_ICONSTOP "An existing installation was found at $R1. Installation aborted."',
                '  Goto _eid_cancel',
            ])
        else:
            lines.extend([
                '  MessageBox MB_OK|MB_ICONSTOP "An existing installation was found at $R1. Installation aborted."',
                '  Goto _eid_cancel',
            ])
    elif ei.mode == "overwrite":
        lines.append('  Goto _eid_done  ; Overwrite mode: skip uninstall')

    # Uninstall execution and wait loop
    uninst_args = ei.uninstaller_args or "/S"
    wait_ms = ei.uninstall_wait_ms

    if wait_ms is not None and int(wait_ms) < 0:
        lines.extend([
            '_eid_do_uninstall:',
        ])
        if has_logging:
            lines.append(f'  !insertmacro LogWrite "Running existing uninstaller: $R1\\Uninstall.exe {uninst_args}"')
            lines.append('  !insertmacro LogWrite "Waiting for uninstaller to finish (no timeout)"')
        lines.extend([
            f'  ExecWait \'$R1\\Uninstall.exe {uninst_args}\' $R4',
            '  StrCmp $R4 "0" _eid_done',
            f'  MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "{prompt_text}" IDRETRY _eid_do_uninstall IDCANCEL _eid_cancel',
        ])
    else:
        lines.extend([
            '_eid_do_uninstall:',
        ])
        if has_logging:
            lines.append(f'  !insertmacro LogWrite "Running existing uninstaller: $R1\\Uninstall.exe {uninst_args}"')
            lines.append(f'  !insertmacro LogWrite "Waiting for uninstaller to finish (up to {wait_ms}ms)"')
        lines.extend([
            f'  ExecWait \'$R1\\Uninstall.exe {uninst_args}\' $R4',
            '  StrCmp $R4 "0" _eid_done',
        ])
        if has_logging:
            lines.append('  !insertmacro LogWrite "Uninstaller returned a non-zero exit code."')
        lines.extend([
            f'  MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "{prompt_text}" IDRETRY _eid_do_uninstall IDCANCEL _eid_cancel',
        ])

    lines.extend([
        '',
        '_eid_cancel:',
        '  Abort',
        '',
        '_eid_done:',
    ])

    if has_logging:
        lines.append('  !insertmacro _YPACK_DebugLog "[YPACK] ExistingInstall_DirLeave: EXIT (no conflict or after uninstall)"')

    lines.extend([
        '  SetRegView lastused',
        '',
        'FunctionEnd',
        '',
    ])

    return lines


def generate_uninit(ctx: BuildContext) -> List[str]:
    """Emit ``un.onInit`` \u2014 uninstaller mutex and confirmation."""
    cfg = ctx.config
    lines: List[str] = [
        "; ===========================================================================",
        "; Uninstaller Initialization",
        "; ===========================================================================",
        "Function un.onInit",
        "",
        '  ; Prevent multiple uninstaller instances',
        '  System::Call \'kernel32::CreateMutex(p 0, i 0, t "${APP_NAME}_UninstallerMutex") p .r1 ?e\'',
        '  Pop $R0',
        '  StrCmp $R0 "0" +3 0',
        '  MessageBox MB_OK|MB_ICONEXCLAMATION "The uninstaller is already running."',
        '  Abort',
        '',
    ]

    # Logging
    if cfg.logging and cfg.logging.enabled:
        lines.extend([
            '!ifdef NSIS_CONFIG_LOG',
            '  LogSet on',
            '!endif',
        ])

    lines.extend([
        "FunctionEnd",
        "",
    ])
    return lines


# -----------------------------------------------------------------------
# Internal
# -----------------------------------------------------------------------

def _file_line(ctx: BuildContext, source: str) -> str:
    """Build a single ``File`` directive, choosing /r when appropriate."""
    resolved = ctx.resolve_path(source)
    if os.path.exists(resolved):
        path_for_nsi = resolved
    else:
        path_for_nsi = _normalize_path(source)
    if _should_use_recursive(source):
        return f'  File /r "{path_for_nsi}"'
    return f'  File "{path_for_nsi}"'
