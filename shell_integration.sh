#!/bin/bash

# ==========================================
# ☁️ AWS Quality of Life Helpers (With Z-Index)
# ==========================================

# AWS Profile Switcher & Z-Index Learner
awsp() {
    if [ -z "$1" ]; then
        if [ -n "$AWS_PROFILE" ]; then
            echo -e "Current AWS_PROFILE: \033[1;32m$AWS_PROFILE\033[0m\n"
        else
            echo -e "Current AWS_PROFILE: \033[1;31mNone\033[0m\n"
        fi
        echo "Available profiles:"
        grep '\[profile' ~/.aws/config | sed 's/\[profile //g' | sed 's/\]//g' | sort | column
    else
        export AWS_PROFILE=$1
        # Teach the ambient Z-index to remember this profile for this directory
        aws-sso-sync learn "$1" 2>/dev/null
        echo -e "AWS_PROFILE set to: \033[1;32m$AWS_PROFILE\033[0m (Learned for this directory!)"
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
