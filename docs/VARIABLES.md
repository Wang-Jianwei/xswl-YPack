# Variable system (built-in variables) 🔧

This document describes the variable system used in YAML configurations and lists all built-in variables supported by the converters.

## Syntax overview

- **Built-in runtime variables**: use `$NAME` (e.g. `$INSTDIR`, `$APPDATA`). These are mapped to tool-specific forms during conversion (NSIS/WIX/Inno).
- **Configuration references**: use `${path.to.value}` (e.g. `${app.name}`) to reference values from the YAML config.
- **Custom variables (aliases)**: use `${variables.NAME}` and define them under a top-level `variables` mapping in YAML.
- **Escape**: `$$` → `$` (use `$$INSTDIR` to get literal `$INSTDIR`).

> Resolution order when generating scripts:
> 1. Expand `${...}` config references (including `${variables.NAME}`).
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

## Validation and behavior

- Unknown variables (e.g. `$UNKNOWN`) are preserved in the generated text; a **strict validation** option can raise errors on unknown variables when desired.
- Variable references may be nested; the resolver detects circular references and raises a `CircularReferenceError` when detected.

## Implementation reference

- Built-in definitions: `ypack/variables.py`
- Resolver: `ypack/resolver.py`

---

If you'd like, I can also add a short section to `README.md` linking to this page. 👍