# Web UI 可视化编辑器设计方案

## 概述

构建一个基于 Web 的可视化编辑器，用于通过拖拽和表单编辑的方式生成 YAML 安装包配置文件。
用户可以选择不同的安装包生成工具（NSIS、WiX、Inno 等），当前只实现了 NSIS 转换器。

## 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                   Web UI (前端)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ 属性编辑面板  │  │  可视化视图   │  │  预览面板     │  │
│  │ (表单 + 列表) │  │  (树形/代码)  │  │ (YAML/脚本)  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                         ↕ HTTP API
┌─────────────────────────────────────────────────────────┐
│              Python Backend (Flask/FastAPI)             │
│  ┌─────────────────────────────────────────────────┐   │
│  │  ypack/web/                                     │   │
│  │    ├─ server.py        (主服务)                 │   │
│  │    ├─ api/                                       │   │
│  │    │   ├─ schema.py    (获取 JSON Schema)       │   │
│  │    │   ├─ validate.py  (YAML 校验)              │   │
│  │    │   ├─ convert.py   (YAML → 安装器脚本)      │   │
│  │    │   └─ project.py   (项目加载/保存)          │   │
│  │    └─ static/          (前端静态文件)            │   │
│  └─────────────────────────────────────────────────┘   │
│                         ↓                                │
│  ┌──────────────────────────────────────────────────┐  │
│  │  现有模块复用                                     │  │
│  │    ypack/schema.py    (Schema 校验)              │  │
│  │    ypack/config.py    (YAML → PackageConfig)    │  │
│  │    ypack/converters/  (PackageConfig → 脚本)    │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                         ↓
                    config.yaml
                         ↓
                  [NSIS | WiX | Inno]
```

## 数据结构映射（基于 config.py）

### PackageConfig 各部分对应的 UI 组件

| config.py 字段 | UI 组件类型 | 说明 |
|----------------|-------------|------|
| `app: AppInfo` | 表单 | 基本信息输入：name, version, publisher, icon等 |
| `install: InstallConfig` | 多子表单 | 包含快捷方式、注册表、环境变量等配置 |
| `files: List[FileEntry]` | 列表编辑器 | 简单文件/目录列表，支持添加/删除/编辑 |
| `packages: List[PackageEntry]` | 树形编辑器 | 支持嵌套子组件(children)，拖拽调整层级 |
| `signing: SigningConfig` | 表单 | 代码签名配置（可折叠） |
| `update: UpdateConfig` | 表单 | 自动更新配置（可折叠） |
| `logging: LoggingConfig` | 表单 | 日志配置（可折叠） |
| `languages: List[str]` | 多选框 | 语言选择 |
| `custom_includes` | 键值对编辑器 | 自定义包含文件 |

### 复杂子结构的 UI 设计

#### PackageEntry（组件树）
```javascript
// 树形节点数据结构
{
  id: "uuid",
  name: "Core",
  type: "package",
  data: {
    sources: [{source: "bin/*", destination: "$INSTDIR"}],
    recursive: true,
    optional: false,
    default: true,
    description: "Core Functionality",
    post_install: []
  },
  children: [
    { id: "uuid2", name: "Tools", type: "package", data: {...}, children: [] }
  ]
}
```

**UI 功能**：
- 拖拽调整层级和顺序
- 右键菜单：添加子组件、删除、编辑属性
- 可视化标识：optional（可选）、default（默认勾选）
- 双击节点打开属性编辑器

#### InstallConfig（复合配置）

**子表单分组**：
```
基本设置
  ├─ 安装目录（文本框 + 变量选择器）
  ├─ 注册表键（文本框）
  └─ 注册表视图（下拉：auto/32/64）

快捷方式
  ├─ 桌面快捷方式 (ShortcutConfig)
  │   ├─ 名称
  │   └─ 目标
  └─ 开始菜单快捷方式 (ShortcutConfig)

注册表项 (List<RegistryEntry>)
  [+ 添加注册表项]
  ├─ 项1: HKLM\Software\...\InstallPath
  └─ 项2: ...

环境变量 (List<EnvVarEntry>)
  [+ 添加环境变量]
  ├─ MYAPP_HOME = $INSTDIR
  └─ PATH += $INSTDIR\bin (追加)

文件关联 (List<FileAssociation>)
  [+ 添加文件关联]
  └─ .my → MyApp

系统要求 (SystemRequirements)
  ├─ 最低 Windows 版本
  ├─ 最小磁盘空间 (MB)
  ├─ 最小内存 (MB)
  └─ ☑ 需要管理员权限

现有安装策略 (ExistingInstallConfig)
  ├─ 处理模式：[prompt_uninstall ▼]
  ├─ ☐ 版本检查
  ├─ ☐ 允许多个版本
  └─ 卸载等待时间 (ms)
```

## API 接口设计

### 1. Schema 相关

```http
GET /api/schema
返回：JSON Schema（基于 ypack/schema.py）
用途：前端表单验证、自动补全
```

```http
GET /api/schema/enums
返回：所有枚举值（如 registry_view: auto/32/64）
用途：下拉框选项
```

### 2. 项目管理

```http
POST /api/project/new
Body: { name: "MyInstaller" }
返回：空白 PackageConfig JSON
```

```http
POST /api/project/load
Body: { yaml_content: "..." }
返回：PackageConfig JSON + 验证结果
```

```http
POST /api/project/save
Body: { config: {...} }
返回：格式化的 YAML 字符串
```

### 3. 验证相关

```http
POST /api/validate/yaml
Body: { yaml_content: "..." }
返回：{ valid: true/false, errors: [...] }
用途：实时 YAML 语法检查
```

```http
POST /api/validate/config
Body: { config: {...} }
返回：{ valid: true/false, errors: [...] }
用途：验证完整配置结构
```

### 4. 转换器相关

```http
GET /api/converters
返回：可用转换器列表
{
  converters: [
    { id: "nsis", name: "NSIS", supported: true },
    { id: "wix", name: "WiX Toolset", supported: false },
    { id: "inno", name: "Inno Setup", supported: false }
  ]
}
```

```http
POST /api/convert/preview
Body: { 
  config: {...},
  converter: "nsis"
}
返回：生成的安装脚本内容（字符串）
用途：预览生成的 .nsi 脚本
```

```http
POST /api/convert/build
Body: { 
  yaml_content: "...",
  converter: "nsis",
  output_path: "installer.nsi"
}
返回：{ success: true, output: "path/to/installer.nsi" }
用途：完整转换流程
```

### 5. 辅助功能

```http
GET /api/variables/builtin
返回：内置变量列表（$INSTDIR, $PROGRAMFILES64等）
用途：变量选择器
```

```http
POST /api/files/scan
Body: { directory: "C:/MyApp" }
返回：文件树结构
用途：文件选择器
```

## 前端技术栈建议

### 核心库选择

**选项 1：Vue 3 + Element Plus**
```
优点：
- 轻量级，适合单页应用
- Element Plus 组件丰富（Tree、Form、Upload等）
- Vue 响应式系统适合复杂表单
- 国内使用广泛，中文文档友好
```

**选项 2：React + Ant Design**
```
优点：
- React Flow 集成方便（如需流程图视图）
- Ant Design 企业级组件
- TypeScript 支持更好
```

### 必需组件

1. **代码编辑器**：Monaco Editor
   - VS Code 同款
   - YAML 语法高亮
   - 错误提示集成

2. **树形编辑器**：vue-tree / rc-tree
   - 拖拽排序
   - 嵌套层级
   - 自定义节点渲染

3. **表单生成器**：基于 JSON Schema
   - vue-json-schema-form
   - react-jsonschema-form

4. **YAML 处理**：js-yaml
   - YAML ↔ JSON 转换
   - 语法验证

## 实现计划

### Phase 1：基础框架（MVP）

**后端**
- [x] 现有 schema.py 和 config.py
- [ ] Flask 基础服务器
- [ ] GET /api/schema
- [ ] POST /api/validate/yaml
- [ ] POST /api/project/load
- [ ] POST /api/project/save

**前端**
- [ ] 基础页面布局（三栏）
- [ ] App 信息表单
- [ ] 简单 Files 列表编辑
- [ ] Monaco YAML 编辑器
- [ ] 双向同步（表单 ↔ YAML）

### Phase 2：完整编辑功能

**后端**
- [ ] POST /api/convert/preview
- [ ] GET /api/converters
- [ ] GET /api/variables/builtin

**前端**
- [ ] InstallConfig 全部子表单
- [ ] Packages 树形编辑器
- [ ] 注册表/环境变量/文件关联列表
- [ ] 实时验证提示
- [ ] NSIS 脚本预览

### Phase 3：高级功能

- [ ] 文件上传（拖拽添加文件）
- [ ] 模板系统（预设配置）
- [ ] 多项目管理（.ypack 工作区）
- [ ] 版本历史（Git 集成）
- [ ] WiX / Inno Setup 转换器支持

## 目录结构

```
ypack/
  web/
    __init__.py
    server.py              # Flask/FastAPI 主服务
    api/
      __init__.py
      schema.py           # Schema 相关接口
      validate.py         # 验证接口
      convert.py          # 转换接口
      project.py          # 项目管理接口
      variables.py        # 变量辅助接口
    static/               # 前端构建输出
      index.html
      assets/
        js/
        css/
    frontend/             # 前端源码（开发时）
      src/
        components/
          AppInfoForm.vue
          InstallConfigForm.vue
          PackageTree.vue
          YamlEditor.vue
          ...
        views/
          Editor.vue
        App.vue
        main.js
      package.json
      vite.config.js
```

## 关键实现细节

### 1. YAML ↔ JSON 双向绑定

```python
# 后端
@app.post("/api/project/load")
def load_project(yaml_content: str):
    config = PackageConfig.from_yaml(yaml_content)
    # 转换为 JSON（前端可用）
    return config_to_dict(config)

@app.post("/api/project/save")
def save_project(config_dict: dict):
    # 转换为 YAML
    import yaml
    return yaml.dump(config_dict, allow_unicode=True)
```

```javascript
// 前端
const editorState = reactive({
  config: {}, // JSON 对象
  yaml: ""    // YAML 字符串
});

// 表单 → YAML
watch(() => editorState.config, (newConfig) => {
  axios.post('/api/project/save', { config: newConfig })
    .then(res => editorState.yaml = res.data);
}, { deep: true });

// YAML → 表单
watch(() => editorState.yaml, (newYaml) => {
  axios.post('/api/project/load', { yaml_content: newYaml })
    .then(res => editorState.config = res.data);
});
```

### 2. PackageEntry 树形编辑

```vue
<template>
  <el-tree
    :data="packagesTree"
    node-key="id"
    draggable
    :allow-drop="allowDrop"
    @node-drop="handleDrop"
  >
    <template #default="{ node, data }">
      <span class="package-node">
        <span>{{ data.name }}</span>
        <el-tag v-if="data.data.optional" size="small">可选</el-tag>
        <el-tag v-if="!data.data.default" type="info" size="small">默认不选</el-tag>
      </span>
    </template>
  </el-tree>
</template>

<script setup>
const packagesTree = ref([]);

// 从 config.packages 构建树
function buildTree(packages) {
  return packages.map(pkg => ({
    id: generateId(),
    name: pkg.name,
    type: 'package',
    data: pkg,
    children: pkg.children ? buildTree(pkg.children) : []
  }));
}

// 拖拽后更新配置
function handleDrop(dragNode, dropNode, dropType) {
  // 重建 config.packages
  rebuildPackagesConfig();
}
</script>
```

### 3. 实时验证提示

```javascript
// Monaco Editor 错误标记
async function validateYaml(yamlContent) {
  const res = await axios.post('/api/validate/yaml', { 
    yaml_content: yamlContent 
  });
  
  if (!res.data.valid) {
    const markers = res.data.errors.map(err => ({
      severity: monaco.MarkerSeverity.Error,
      startLineNumber: err.line,
      startColumn: err.column,
      endLineNumber: err.line,
      endColumn: err.column + err.length,
      message: err.message
    }));
    monaco.editor.setModelMarkers(editor.getModel(), 'yaml', markers);
  }
}
```

## 用户工作流程

1. **新建项目**
   - 填写 App 基本信息
   - 配置安装目录、快捷方式等
   
2. **添加文件和组件**
   - 在 Files 中添加简单文件
   - 在 Packages 树中构建组件层级
   - 为组件配置 sources、post_install 等

3. **高级配置**
   - 添加注册表项、环境变量
   - 配置文件关联
   - 设置签名、更新等

4. **预览和导出**
   - 实时查看 YAML 代码
   - 选择转换器（NSIS/WiX/Inno）
   - 预览生成的安装脚本
   - 导出 YAML 或直接构建安装包

5. **加载现有项目**
   - 打开已有 .yaml 文件
   - 在可视化界面中编辑
   - 保存回 YAML

## 兼容性考虑

### 跨转换器设计

配置应该保持转换器中立：
```yaml
# ✅ 好的设计（跨工具）
install:
  install_dir: "$PROGRAMFILES64/${app.name}"  # 使用内置变量
  
# ❌ 避免（NSIS 特定）
install:
  install_dir: "$PROGRAMFILES64\\${APP_NAME}"  # NSIS 宏
```

UI 应该：
- 使用 config.py 定义的抽象数据结构
- 变量选择器提供跨工具的内置变量
- 转换器特定功能放在 `custom_includes` 中

### 未来扩展性

**添加新转换器时只需**：
1. 实现 `ypack/converters/convert_wix.py`
2. 在 `/api/converters` 中注册
3. UI 无需修改（选择器自动更新）

## 下一步

我可以帮你：
1. **立即开始搭建** Phase 1 MVP（基础后端 + 简单前端）
2. **先写详细的 API 文档** 让你审核接口设计
3. **先实现某个特定模块** 作为技术验证

你希望从哪个开始？
