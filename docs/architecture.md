# 架构与工作流程 📦🔧

本文档说明 `xswl-YPack` v0.2.0 的内部架构与工作流程。

## 总览

```mermaid
flowchart LR
  subgraph CLI
    Start["xswl-ypack convert / validate / init"]
  end

  Start --> ParseConfig["加载 YAML<br>PackageConfig.from_yaml"]
  ParseConfig --> SchemaValidation["Schema 校验<br>schema.validate_config"]
  SchemaValidation --> BuildDataclasses["构建 dataclass 树<br>AppInfo / InstallConfig / ..."]

  BuildDataclasses --> ConverterInit["YamlToNsisConverter(config, raw_dict)"]
  ConverterInit --> CreateContext["创建 BuildContext<br>(config, raw_dict, resolver)"]
  CreateContext --> Convert["convert() → 组装各子模块"]

  subgraph Modules[NSIS 子模块]
    nsis_header["nsis_header.py<br>Unicode / defines / MUI"]
    nsis_sections["nsis_sections.py<br>Install & Uninstall Section"]
    nsis_packages["nsis_packages.py<br>Packages / Signing / Update / .onInit"]
    nsis_helpers["nsis_helpers.py<br>PATH helpers / checksum"]
  end

  Convert --> nsis_header
  Convert --> nsis_sections
  Convert --> nsis_packages
  Convert --> nsis_helpers

  nsis_header & nsis_sections & nsis_packages & nsis_helpers --> Assemble["拼接 → 完整 .nsi 字符串"]
  Assemble --> SaveOrDryRun{"--dry-run?"}
  SaveOrDryRun -->|否| Save["save() → 写入 installer.nsi（UTF-8 with BOM）"]
  SaveOrDryRun -->|是| Stdout["输出到 stdout"]



> Note: The on-disk script is written using UTF-8 with BOM (`utf-8-sig`) when saved, because NSIS requires a BOM to correctly interpret Unicode characters.
  Save --> OptionalBuild{"--build?"}
  OptionalBuild -->|是| Makensis["调用 makensis"]
  OptionalBuild -->|否| End["完成"]
  Makensis --> End

  style Start fill:#f9f,stroke:#333,stroke-width:1px
  style End fill:#bfb,stroke:#333,stroke-width:1px
```

---

## 模块职责 🧩

| 模块 | 职责 |
|---|---|
| `cli.py` | 子命令入口：`convert`（`-f` 格式选项）、`init`、`validate` |
| `config.py` | YAML → dataclass 解析；所有配置类定义 |
| `schema.py` | jsonschema 校验（可选 fallback） |
| `variables.py` | 内置变量定义（NSIS / WIX / Inno 三重映射）、语言定义 |
| `resolver.py` | `${config.ref}` / `$BUILTIN` 变量解析、循环引用检测 |
| `converters/__init__.py` | **转换器注册表**（`CONVERTER_REGISTRY` / `get_converter_class()`） |
| `converters/base.py` | `BaseConverter` 抽象基类（`tool_name` / `output_extension` / `convert` / `save`） |
| `converters/context.py` | `BuildContext`：共享上下文（`target_tool` 驱动 resolver & 路径分隔符） |
| `converters/convert_nsis.py` | `YamlToNsisConverter`：主组装器，调用各子模块 |
| `converters/nsis_header.py` | Unicode / defines / icons / MUI pages / general settings |
| `converters/nsis_sections.py` | Install Section（文件、注册表、环境变量、快捷方式、文件关联）<br>Uninstall Section（反向清理） |
| `converters/nsis_packages.py` | 组件 Section / SectionGroup / 签名 / 更新 / `.onInit` |
| `converters/nsis_helpers.py` | `_StrContains` / `_RemovePathEntry` 辅助函数 + 校验函数 |

---

## 关键设计决策 🔍

### BuildContext 模式

所有转换子模块通过 `BuildContext` 获取配置和变量解析，**不直接依赖**具体 Converter 实例。
`BuildContext.target_tool` 字段驱动：

- `create_resolver()` 选择对应后端的变量映射（NSIS / WIX / Inno）
- `path_separator` 属性根据目标工具返回正确的路径分隔符

这使得每个子模块可以独立测试，也保证了新增后端只需注册到 `CONVERTER_REGISTRY` 即可。

### NSIS 脚本正确性修复（v0.2.0）

| 问题 | 修复 |
|---|---|
| `SetOutPath` 未在每组文件前设置 | 每当 destination 变化时重新 emit |
| `_Contains` 函数死循环 | 重写为 `_StrContains`，正确使用标签和寄存器保存 |
| `StrReplace`（NSIS 不存在） | 替换为正确的内联字符串操作 |
| `${BypassUAC}`（不存在） | 替换为 `UserInfo::GetAccountType` |
| 缺少 `Unicode true` | 默认写入头部 |
| 卸载不删除 package 文件 | 在 Uninstall Section 中补全 |
| `SetRegView` 不恢复 | 结束后发出 `SetRegView lastused` |
| 环境变量修改后不广播 | 添加 `SendMessage ... WM_SETTINGCHANGE` |
| 远程文件缺少 `inetc.nsh` | 按需 `!include` |
| 安装大小估算缺失 | 写入 `EstimatedSize` 到注册表 |

### Schema 校验

- 安装 `jsonschema` 时使用 Draft7Validator 做完整校验
- 未安装时 fallback 到仅检查顶层必需键
- 由 `PackageConfig.from_yaml()` 自动调用

---

## CLI 子命令

```powershell
xswl-ypack convert <yaml> [-o output] [-f nsis|wix|inno] [--installer-name NAME] [--dry-run] [--build] [--makensis path] [-v]
xswl-ypack init [-o installer.yaml]
xswl-ypack validate <yaml> [-v]

- `convert`：完整转换流程（YAML → 安装脚本），`-f` 选择后端（默认 `nsis`）。`--installer-name` 可用于在构建时覆盖 `install.installer_name`（若两者都未设置则使用默认 `${APP_NAME}-${APP_VERSION}-Setup.exe`）。
```

- `convert`：完整转换流程（YAML → 安装脚本），`-f` 选择后端（默认 `nsis`）
- `init`：生成初始 YAML 模板
- `validate`：仅执行 schema 校验，不生成脚本
- 向后兼容：`xswl-ypack installer.yaml` 等价于 `xswl-ypack convert installer.yaml`

---

## 扩展点 ⚙️

- **新的转换后端**：
  1. 继承 `BaseConverter`，设置 `tool_name` 和 `output_extension`
  2. 实现 `convert()` / `save()`
  3. 在 `converters/__init__.py` 的 `CONVERTER_REGISTRY` 中注册
  4. 可选：在 `BUILD_COMMANDS` 中注册编译命令以支持 `--build`
  5. `BuildContext`、变量系统、配置解析全部可复用
- **自定义 NSIS 片段**：通过 `custom_includes.nsis` 注入 `!include`。
- **Package post_install**：在组件 Section 末尾以 `ExecWait` 执行任意命令。

---

## 测试

```bash
pytest tests/ -v
```

98 个测试覆盖：配置解析、变量解析、NSIS 输出、转换器注册表、CLI 子命令（含 `--format`）、Schema 校验、端到端集成。

---

## 使用示例

### CLI

```bash
xswl-ypack init
# 编辑 installer.yaml
xswl-ypack validate installer.yaml -v
xswl-ypack convert installer.yaml --build -v
xswl-ypack convert installer.yaml -f nsis -v
```

### Python API

```python
from ypack import PackageConfig, YamlToNsisConverter, get_converter_class

# 直接使用
cfg = PackageConfig.from_yaml("installer.yaml")
conv = YamlToNsisConverter(cfg, cfg._raw_dict)
conv.save("dist/installer.nsi")

# 或通过注册表动态选择后端
ConverterClass = get_converter_class("nsis")  # 或 "wix" / "inno"
conv = ConverterClass(cfg, cfg._raw_dict)
script = conv.convert()
```
