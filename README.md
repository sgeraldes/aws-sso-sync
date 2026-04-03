<h1 align="center">
  ☁️ AWS SSO Synchronizer & Ambient Context (Z-Index)
</h1>

<p align="center">
  <strong>Stop fighting with AWS Profiles. Let your terminal read your mind.</strong><br>
  Automatically maps all your AWS SSO accounts and brings <code>autojump</code>/<code>zoxide</code> intelligence to your AWS profiles.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.6+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Mac%20%7C%20Linux-lightgrey.svg" alt="Platforms">
  <img src="https://img.shields.io/badge/Shell-Bash%20%7C%20Zsh%20%7C%20PowerShell-success.svg" alt="Shells">
  <img src="https://img.shields.io/badge/Agentic-AI%20Ready-purple.svg" alt="AI Ready">
</p>

---

## ⚡ What is this?
When you have multiple AWS Organizations (SSO portals) and hundreds of accounts, `aws configure sso` becomes a nightmare. 

**AWS SSO Sync** solves this in two ways:
1. **The Cloud Scanner:** It automatically logs into all your SSO portals, retrieves *every* account and role, and safely formats them into `~/.aws/config` with predictable, standardized profile names.
2. **The Ambient Z-Index (The Magic):** It silently learns which AWS profile you use in which directory. Tomorrow, when you `cd` into that folder, your terminal instantly auto-activates the correct AWS account in the background.

It also generates a local `account-map.json` index so that **AI Coding Agents (like Claude, pi, Cursor, etc.)** can instantly resolve an Account ID to an AWS Profile without asking you to set it manually.

---

## 🚀 Features

* **Zero Configuration:** Just define your `[sso-session]` blocks, and it handles the rest.
* **Interactive TUI:** Type `awsp` to open a beautiful, searchable, keyboard-navigable list of your accounts.
* **Cross-Platform:** Works natively on Windows (PowerShell), Windows (WSL), Mac (Zsh/Bash), and Linux.
* **Agent-Ready Mapping:** Exports an `account-map.json` index.

---

## 🛠️ Installation (1-Minute Setup)

You don't need to clone this repository manually. Just run these commands from anywhere:

### Step 1: Install the CLI 
Use `pipx` (or `pip`) to install the tool globally:
```bash
pip install git+https://github.com/sgeraldes/aws-sso-sync.git
```

### Step 2: Run the Installer
Run the built-in installer. This will automatically detect your operating system and shell (Bash, Zsh, or PowerShell) and safely inject the ambient context hooks:
```bash
aws-sso-sync install
```

### Step 3: Restart your Terminal
Restart your terminal. You can now use the interactive `awsp` command and enjoy ambient context auto-switching!

---

## 🎮 Usage

### 1. The Cloud Sync (Run Once)
To scan your AWS SSO portals and generate your profiles:
```bash
aws-sso-sync sync
```

### 2. The Interactive Switcher
Just type `awsp` in any folder. 
* Use your arrow keys to find your account.
* Hit Enter.
* *Magic:* The tool sets your `AWS_PROFILE` **and** remembers it for that folder forever.

### 3. The Auto-Restorer (Ambient Context)
Leave the folder. When you `cd` back into it later, watch your terminal print:
> `☁️ [AWS Z-Index] Auto-restored profile: mibanco-dev...`

---
*Built with ❤️ in an Agentic Pair Programming Session.*