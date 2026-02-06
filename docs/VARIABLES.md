# Variable system (built-in variables) 🔧

This document describes the variable system used in YAML configurations and lists all built-in variables supported by the converters.

## Syntax overview

- **Built-in runtime variables**: use `$NAME` (e.g. `$INSTDIR`, `$APPDATA`). These are mapped to tool-specific forms during conversion (NSIS/WIX/Inno).
- **Configuration references**: use `${path.to.value}` (e.g. `${app.name}`) to reference values from the YAML config.
- **Escape**: `$$` → `$` (use `$$INSTDIR` to get literal `$INSTDIR`).

> Resolution order when generating scripts:
> 1. Expand `${...}` config references (including `${path.to.value}`).
> 2. Convert `$NAME` built-in variables to the target tool's form (e.g. NSIS `$INSTDIR`, WIX `[INSTALLDIR]`).

## Examples

```yaml
app:
  name: "MyApp"
  publisher: "ACME"

variables:
  DATA_DIR: "$APPDATA\\${app.publisher}\\${app.name}"

files:
  - source: "./data/*"
    destination: "${variables.DATA_DIR}\\config"
```

- `${variables.DATA_DIR}` expands to `$APPDATA\ACME\MyApp` (in YAML phase).
- `$APPDATA` is converted to `[AppDataFolder]` when targeting WIX.

## Built-in variables (complete list)

| Variable | Description / 描述 | NSIS | WIX | Inno Setup |
|---|---|---:|---:|---:|
| `INSTDIR` | Installation directory chosen by user / 安装目录（由用户选择） | `$INSTDIR` | `[INSTALLDIR]` | `{app}` |
| `PROGRAMFILES` | Program Files folder (32-bit on 64-bit systems) / 程序文件目录（32 位/兼容） | `$PROGRAMFILES` | `[ProgramFilesFolder]` | `{pf}` |
| `PROGRAMFILES64` | Program Files (64-bit) / 程序文件目录（64 位） | `$PROGRAMFILES64` | `[ProgramFiles64Folder]` | `{pf64}` |
| `APPDATA` | Application Data folder (roaming) / 应用数据（漫游）目录 | `$APPDATA` | `[AppDataFolder]` | `{userappdata}` |
| `LOCALAPPDATA` | Local Application Data (non-roaming) / 本地应用数据（非漫游）目录 | `$LOCALAPPDATA` | `[LocalAppDataFolder]` | `{localappdata}` |
| `DESKTOP` | Desktop folder / 桌面目录 | `$DESKTOP` | `[DesktopFolder]` | `{userdesktop}` |
| `STARTMENU` | Start Menu folder / 开始菜单目录 | `$STARTMENU` | `[StartMenuFolder]` | `{userstartmenu}` |
| `SMPROGRAMS` | Start Menu Programs folder / 开始菜单程序目录（Programs） | `$SMPROGRAMS` | `[ProgramMenuFolder]` | `{userprograms}` |
| `TEMP` | Temporary folder / 临时目录 | `$TEMP` | `[TempFolder]` | `{tmp}` |
| `WINDIR` | Windows directory / Windows 系统目录 | `$WINDIR` | `[WindowsFolder]` | `{win}` |
| `SYSDIR` | System32 folder / System32 目录 | `$SYSDIR` | `[SystemFolder]` | `{sys}` |
| `COMMONFILES` | Common Files folder / 公共文件目录 | `$COMMONFILES` | `[CommonFilesFolder]` | `{cf}` |
| `COMMONFILES64` | Common Files folder (64-bit) / 公共文件目录（64 位） | `$COMMONFILES64` | `[CommonFiles64Folder]` | `{cf64}` |
| `DOCUMENTS` | My Documents / Personal folder / 文档目录（我的文档/个人文件夹） | `$DOCUMENTS` | `[PersonalFolder]` | `{userdocs}` |

> Note: converters may add more variables over time; consult `ypack/variables.py` for the authoritative list.

## ypack Language Identifiers (cross-platform)

ypack defines a set of language identifiers that are **independent of any particular installer tool**. Each converter then maps these identifiers to the target tool's language format.

| ypack Identifier | Description / 描述 | NSIS MUI | WIX | Inno Setup |
|---|---|---|---|---|
| `English` | English (US) / 英语（美国） | `English` | (TBD) | (TBD) |
| `SimplifiedChinese` | Simplified Chinese / 简体中文 | `SimplifiedChinese` | (TBD) | (TBD) |
| `TraditionalChinese` | Traditional Chinese / 繁體中文 | `TraditionalChinese` | (TBD) | (TBD) |
| `French` | French / 法语 | `French` | (TBD) | (TBD) |
| `German` | German / 德语 | `German` | (TBD) | (TBD) |
| `Spanish` | Spanish / 西班牙语 | `Spanish` | (TBD) | (TBD) |
| `Japanese` | Japanese / 日语 | `Japanese` | (TBD) | (TBD) |
| `Korean` | Korean / 韩语 | `Korean` | (TBD) | (TBD) |
| `Russian` | Russian / 俄语 | `Russian` | (TBD) | (TBD) |
| `Portuguese` | Portuguese (Portugal) / 葡萄牙语 | `Portuguese` | (TBD) | (TBD) |
| `BrazilianPortuguese` | Portuguese (Brazil) / 葡萄牙语（巴西） | `BrazilianPortuguese` | (TBD) | (TBD) |
| `Polish` | Polish / 波兰语 | `Polish` | (TBD) | (TBD) |
| `Czech` | Czech / 捷克语 | `Czech` | (TBD) | (TBD) |
| `Turkish` | Turkish / 土耳其语 | `Turkish` | (TBD) | (TBD) |
| `Hungarian` | Hungarian / 匈牙利语 | `Hungarian` | (TBD) | (TBD) |

> **Note on language support**: The list above is defined in `ypack/variables.py` (`YPACK_LANGUAGES`). Additional languages may be added as converters are extended. To use a language in YAML `languages` field, it must be listed in `YPACK_LANGUAGES` or explicitly handled by the converter.

## Tool-specific macros (NOT cross-platform)

Some installer converters define their own macros that appear in the generated scripts but are **tool-specific and should NOT be relied upon in YAML configuration** for cross-tool compatibility:

| Macro | Tool | Where it appears | Note / 注意 |
|---|---|---|---|
| `${APP_NAME}` | NSIS | Generated `.nsi` script | Defined by `convert_nsis.py` via `!define APP_NAME`. Do not use in YAML; use `${app.name}` (config reference) instead. |
| `${APP_VERSION}` | NSIS | Generated `.nsi` script | Defined by `convert_nsis.py` via `!define APP_VERSION`. Do not use in YAML. |
| `${APP_PUBLISHER}` | NSIS | Generated `.nsi` script | Defined by `convert_nsis.py` via `!define APP_PUBLISHER`. Do not use in YAML. |
| `${REG_KEY}` | NSIS | Generated `.nsi` script (registry operations) | Defined by `convert_nsis.py` via `!define REG_KEY "Software\<app.name>"`. Do not use in YAML; instead use portable config references like `registry_key: "Software\\${app.name}"`. |

> **Best practice**: In YAML configurations, use **cross-tool portable forms**:
> - For registry keys: use `"Software\\${app.name}"` or `"Software\\${app.publisher}\\${app.name}"` (config references)
> - Never reference tool-specific macros like `${REG_KEY}`, `${APP_NAME}` in your YAML files

## Validation and behavior

- Unknown variables (e.g. `$UNKNOWN`) are preserved in the generated text; a **strict validation** option can raise errors on unknown variables when desired.
- Variable references may be nested; the resolver detects circular references and raises a `CircularReferenceError` when detected.

## Implementation reference

- Built-in definitions: `ypack/variables.py`
- Resolver: `ypack/resolver.py`

---

If you'd like, I can also add a short section to `README.md` linking to this page. 👍