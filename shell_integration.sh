#!/bin/bash

# ==========================================
# ☁️ AWS Quality of Life Helpers (With Z-Index)
# ==========================================

# AWS Profile Switcher & Z-Index Learner (TUI)
awsp() {
    if [ -n "$1" ]; then
        # Direct assignment if argument provided
        export AWS_PROFILE=$1
        aws-sso-sync learn "$1" 2>/dev/null
        echo -e "AWS_PROFILE set to: \033[1;32m$AWS_PROFILE\033[0m (Learned for this directory!)"
    else
        # Interactive TUI mode
        local tmp_file="/tmp/aws_sso_sync_selection"
        aws-sso-sync ui --out "$tmp_file"
        
        if [ -f "$tmp_file" ]; then
            local selected=$(cat "$tmp_file")
            rm -f "$tmp_file"
            if [ -n "$selected" ]; then
                export AWS_PROFILE="$selected"
                echo -e "\n\033[1;32m☁️ AWS_PROFILE activated: $AWS_PROFILE\033[0m\n"
            fi
        fi
    fi
}

# Ambient Z-Index Auto-Restorer
# Detects directory changes and automatically restores learned AWS profiles
_aws_z_index_hook() {
    if [ "$_LAST_AWS_Z_PWD" != "$PWD" ]; then
        _LAST_AWS_Z_PWD="$PWD"
        local learned
        learned=$(aws-sso-sync recall 2>/dev/null)
        if [ -n "$learned" ] && [ "$AWS_PROFILE" != "$learned" ]; then
            export AWS_PROFILE="$learned"
            echo -e "\033[2m☁️  [AWS Z-Index] Auto-restored profile: \033[1;32m$learned\033[0m"
        fi
    fi
}

# Safely append to PROMPT_COMMAND if not already present
if [[ ! "$PROMPT_COMMAND" == *"_aws_z_index_hook"* ]]; then
    PROMPT_COMMAND="_aws_z_index_hook; ${PROMPT_COMMAND:-}"
fi
