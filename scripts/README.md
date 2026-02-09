# 脚本说明与使用指南 🔧

本目录下的脚本用于在 Windows 上采集、搜索和比对系统与驱动安装状态，便于验证安装包（例如会自动安装驱动的安装器）是否真的安装了驱动。

> 注意：所有脚本在大多数操作下需要以管理员权限运行以获得完整信息（右键 PowerShell → Run as Administrator）。

---

## 可用脚本

- `driver-check.ps1`  — 生成当前驱动快照（JSON + CSV）。
  - 作用：抓取当前系统的 PnP 设备信息、已签名驱动（Win32_PnPSignedDriver）、系统驱动（Win32_SystemDriver）、`pnputil` 输出，并可选读取 `setupapi.dev.log` 的尾部，用于安装前后快照比较与后续搜索。
  - 参数：
    - `-OutFile <string>`（可选，默认 `drivers_snapshot.json`）：输出 JSON 快照文件名。
    - `-IncludeSetupApiLog`（switch，可选）：同时读取 `%windir%\inf\setupapi.dev.log` 的尾部并包含在快照中。
    - `-SetupApiTail <int>`（可选，默认 `200`）：读取 `setupapi.dev.log` 的尾部行数（仅当 `-IncludeSetupApiLog` 指定时生效）。
  - 注意：请以管理员权限运行以获得完整信息（右键 PowerShell → Run as Administrator）。
  - 输出：JSON 快照文件（结构：PnpDevices、PnPSignedDrivers、SystemDrivers、DriverStoreRaw、SetupapiLogTail）和一个汇总 CSV（同名但扩展名为 `.drivers.csv`）。
  - 用法示例：
    - `.\\scripts\\driver-check.ps1 -OutFile before.json -IncludeSetupApiLog -SetupApiTail 500`

- `driver-diff.ps1`  — 对比两个由 `driver-check.ps1` 生成的快照，输出新增/移除的 PnP 已签名驱动（按 InfName + DeviceName 区分）与系统驱动（按服务名区分）。
  - 作用：自动识别安装后新增或被移除的驱动与内核服务，方便判断安装器是否安装了新驱动。
  - 参数：
    - `-Old <string>`（必需）：旧的快照文件名（例如安装前的 `before.json`）。
    - `-New <string>`（必需）：新的快照文件名（例如安装后的 `after.json`）。
    - `-SaveOutput`（switch，可选）：将差异结果保存为 `driver-diff-<timestamp>.json`。
  - 输出：命令行差异报告，并在 `-SaveOutput` 指定时生成 JSON 报告文件。
  - 用法示例：
    - `.\scripts\driver-diff.ps1 -Old before.json -New after.json -SaveOutput`

- `search-setupapi.ps1`  — 在 `setupapi.dev.log`（以及 `%TEMP%` 的常见安装/临时日志）中根据关键字搜索安装记录。
  - 参数：
    - `-Pattern <string>`（必需）：要搜索的关键字或字符串（可使用正则表达式配合 `-Regex`）。
    - `-Lines <int>`（可选，默认 `200`）：读取 `setupapi.dev.log` 的尾部行数进行搜索。
  - 作用：帮助在安装日志中确认是否有 INF 文件的安装记录、复制 `.sys` 文件或驱动安装失败的详细错误信息。
  - 用法示例：
    - `.\scripts\search-setupapi.ps1 -Pattern "oem" -Lines 300`

- `find-driver.ps1`  — 根据关键字或正则在实时系统或快照中查找驱动/设备/Driver Store 条目，支持类型过滤（`pnp|signed|system|store|setupapi|all`）。
  - 作用：快速定位特定厂商/INF/设备名称的驱动，支持模糊或正则匹配，可在安装前后对比使用。
  - 参数：
    - `-Pattern <string>`（必需）：搜索关键字或正则表达式。
    - `-Regex`（switch，可选）：将 `-Pattern` 当作正则表达式处理。
    - `-CaseSensitive`（switch，可选）：启用区分大小写匹配。
    - `-Type <pnp|signed|system|store|setupapi|all>`（可选，默认 `all`）：选择要搜索的目标类型。
    - `-Snapshot <string>`（可选）：指定由 `driver-check.ps1` 生成的 JSON 快照文件以在快照中搜索（否则从实时系统查询）。
    - `-SetupApiTail <int>`（可选，默认 `200`）：当 `-Type setupapi` 时用于读取 `setupapi.dev.log` 的尾部行数。
    - `-Detailed`（switch，可选）：显示完整属性而不是摘要表格。
  - 用法示例：
    - `.\scripts\find-driver.ps1 -Pattern 'siglent' -Type all`
    - `.\scripts\find-driver.ps1 -Pattern '^oem\\d+\\.inf$' -Regex -Type store`
    - `.\scripts\find-driver.ps1 -Pattern 'mydriver' -Snapshot before.json -Type signed -Detailed`

---

## 常见工作流程（示例） ✅

1. 以管理员权限打开 PowerShell。  
2. 运行 `driver-check.ps1` 做安装前快照：
   - `.
otescripts\driver-check.ps1 -OutFile before.json -IncludeSetupApiLog`
3. 运行或触发安装包（安装过程）。
4. 运行 `driver-check.ps1` 做安装后快照：
   - `.
otescripts\driver-check.ps1 -OutFile after.json -IncludeSetupApiLog`
5. 运行 `driver-diff.ps1` 查看差异：
   - `.
otescripts\driver-diff.ps1 -Old before.json -New after.json -SaveOutput`
6. 如需进一步确认，使用 `find-driver.ps1` 或 `search-setupapi.ps1` 搜索具体 `INF`、`.sys` 名称或厂商关键字。

---

## 编码与本地化注意事项 ⚠️

- 脚本默认使用 UTF-8 编码并包含 ASCII 文案，避免旧版 PowerShell 在非 UTF-8 环境下解析错误。若你希望恢复中文提示，我可以把文件转换为带 BOM 的 UTF-8 或系统 ANSI（GBK）编码并替换回中文文本。

---

## 故障排查小贴士 🛠️

- 如果运行时报解析（parser）错误，优先检查脚本文件是否以正确编码保存（推荐 UTF-8 with BOM 或 UTF-8）。
- 如 `pnputil` 命令不可用，确认 Windows 版本和权限，或在管理员 PowerShell 中执行。
- `setupapi.dev.log` 文件可能非常大；脚本默认只取尾部（`-Tail`）以加快搜索。

---

## 扩展建议（如需我实现）

- 导出结果为 CSV/JSON（便于自动化或上传到远程服务器）。 ✅
- 添加 `-Watch` 模式：在安装过程中持续监控并在检测到新增驱动时自动报告或写入日志。 ✅
- 将脚本转成可交互的单文件安装验证工具（自动前/后快照、运行安装器、对比并生成报告）。 ✅

需要我把哪一项扩展到脚本中？（例如：`-Watch` 自动监控或 JSON 输出）
