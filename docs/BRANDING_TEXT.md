# BrandingText 支持

本项目现在支持 `branding` 配置选项，用于自定义 NSIS 安装程序窗口中显示的品牌文本。

## 使用方法

在 YAML 配置文件的 `app` 部分添加 `branding` 字段：

```yaml
app:
  name: "MyApp"
  version: "1.0.0"
  publisher: "My Company Inc."
  branding: "Powered by My Company Inc."
  description: "My awesome application"
```

## 默认行为

如果未指定 `branding`，系统将自动使用 `publisher` 字段作为默认值：

```yaml
app:
  name: "MyApp"
  version: "1.0.0"
  publisher: "My Company Inc."
  description: "My application"
  # 未指定 branding，将默认使用 "My Company Inc." 作为 BrandingText
```

## 转换到 NSIS

配置文件中的 `branding` 将被转换为 NSIS 脚本中的 `BrandingText` 指令：

```nsis
BrandingText "Powered by My Company Inc."
```

此文本将显示在 NSIS 安装程序窗口的底部。

## 支持特殊字符

`branding` 支持在 YAML 中使用变量引用和特殊字符：

```yaml
app:
  name: "MyApp"
  version: "1.0.0"
  publisher: "My Company"
  branding: "${app.publisher} - Version ${app.version}"
```

转换后将自动解析这些变量。
