<#
.SYNOPSIS
    精简多平台Claude启动器 - 支持别名调用
.DESCRIPTION
    支持简化别名调用：cc.mp.ps1 dp (启动DeepSeek)、cc.mp.ps1 kimi (启动Kimi)
    自动加载平台配置并设置环境变量
.PARAMETER Platform
    平台名称或别名：dp/ds(deepseek), kimi, gc(gaccode), sf(siliconflow), lp/local(local_proxy)
.EXAMPLE
    .\cc.mp.ps1 dp           # 启动DeepSeek
    .\cc.mp.ps1 kimi         # 启动Kimi
    .\cc.mp.ps1 gc           # 启动GAC Code
#>

param(
    [Parameter(Position = 0)]
    [string]$Platform = "",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$RemainingArgs
)

#region 初始化
Write-Host "🚀 Multi-Platform Claude Launcher v3.0" -ForegroundColor Magenta
Write-Host "======================================`n" -ForegroundColor Gray

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 配置文件优先级：脚本同目录 > 插件目录  
$ConfigFile = Join-Path $ScriptDir "launcher-config.json"
$SessionMappingFile = Join-Path $ScriptDir "session-mappings.json"

# 如果脚本同目录没有配置文件，尝试查找插件目录
if (-not (Test-Path $ConfigFile)) {
    $PossiblePluginPaths = @(
        (Join-Path $ScriptDir "..\data\config\launcher-config.json"),
        (Join-Path $env:USERPROFILE ".claude\scripts\gaccode.com\data\config\launcher-config.json"),
        "C:\Users\dray\.claude\scripts\gaccode.com\data\config\launcher-config.json"
    )
    
    foreach ($Path in $PossiblePluginPaths) {
        if (Test-Path $Path) {
            $ConfigFile = $Path
            $SessionMappingFile = (Split-Path $Path -Parent) -replace "config", "cache" + "\session-mappings.json"
            break
        }
    }
}

# 日志系统（如果可用）
$LoggerScript = (Join-Path (Split-Path $ScriptDir -Parent) "data\logger.py")

# 日志记录函数
function Write-Log {
    param([string]$Level, [string]$Message, [hashtable]$ExtraData = @{})
    
    if (Test-Path $LoggerScript) {
        try {
            $ExtraJson = if ($ExtraData.Count -gt 0) { ($ExtraData | ConvertTo-Json -Compress) } else { $null }
            if ($ExtraJson) {
                python $LoggerScript "launcher" $Level $Message $ExtraJson 2>$null
            } else {
                python $LoggerScript "launcher" $Level $Message 2>$null
            }
        } catch {
            # Fallback to console output
        }
    }
    
    # 同时输出到控制台（保持用户体验）
    $Color = switch ($Level) {
        "ERROR" { "Red" }
        "WARNING" { "Yellow" }
        "INFO" { "Cyan" }
        default { "White" }
    }
    Write-Host $Message -ForegroundColor $Color
}

if (-not (Test-Path $ConfigFile)) {
    Write-Host "❌ Configuration file not found: $ConfigFile" -ForegroundColor Red; exit 1
}
#endregion

#region 加载平台配置
Write-Log "INFO" "📋 Loading platform configuration..."

try {
    $Config = Get-Content $ConfigFile -Raw | ConvertFrom-Json
    $Platforms = $Config.platforms
    $Aliases = $Config.aliases
    
    # 解析平台别名
    $ResolvedPlatform = if ($Aliases.PSObject.Properties.Name -contains $Platform) { $Aliases.$Platform } else { $Platform }
    
    # 获取启用的平台
    $EnabledPlatforms = @{}
    foreach ($PlatformName in $Platforms.PSObject.Properties.Name) {
        $PlatformConfig = $Platforms.$PlatformName
        $IsEnabled = $PlatformConfig.enabled -eq $true
        $HasKey = ![string]::IsNullOrEmpty($PlatformConfig.api_key)
        
        if ($IsEnabled -and $HasKey) {
            $EnabledPlatforms[$PlatformName] = $PlatformConfig
        }
    }
    
    if ($ResolvedPlatform -and $EnabledPlatforms.ContainsKey($ResolvedPlatform)) {
        $SelectedPlatform = $ResolvedPlatform
    } elseif ($Platform) {
        Write-Host "❌ Platform '$Platform' (resolved: $ResolvedPlatform) not enabled or not found" -ForegroundColor Red
        Write-Host "Available platforms:" -ForegroundColor Yellow
        foreach ($PlatformName in $EnabledPlatforms.Keys) {
            $PlatformConfig = $EnabledPlatforms[$PlatformName]
            $AliasesList = @()
            foreach ($Alias in $Aliases.PSObject.Properties) {
                if ($Alias.Value -eq $PlatformName) { $AliasesList += $Alias.Name }
            }
            $AliasText = if ($AliasesList.Count -gt 0) { " (aliases: $($AliasesList -join ', '))" } else { "" }
            Write-Host "  - $PlatformName$AliasText`: $($PlatformConfig.name)" -ForegroundColor Gray
        }
        exit 1
    } else {
        if ($EnabledPlatforms.Count -gt 0) {
            # 优先使用配置中的默认平台
            $DefaultPlatform = $Config.settings.default_platform
            if ($DefaultPlatform -and $EnabledPlatforms.ContainsKey($DefaultPlatform)) {
                $SelectedPlatform = $DefaultPlatform
                Write-Host "No platform specified, using configured default: $SelectedPlatform" -ForegroundColor Yellow
            } else {
                # 默认平台不可用，选择第一个启用的平台
                $SelectedPlatform = $EnabledPlatforms.Keys | Select-Object -First 1
                Write-Host "No platform specified, default platform not available, using: $SelectedPlatform" -ForegroundColor Yellow
            }
        } else {
            Write-Host "❌ No platforms enabled. Please set API keys in $ConfigFile" -ForegroundColor Red
            exit 1
        }
    }
    
    $PlatformConfig = $EnabledPlatforms[$SelectedPlatform]
    Write-Host "✅ Selected Platform: $($PlatformConfig.name) ($SelectedPlatform)" -ForegroundColor Green
    Write-Host "   Enabled Platforms: $($EnabledPlatforms.Count)" -ForegroundColor Gray
    
    # 同步配置到插件目录
    $PluginRelativePath = $Config.settings.plugin_path
    if ([System.IO.Path]::IsPathRooted($PluginRelativePath)) {
        $PluginPath = $PluginRelativePath
    } else {
        $PluginPath = Join-Path $ScriptDir $PluginRelativePath
    }
    
    # 确保插件目录存在
    if (-not (Test-Path $PluginPath)) {
        # 如果相对路径不存在，尝试查找gaccode.com目录
        $ParentDir = Split-Path $ScriptDir -Parent
        $GacCodeDir = Join-Path $ParentDir "gaccode.com"
        if (Test-Path $GacCodeDir) {
            $PluginPath = $GacCodeDir
        } else {
            Write-Host "❌ Cannot find plugin directory. Please ensure the script is in the correct location." -ForegroundColor Red
            exit 1
        }
    }
    
    # 确保 data 子目录存在
    $DataConfigDir = Join-Path $PluginPath "config"
    $DataCacheDir = Join-Path $PluginPath "cache"
    
    if (-not (Test-Path $DataConfigDir)) {
        New-Item -ItemType Directory -Path $DataConfigDir -Force | Out-Null
    }
    if (-not (Test-Path $DataCacheDir)) {
        New-Item -ItemType Directory -Path $DataCacheDir -Force | Out-Null
    }
    
    $PluginConfigFile = Join-Path $DataConfigDir "platform-config.json"
    $PluginSessionFile = Join-Path $DataCacheDir "session-mappings.json"
    
    Write-Host "🔄 Syncing configuration to plugin directory..." -ForegroundColor Cyan
    
    # 创建插件配置文件
    $PluginConfig = @{
        platforms = $Config.platforms
        aliases = $Config.aliases
        settings = @{
            default_platform = $Config.settings.default_platform
            last_updated = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss.fffK')
        }
    }
    $PluginConfig | ConvertTo-Json -Depth 10 | Set-Content $PluginConfigFile -Encoding UTF8
    
    Write-Host "   ✅ Plugin configuration synced" -ForegroundColor Green
}
catch {
    Write-Host "❌ Failed to load configuration: $($_.Exception.Message)" -ForegroundColor Red; exit 1
}
#endregion

#region 设置环境变量
Write-Host "`n🔧 Setting up environment..." -ForegroundColor Cyan

# 清理环境变量
$variablesToClear = @(
    # Claude Code 核心环境变量
    "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "ANTHROPIC_API_URL",
    "ANTHROPIC_API_VERSION", "ANTHROPIC_CUSTOM_HEADERS", "ANTHROPIC_DEFAULT_HEADERS",
    "ANTHROPIC_MODEL", "ANTHROPIC_SMALL_FAST_MODEL", "ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION",
    "ANTHROPIC_TIMEOUT_MS", "ANTHROPIC_REQUEST_TIMEOUT", "ANTHROPIC_MAX_RETRIES",
    # 代理相关变量
    "HTTPS_PROXY", "HTTP_PROXY",
    # 其他AI平台环境变量
    "MOONSHOT_API_KEY", "DEEPSEEK_API_KEY", "SILICONFLOW_API_KEY",
    # 可能的其他相关变量
    "CLAUDE_API_KEY", "CLAUDE_AUTH_TOKEN", "CLAUDE_BASE_URL", "CLAUDE_MODEL"
)
foreach ($varName in $variablesToClear) {
    if (Test-Path "Env:$varName") {
        Write-Host "  -> Clearing: $varName" -ForegroundColor DarkGray
        # 双保险策略：先设为空，再移除，确保子进程无法继承
        [System.Environment]::SetEnvironmentVariable($varName, "", "Process")
        Remove-Item "Env:$varName" -ErrorAction SilentlyContinue
    }
}

# 设置新环境变量
$env:ANTHROPIC_API_KEY = $PlatformConfig.api_key
$env:ANTHROPIC_BASE_URL = $PlatformConfig.api_base_url
$env:ANTHROPIC_MODEL = $PlatformConfig.model
$env:ANTHROPIC_SMALL_FAST_MODEL = $PlatformConfig.small_model

# Git Bash 路径配置 (如果需要)
$GitBashPath = "C:\Users\dray\scoop\apps\git\current\bin\bash.exe"
if (Test-Path $GitBashPath) {
    $env:CLAUDE_CODE_GIT_BASH_PATH = $GitBashPath
    Write-Host "  -> CLAUDE_CODE_GIT_BASH_PATH set" -ForegroundColor Gray
}

Write-Host "✅ Environment configured" -ForegroundColor Green
#endregion

#region 生成UUID和注册配置
Write-Host "`n🔐 Registering session..." -ForegroundColor Cyan

$CustomSessionUUID = [System.Guid]::NewGuid().ToString()

# 注册session映射到本地文件
try {
    $SessionMapping = @{}
    if (Test-Path $SessionMappingFile) {
        $SessionMappingObj = Get-Content $SessionMappingFile -Raw | ConvertFrom-Json
        # Convert PSCustomObject to hashtable for compatibility
        $SessionMapping = @{}
        $SessionMappingObj.PSObject.Properties | ForEach-Object { $SessionMapping[$_.Name] = $_.Value }
    }
    
    $SessionMapping[$CustomSessionUUID] = @{
        platform = $SelectedPlatform
        created = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss.fffK')
    }
    
    # 保留最近50个session
    if ($SessionMapping.Count -gt 50) {
        $SortedSessions = $SessionMapping.GetEnumerator() | Sort-Object { [DateTime]$_.Value.created } -Descending | Select-Object -First 50
        $SessionMapping = @{}
        $SortedSessions | ForEach-Object { $SessionMapping[$_.Key] = $_.Value }
    }
    
    $SessionMapping | ConvertTo-Json -Depth 10 | Set-Content $SessionMappingFile -Encoding UTF8
    
    # 同步session映射到插件目录
    $SessionMapping | ConvertTo-Json -Depth 10 | Set-Content $PluginSessionFile -Encoding UTF8
    
    Write-Host "   ✅ Session registered" -ForegroundColor Green
    Write-Host "   UUID: $CustomSessionUUID" -ForegroundColor Green
    Write-Host "   Platform: $SelectedPlatform" -ForegroundColor Green
    Write-Host "   Model: $($PlatformConfig.model)" -ForegroundColor Green
}
catch {
    Write-Host "❌ Registration error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
#endregion

#region 启动Claude Code
Write-Host "`n🚀 Launching Claude Code..." -ForegroundColor Magenta

# 可执行文件配置（支持 npx 方式）
# 方式一: 全局安装 (npm install -g @anthropic-ai/claude-code)
$ClaudeExecutable = "claude"
$ClaudeArguments = ""

# 方式二: 通过 npx 运行 (如需要，取消注释下面两行)
# $ClaudeExecutable = "npx"
# $ClaudeArguments = "@anthropic-ai/claude-code"

# 准备参数列表
$argumentsToPass = [System.Collections.ArrayList]::new()
if (-not [string]::IsNullOrEmpty($ClaudeArguments)) {
    [void]$argumentsToPass.Add($ClaudeArguments)
}
[void]$argumentsToPass.Add("--session-id=$CustomSessionUUID")
if ($RemainingArgs) { $argumentsToPass.AddRange($RemainingArgs) }

Write-Host "🎯 Configuration Summary:" -ForegroundColor Yellow
Write-Host "   Platform: $($PlatformConfig.name)" -ForegroundColor White
Write-Host "   Session: $CustomSessionUUID" -ForegroundColor Gray
Write-Host "   Model: $($PlatformConfig.model)" -ForegroundColor Gray

$commandString = "$ClaudeExecutable $($argumentsToPass -join ' ')"
Write-Host "`n💻 Executing: $commandString" -ForegroundColor Green
Write-Host "=" * 60 -ForegroundColor Gray

if (-not (Get-Command $ClaudeExecutable -ErrorAction SilentlyContinue)) {
    Write-Host "❌ $ClaudeExecutable command not found. Please install Claude Code first." -ForegroundColor Red
    exit 1
}

try {
    Invoke-Expression -Command $commandString
    $claudeExitCode = $LASTEXITCODE
}
catch {
    Write-Host "`n❌ Execution failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
#endregion

#region 清理
Write-Host "`n" + "=" * 60 -ForegroundColor Gray
if ($claudeExitCode -eq 0) {
    Write-Host "🎉 Session completed successfully!" -ForegroundColor Green
} else {
    Write-Host "❌ Claude Code exited with error code: $claudeExitCode" -ForegroundColor Red
}
Write-Host "   Platform: $($PlatformConfig.name)" -ForegroundColor White  
Write-Host "   UUID: $CustomSessionUUID" -ForegroundColor Gray

exit $claudeExitCode
#endregion