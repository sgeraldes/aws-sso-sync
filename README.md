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

This tool works seamlessly across **Windows (PowerShell), Windows (WSL / Bash), Mac (Zsh/Bash), and Linux.**

### Step 1: Install the CLI
Use `pipx` (or `pip`) to install the tool globally from your Git repository:
```bash
pip install git+https://github.com/YOUR_GITHUB_USERNAME/aws-sso-sync.git
```
*(Note: Replace `YOUR_GITHUB_USERNAME` with your actual username once you push this code to GitHub.)*

### Step 2: Run the Installer
Run the built-in installer. This will automatically detect your operating system and shell (Bash, Zsh, or PowerShell) and safely inject the ambient context hooks:
```bash
aws-sso-sync install
```

### Step 3: Restart your Terminal
Restart your terminal. You can now use the interactive `awsp` command and enjoy ambient context auto-switching!