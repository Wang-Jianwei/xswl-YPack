# Web UI 启动脚本
# 用于快速启动 YPack Web UI 服务器

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "  YPack Web UI Server Launcher" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

# 检查 Python
Write-Host "[1/3] 检查 Python 环境..." -ForegroundColor Yellow
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "错误: 未找到 Python!" -ForegroundColor Red
    Write-Host "请先安装 Python 3.8 或更高版本" -ForegroundColor Red
    exit 1
}

$pythonVersion = python --version
Write-Host "✓ 找到 $pythonVersion" -ForegroundColor Green
Write-Host ""

# 检查依赖
Write-Host "[2/3] 检查依赖..." -ForegroundColor Yellow
$missingDeps = @()

foreach ($dep in @("flask", "flask_cors", "jsonschema")) {
    python -c "import $dep" 2>$null
    if ($LASTEXITCODE -ne 0) {
        $missingDeps += $dep
    }
}

if ($missingDeps.Count -gt 0) {
    Write-Host "检测到缺失的依赖: $($missingDeps -join ', ')" -ForegroundColor Red
    Write-Host ""
    Write-Host "正在安装依赖..." -ForegroundColor Yellow
    pip install flask flask-cors jsonschema
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "依赖安装失败!" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✓ 所有依赖已安装" -ForegroundColor Green
}
Write-Host ""

# 启动服务器
Write-Host "[3/3] 启动 Web 服务器..." -ForegroundColor Yellow
Write-Host ""

# 解析命令行参数
$host_addr = "127.0.0.1"
$port = 5000
$debug = $false

for ($i = 0; $i -lt $args.Count; $i++) {
    switch ($args[$i]) {
        "--host" { $host_addr = $args[$i+1]; $i++ }
        "--port" { $port = $args[$i+1]; $i++ }
        "--debug" { $debug = $true }
    }
}

# 构建命令
$cmd = "python -m ypack.web.server --host $host_addr --port $port"
if ($debug) {
    $cmd += " --debug"
}

Write-Host "命令: $cmd" -ForegroundColor Cyan
Write-Host ""

# 运行
Invoke-Expression $cmd
