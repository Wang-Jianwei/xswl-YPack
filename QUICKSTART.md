# Quick Start Guide

## Installation

```bash
pip install xswl-ypack
```

Or install from source with dev tools:

```bash
git clone https://github.com/Wang-Jianwei/xswl-YPack.git
cd xswl-YPack
pip install -e ".[dev,validation]"
```

## Basic Usage

### 使用 Web UI（可选）

如果想要可视化编辑器与在线校验/保存功能，可以运行内置的 Web UI：

```bash
# 安装 Web UI 依赖
pip install -e ".[web]"

# 启动服务器（支持 --host --port --debug）
xswl-ypack-web --host 127.0.0.1 --port 5000

# 或使用 Windows 启动脚本
.\scripts\start-web-ui.ps1
```

Web UI 暴露的常用 API（适用于自动化或前端集成）：

- GET  /api/health
- GET  /api/schema
- GET  /api/schema/enums
- POST /api/validate/yaml
- POST /api/validate/config
- POST /api/project/new
- POST /api/project/load
- POST /api/project/save
- GET  /api/variables/builtin

---

### 1. Generate a starter configuration

```bash
xswl-ypack init
```

This creates `installer.yaml` with sensible defaults.

### 2. Edit the YAML

```yaml
app:
  name: MyApp
  version: "1.0.0"
  publisher: My Company

install:
  install_dir: "$PROGRAMFILES64\\MyApp"
  desktop_shortcut:
    name: "${app.name}"
    target: "$INSTDIR\\MyApp.exe"
  start_menu_shortcut:
    name: "${app.name}"
    target: "$INSTDIR\\MyApp.exe"
  # existing_install controls behavior when a prior install is found (default: prompt_uninstall)
  # Simple:   existing_install: "prompt_uninstall"
  # Full:     existing_install: { mode: "prompt_uninstall", version_check: true, allow_multiple: false, uninstall_wait_ms: 15000 }
  # Tip: set "uninstall_wait_ms: -1" to wait indefinitely for the previous uninstaller (use with caution)
  existing_install: "prompt_uninstall"
files:
  - MyApp.exe
  - config.json
```

Notes:

- Use `desktop_shortcut` / `start_menu_shortcut` object form to set an explicit `name` (optional) and `target` (required).
- The legacy `desktop_shortcut_target` / `start_menu_shortcut_target` fields are still accepted for backward compatibility but are deprecated in favor of the structured form.

> **Pattern semantics:**
>
> - `dir/*` — direct children only (non-recursive).
> - `dir/**/*` — recursive (generates `File /r`).

### 3. Validate the configuration

```bash
xswl-ypack validate installer.yaml -v
```

### 4. Generate the installer script

```bash
# Default: NSIS
xswl-ypack convert installer.yaml

# Specify format explicitly (nsis / wix / inno)
xswl-ypack convert installer.yaml -f nsis

# Build and set custom installer filename
xswl-ypack convert installer.yaml --build --installer-name "MyApp-1.2.3-Setup.exe"
```

This generates `installer.nsi` in the same directory.

> Note: Generated scripts are written as **UTF-8 with BOM** (`utf-8-sig`) to ensure NSIS correctly handles Unicode characters.

### 5. Preview without writing a file

```bash
# short: -n
xswl-ypack convert installer.yaml --dry-run
```

### 6. Build the installer (requires compiler)

```bash
# Default: uses `makensis` from PATH. 也可以通过 --makensis 指定路径：
xswl-ypack convert installer.yaml --build --makensis "C:\Program Files\NSIS\makensis.exe"
```

This generates the `.nsi` file and runs `makensis` to build `MyApp-1.0.0-Setup.exe`.

> Currently, `--build` is supported for NSIS only. WIX and Inno Setup backends are coming soon.

## Example Workflows

### Python Project (PyInstaller)

```yaml
app:
  name: MyPythonApp
  version: "1.0.0"

files:
  - dist/MyPythonApp.exe
  - source: "dist/_internal/**/*"
    destination: "$INSTDIR\\_internal"
```

### C++ Project

```yaml
app:
  name: MyCppApp
  version: "2.0.0"

files:
  - Release/MyCppApp.exe
  - source: "Release/*.dll"
    destination: "$INSTDIR"
```

### Go Project

```yaml
app:
  name: MyGoApp
  version: "1.5.0"

files:
  - build/MyGoApp.exe
  - config.yaml
```

## Visualization

项目包含一个命令行工具 `tools/yaml_to_mermaid.py`，用于把 `installer.yaml` 转换为 Mermaid 源或交互式 HTML：

```bash
# 输出 mermaid（.mmd）
python -m tools.yaml_to_mermaid installer.yaml -o installer.mmd
# 生成交互式 HTML
python -m tools.yaml_to_mermaid installer.yaml --html installer.html
```

---

## Advanced Features

### Registry Entries

```yaml
install:
  registry_entries:
    - hive: HKLM
      key: "Software\\MyApp"
      name: UpdateURL
      value: "https://example.com/updates"
      type: string
      view: "64"
```

### Environment Variables

```yaml
install:
  env_vars:
    - name: PATH
      value: "$INSTDIR\\bin"
      scope: system
      append: true
```

### Code Signing

```yaml
signing:
  enabled: true
  certificate: cert.pfx
  password: your_password
  timestamp_url: http://timestamp.digicert.com
```

### Auto-Update

```yaml
update:
  enabled: true
  update_url: https://example.com/latest.json
  download_url: https://example.com/download
  backup_on_upgrade: true
```

### Custom NSIS Includes

```yaml
custom_includes:
  nsis:
    - custom_functions.nsh
    - extra_pages.nsh
```

## Testing

```bash
pytest tests/ -v
```

## More Information

See the full [README.md](README.md) for detailed configuration reference.
