#!/bin/bash
# Multi-Platform Claude Launcher - Linux/Mac版本（本地配置）
# 用法: ./cc.mp.sh dp (启动DeepSeek), ./cc.mp.sh kimi (启动Kimi)

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# Configuration
PLATFORM="$1"
shift || true  # Remove first argument (platform)
REMAINING_ARGS=("$@")

# Get script directory and configuration files
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CONFIG_FILE="$SCRIPT_DIR/launcher-config.json"
SESSION_MAPPING_FILE="$SCRIPT_DIR/session-mappings.json"

echo -e "${MAGENTA}🚀 Multi-Platform Claude Launcher v3.0${NC}"
echo -e "${GRAY}======================================${NC}\n"

# Check dependencies
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python not found${NC}"
    exit 1
fi

PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo -e "${RED}❌ Configuration file not found: $CONFIG_FILE${NC}"
    exit 1
fi

# Load platform configuration
echo -e "${CYAN}📋 Loading platform configuration...${NC}"

CONFIG_SCRIPT="
import json
import sys
from datetime import datetime

# Load configuration
with open('$CONFIG_FILE', 'r', encoding='utf-8') as f:
    config = json.load(f)

platforms = config['platforms']
aliases = config.get('aliases', {})
specified_platform = '$PLATFORM'

# Resolve platform alias
resolved_platform = aliases.get(specified_platform, specified_platform)

# Get enabled platforms
enabled_platforms = {}
for platform, platform_config in platforms.items():
    if platform_config.get('enabled') and platform_config.get('api_key'):
        enabled_platforms[platform] = platform_config

if resolved_platform and resolved_platform in enabled_platforms:
    selected_platform = resolved_platform
elif specified_platform:
    print(f'ERROR: Platform \"{specified_platform}\" (resolved: {resolved_platform}) not enabled or not found')
    print('Available platforms:')
    for platform, platform_config in enabled_platforms.items():
        aliases_list = [k for k, v in aliases.items() if v == platform]
        alias_text = f' (aliases: {\", \".join(aliases_list)})' if aliases_list else ''
        print(f'  - {platform}{alias_text}: {platform_config[\"name\"]}')
    sys.exit(1)
else:
    if enabled_platforms:
        # 优先使用配置中的默认平台
        default_platform = config['settings'].get('default_platform')
        if default_platform and default_platform in enabled_platforms:
            selected_platform = default_platform
            print(f'No platform specified, using configured default: {selected_platform}')
        else:
            # 默认平台不可用，选择第一个启用的平台
            selected_platform = list(enabled_platforms.keys())[0]
            print(f'No platform specified, default platform not available, using: {selected_platform}')
    else:
        print('ERROR: No platforms enabled. Please set API keys in launcher-config.json')
        sys.exit(1)

# Sync configuration to plugin directory
plugin_path = config['settings']['plugin_path']
plugin_config_file = f'{plugin_path}/platform-config.json'
plugin_session_file = f'{plugin_path}/session-mappings.json'

print('🔄 Syncing configuration to plugin directory...')

# Create plugin configuration
plugin_config = {
    'platforms': platforms,
    'aliases': aliases,
    'settings': {
        'default_platform': config['settings']['default_platform'],
        'last_updated': datetime.now().isoformat()
    }
}

with open(plugin_config_file, 'w', encoding='utf-8') as f:
    json.dump(plugin_config, f, indent=2, ensure_ascii=False)

platform_config = enabled_platforms[selected_platform]
result = {
    'platform': selected_platform,
    'config': platform_config,
    'enabled_count': len(enabled_platforms),
    'plugin_session_file': plugin_session_file
}
print(json.dumps(result))
"

CONFIG_RESULT=$($PYTHON_CMD -c "$CONFIG_SCRIPT" 2>&1)
CONFIG_EXIT_CODE=$?

if [[ $CONFIG_EXIT_CODE -ne 0 ]]; then
    echo -e "${RED}❌ $CONFIG_RESULT${NC}"
    exit 1
fi

# Parse JSON result
if command -v jq &> /dev/null; then
    SELECTED_PLATFORM=$(echo "$CONFIG_RESULT" | jq -r '.platform')
    PLATFORM_NAME=$(echo "$CONFIG_RESULT" | jq -r '.config.name')
    API_KEY=$(echo "$CONFIG_RESULT" | jq -r '.config.api_key')
    API_BASE_URL=$(echo "$CONFIG_RESULT" | jq -r '.config.api_base_url')
    MODEL=$(echo "$CONFIG_RESULT" | jq -r '.config.model')
    SMALL_MODEL=$(echo "$CONFIG_RESULT" | jq -r '.config.small_model')
    ENABLED_COUNT=$(echo "$CONFIG_RESULT" | jq -r '.enabled_count')
    PLUGIN_SESSION_FILE=$(echo "$CONFIG_RESULT" | jq -r '.plugin_session_file')
else
    # Fallback to python JSON parsing
    PARSE_SCRIPT="
import json
data = json.loads('''$CONFIG_RESULT''')
print(f'SELECTED_PLATFORM={data[\"platform\"]}')
print(f'PLATFORM_NAME={data[\"config\"][\"name\"]}')
print(f'API_KEY={data[\"config\"][\"api_key\"]}')
print(f'API_BASE_URL={data[\"config\"][\"api_base_url\"]}')
print(f'MODEL={data[\"config\"][\"model\"]}')
print(f'SMALL_MODEL={data[\"config\"][\"small_model\"]}')
print(f'ENABLED_COUNT={data[\"enabled_count\"]}')
print(f'PLUGIN_SESSION_FILE={data[\"plugin_session_file\"]}')"
    eval $($PYTHON_CMD -c "$PARSE_SCRIPT")
fi

echo -e "${GREEN}✅ Selected Platform: $PLATFORM_NAME ($SELECTED_PLATFORM)${NC}"
echo -e "${GRAY}   Enabled Platforms: $ENABLED_COUNT${NC}"
echo -e "${GREEN}   ✅ Plugin configuration synced${NC}"

# Environment setup
echo -e "\n${CYAN}🔧 Setting up environment...${NC}"

# Clear environment variables
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN ANTHROPIC_BASE_URL ANTHROPIC_API_URL
unset ANTHROPIC_API_VERSION ANTHROPIC_CUSTOM_HEADERS ANTHROPIC_DEFAULT_HEADERS
unset ANTHROPIC_MODEL ANTHROPIC_SMALL_FAST_MODEL ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION
unset ANTHROPIC_TIMEOUT_MS ANTHROPIC_REQUEST_TIMEOUT ANTHROPIC_MAX_RETRIES
unset HTTPS_PROXY HTTP_PROXY
unset MOONSHOT_API_KEY DEEPSEEK_API_KEY SILICONFLOW_API_KEY
unset CLAUDE_API_KEY CLAUDE_AUTH_TOKEN CLAUDE_BASE_URL CLAUDE_MODEL

# Set new environment variables
export ANTHROPIC_API_KEY="$API_KEY"
export ANTHROPIC_BASE_URL="$API_BASE_URL"
export ANTHROPIC_MODEL="$MODEL"
export ANTHROPIC_SMALL_FAST_MODEL="$SMALL_MODEL"

echo -e "${GREEN}✅ Environment configured${NC}"

# Generate UUID and register configuration
echo -e "\n${CYAN}🔐 Registering session...${NC}"

# Generate UUID (compatible with both Linux and Mac)
if command -v uuidgen &> /dev/null; then
    CUSTOM_SESSION_UUID=$(uuidgen | tr '[:upper:]' '[:lower:]')
else
    CUSTOM_SESSION_UUID=$($PYTHON_CMD -c "import uuid; print(str(uuid.uuid4()))")
fi

# Register session configuration
REGISTRATION_SCRIPT="
import json
import sys
from datetime import datetime

# Create session mapping
session_uuid = '$CUSTOM_SESSION_UUID'
session_data = {
    'platform': '$SELECTED_PLATFORM',
    'created': datetime.now().isoformat()
}

# Load existing mappings
session_mappings = {}
try:
    with open('$SESSION_MAPPING_FILE', 'r', encoding='utf-8') as f:
        session_mappings = json.load(f)
except FileNotFoundError:
    pass

# Add new session
session_mappings[session_uuid] = session_data

# Keep only latest 50 sessions
if len(session_mappings) > 50:
    sorted_sessions = sorted(session_mappings.items(), 
                           key=lambda x: x[1].get('created', ''), 
                           reverse=True)[:50]
    session_mappings = dict(sorted_sessions)

# Save to local file
with open('$SESSION_MAPPING_FILE', 'w', encoding='utf-8') as f:
    json.dump(session_mappings, f, indent=2, ensure_ascii=False)

# Sync to plugin directory
with open('$PLUGIN_SESSION_FILE', 'w', encoding='utf-8') as f:
    json.dump(session_mappings, f, indent=2, ensure_ascii=False)

print('✅ Session registered')
print(f'   UUID: {session_uuid}')
print(f'   Platform: $SELECTED_PLATFORM')
print(f'   Model: $MODEL')
"

REG_RESULT=$($PYTHON_CMD -c "$REGISTRATION_SCRIPT" 2>&1)
REG_EXIT_CODE=$?

if [[ $REG_EXIT_CODE -ne 0 ]]; then
    echo -e "${RED}❌ Registration failed: $REG_RESULT${NC}"
    exit 1
else
    echo "$REG_RESULT" | while IFS= read -r line; do
        echo -e "${GREEN}   $line${NC}"
    done
fi

# Launch Claude Code
echo -e "\n${MAGENTA}🚀 Launching Claude Code...${NC}"

# Prepare arguments
CLAUDE_ARGS=("--session-id=$CUSTOM_SESSION_UUID")
if [[ ${#REMAINING_ARGS[@]} -gt 0 ]]; then
    CLAUDE_ARGS+=("${REMAINING_ARGS[@]}")
fi

echo -e "${YELLOW}🎯 Configuration Summary:${NC}"
echo -e "${NC}   Platform: $PLATFORM_NAME${NC}"
echo -e "${GRAY}   Session: $CUSTOM_SESSION_UUID${NC}"
echo -e "${GRAY}   Model: $MODEL${NC}"

COMMAND_STRING="claude ${CLAUDE_ARGS[*]}"
echo -e "\n${GREEN}💻 Executing: $COMMAND_STRING${NC}"
echo -e "${GRAY}============================================================${NC}"

# Execute Claude Code
if ! command -v claude &> /dev/null; then
    echo -e "${RED}❌ Claude command not found. Please install Claude Code first.${NC}"
    exit 1
fi

claude "${CLAUDE_ARGS[@]}"
CLAUDE_EXIT_CODE=$?

# Cleanup and summary
echo -e "\n${GRAY}============================================================${NC}"
if [[ $CLAUDE_EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}🎉 Session completed successfully!${NC}"
else
    echo -e "${RED}❌ Claude Code exited with error code: $CLAUDE_EXIT_CODE${NC}"
fi
echo -e "${NC}   Platform: $PLATFORM_NAME${NC}"
echo -e "${GRAY}   UUID: $CUSTOM_SESSION_UUID${NC}"

exit $CLAUDE_EXIT_CODE