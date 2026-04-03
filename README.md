# 🚀 AWS SSO Synchronizer & Ambient Z-Index

Automatically discovers, maps, and standardizes all your AWS SSO accounts and roles into perfectly formatted local profiles. Built for power users and Agentic AI workflows.

## Features

### 1. Cloud-to-Local Sync (`aws-sso-sync sync`)
Automatically logs into all your SSO portals, retrieves *every* account and role, and safely formats them into `~/.aws/config`. 
It builds a master `account-map.json` so AI Coding Agents can instantly resolve an Account ID to an AWS profile.

### 2. Ambient Z-Index Context (The "Z for AWS")
We bring the `zoxide`/`autojump` philosophy to AWS profiles. The system silently learns which profile you use in which directory, and **automatically switches your AWS profile when you `cd` into that folder.**

- **Learn by doing:** Run `awsp <profile>` inside a project, and the tool remembers that association forever in `~/.aws/z-index.json`.
- **Auto-Recall:** Jump into that project folder tomorrow, and your terminal instantly sets the correct `AWS_PROFILE` in the background.

## Setup & Installation

### Step 1: Install the CLI Package
```bash
# Run this inside the repo directory (or via git+https link)
pip install -e .
```

### Step 2: Install Shell Hooks (Z-Index)
To enable the `awsp` helper and the ambient context tracking, add this to your `~/.bashrc` (or source the `shell_integration.sh` file):

```bash
# 1. Profile Switcher + Z-Index Learner
awsp() {
    if [ -z "$1" ]; then
        if [ -n "$AWS_PROFILE" ]; then echo -e "Current AWS_PROFILE: \033[1;32m$AWS_PROFILE\033[0m\n"; fi
        echo "Available profiles:"
        grep '\[profile' ~/.aws/config | sed 's/\[profile //g' | sed 's/\]//g' | sort | column
    else
        export AWS_PROFILE=$1
        aws-sso-sync learn "$1" 2>/dev/null
        echo -e "AWS_PROFILE set to: \033[1;32m$AWS_PROFILE\033[0m (Learned for this directory!)"
    fi
}

# 2. Ambient Z-Index Restorer (Runs on directory change)
_aws_z_index_hook() {
    if [ "$_LAST_AWS_Z_PWD" != "$PWD" ]; then
        _LAST_AWS_Z_PWD="$PWD"
        local learned=$(aws-sso-sync recall 2>/dev/null)
        if [ -n "$learned" ] && [ "$AWS_PROFILE" != "$learned" ]; then
            export AWS_PROFILE="$learned"
            echo -e "\n\033[2m☁️  [AWS Z-Index] Auto-restored profile: \033[1;32m$learned\033[0m\n"
        fi
    fi
}
PROMPT_COMMAND="_aws_z_index_hook; ${PROMPT_COMMAND:-}"
```