# YPack Web UI - 可视化安装包配置编辑器

## 概述

YPack Web UI 是一个基于 Web 的可视化编辑器，用于创建和编辑 YAML 格式的安装包配置文件。

## 功能特性

✅ **Phase 1 (当前版本)**
- 📝 应用信息表单编辑
- 📁 文件列表管理
- 💻 Monaco Editor YAML 代码编辑
- 🔄 双向同步（表单 ↔ YAML）
- ✅ 实时 YAML 验证
- 💾 项目加载/保存

🚧 **计划中**
- 🌲 Packages 树形编辑器（拖拽组件层级）
- ⚙️ 完整 InstallConfig 表单（注册表、环境变量、文件关联等）
- 🔍 NSIS/WiX/Inno 脚本预览
- 📦 更多...

## 快速开始

### 1. 安装依赖

```bash
# 安装 Web UI 依赖
pip install -e ".[web]"

# 或者分别安装
pip install flask flask-cors jsonschema
```

### 2. 启动服务器

**方法 1：使用命令行工具**
```bash
xswl-ypack-web
```

**方法 2：使用 Python 模块**
```bash
python -m ypack_web.server
```

**方法 3：自定义参数**
```bash
# 指定端口和主机
xswl-ypack-web --host 0.0.0.0 --port 8080 --debug

# 查看帮助
xswl-ypack-web --help
```

### 3. 打开浏览器

访问 http://127.0.0.1:5000

## 使用指南

### 基本工作流程

1. **创建新项目**
   - 点击"新建"按钮
   - 输入项目名称
   - 在左侧表单中填写应用信息

2. **添加文件**
   - 在"文件列表"区域点击"添加文件"
   - 输入源路径和目标路径
   - 配置是否递归复制

3. **编辑 YAML**
   - 在中间的 Monaco 编辑器中直接编辑 YAML
   - 修改会自动同步到左侧表单
   - 实时语法高亮和错误提示

4. **验证配置**
   - 在右侧预览面板点击"验证配置"
   - 查看验证结果和错误信息

5. **保存项目**
   - 点击"保存 YAML"下载配置文件
   - 或者直接复制右侧预览的 YAML 内容

### 加载现有项目

1. 点击"打开"按钮
2. 选择本地的 `.yaml` 或 `.yml` 文件
3. 配置会自动加载到编辑器中

## API 接口

Web UI 提供了 RESTful API，可用于集成或自动化：

### Schema 相关
- `GET /api/schema` - 获取 JSON Schema
- `GET /api/schema/enums` - 获取枚举值

### 验证相关
- `POST /api/validate/yaml` - 验证 YAML 内容
- `POST /api/validate/config` - 验证配置字典

### 项目管理
- `POST /api/project/new` - 创建新项目
- `POST /api/project/load` - 从 YAML 加载
- `POST /api/project/save` - 保存为 YAML

### 辅助功能
- `GET /api/variables/builtin` - 获取内置变量
- `GET /api/health` - 健康检查

详细 API 文档请参考 [docs/WEB_UI_DESIGN.md](WEB_UI_DESIGN.md)

## UI 布局

```
┌─────────────────────────────────────────────────────────┐
│  📦 YPack - Visual Installer Builder                    │
│                                    [新建] [打开] [保存]  │
├──────────────┬─────────────────────┬────────────────────┤
│              │                     │                    │
│  左侧面板     │   中间编辑器         │   右侧预览         │
│  (表单编辑)   │   (YAML 代码)       │   (验证/预览)      │
│              │                     │                    │
│ • 应用信息    │  Monaco Editor      │ • YAML 预览        │
│ • 安装设置    │  - 语法高亮         │ • 验证按钮         │
│ • 文件列表    │  - 自动补全         │ • 状态显示         │
│              │  - 错误提示         │                    │
│              │                     │                    │
├──────────────┴─────────────────────┴────────────────────┤
│  ⚫ 配置有效 ✓                                          │
└─────────────────────────────────────────────────────────┘
```

## 技术栈

### 后端
- **Flask** - Web 框架
- **Flask-CORS** - 跨域支持
- **PyYAML** - YAML 解析
- **jsonschema** - Schema 验证

### 前端
- **Vue 3** - 前端框架
- **Element Plus** - UI 组件库
- **Monaco Editor** - 代码编辑器
- **js-yaml** - YAML 处理

## 开发模式

启用调试模式查看详细日志：

```bash
xswl-ypack-web --debug
```

调试模式特性：
- 自动重载代码变更
- 详细错误堆栈
- CORS 允许所有来源

## 故障排查

### 端口被占用

```bash
# 使用其他端口
xswl-ypack-web --port 8080
```

### CORS 错误

如果前端与后端不在同一域名，确保启用了 CORS（默认已启用）。

### 依赖缺失

```bash
# 重新安装依赖
pip install -e ".[web]" --force-reinstall
```

## 目录结构

```
ypack_web/
├── __init__.py           # 包初始化
├── server.py             # Flask 主服务
├── api/                  # API 端点
│   ├── __init__.py
│   ├── schema.py         # Schema 接口
│   ├── validate.py       # 验证接口
│   ├── project.py        # 项目管理
│   └── variables.py      # 变量辅助
└── static/               # 前端静态文件
    └── index.html        # 单页应用
```

## 下一步开发

参考 [WEB_UI_DESIGN.md](WEB_UI_DESIGN.md) 了解完整的设计方案和后续开发计划。

**Phase 2 计划**：
- Packages 树形编辑器
- 注册表/环境变量/文件关联编辑
- NSIS 脚本预览
- 转换器选择

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License
