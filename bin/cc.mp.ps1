# Multi-Platform Claude Code Launcher - PowerShell Wrapper
# Calls the unified Python launcher

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
)

# 用户可以在这里修改项目路径，默认为脚本的父目录（项目根目录）
$ProjectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$Launcher = Join-Path $ProjectDir "bin" "launcher.py"

# Check if Python is available
try {
    $null = python --version 2>$null
} catch {
    Write-Host "❌ Python not found. Please install Python 3.7+ first." -ForegroundColor Red
    exit 1
}

# Check if launcher exists
if (-not (Test-Path $Launcher)) {
    Write-Host "❌ Launcher script not found: $Launcher" -ForegroundColor Red
    exit 1
}

# Pure config-file architecture - no environment variables needed

# Pass all arguments to the Python launcher
try {
    $ArgumentString = if ($Arguments) { $Arguments -join " " } else { "" }
    if ($ArgumentString) {
        python $Launcher $ArgumentString.Split()
    } else {
        python $Launcher
    }
    $ExitCode = $LASTEXITCODE
} finally {
    # Clean up environment variable
    Remove-Item Env:LAUNCHER_SCRIPT_DIR -ErrorAction SilentlyContinue
}
exit $ExitCode