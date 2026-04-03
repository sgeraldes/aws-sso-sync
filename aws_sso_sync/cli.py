#!/usr/bin/env python3
import os
import json
import glob
import subprocess
import re
import argparse
from datetime import datetime, timezone

AWS_DIR = os.path.expanduser("~/.aws")
CONFIG_FILE = os.path.join(AWS_DIR, "config")
CACHE_DIR = os.path.join(AWS_DIR, "sso", "cache")
MAP_FILE = os.path.join(AWS_DIR, "account-map.json")
Z_INDEX_FILE = os.path.join(AWS_DIR, "z-index.json")

def sanitize(text):
    s = re.sub(r'[^a-zA-Z0-9]', '-', text).lower()
    s = re.sub(r'-+', '-', s)
    return s.strip('-')

def get_sso_sessions():
    sessions = {}
    current_session = None
    if not os.path.exists(CONFIG_FILE): return sessions
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            match = re.match(r'^\[sso-session\s+([^\]]+)\]', line)
            if match:
                current_session = match.group(1)
                sessions[current_session] = {}
                continue
            if current_session and '=' in line and not line.startswith('['):
                key, val = line.split('=', 1)
                sessions[current_session][key.strip()] = val.strip()
            elif line.startswith('['):
                current_session = None
    return sessions

def get_cached_token(start_url):
    if not os.path.exists(CACHE_DIR): return None
    for cache_file in glob.glob(os.path.join(CACHE_DIR, "*.json")):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f: data = json.load(f)
            if data.get('startUrl') == start_url:
                expires_at = data.get('expiresAt')
                if expires_at:
                    expires_dt = datetime.strptime(expires_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                    if expires_dt > datetime.now(timezone.utc): return data.get('accessToken')
        except Exception: continue
    return None

def run_aws_json_cmd(cmd):
    is_windows = os.name == 'nt'
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=is_windows)
    if result.returncode != 0: raise Exception(f"AWS CLI Error: {result.stderr}")
    try: return json.loads(result.stdout)
    except json.JSONDecodeError: return {}

def login_sso_session(session_name):
    print(f"\n[!] Token missing or expired for SSO Session: '{session_name}'")
    print(f"[*] Opening browser for authentication...")
    is_windows = os.name == 'nt'
    result = subprocess.run(["aws", "sso", "login", "--sso-session", session_name], shell=is_windows)
    if result.returncode != 0:
        print(f"[-] Failed to login to session {session_name}.")
        return False
    return True

def cmd_sync():
    """Sync AWS SSO Accounts and generate profiles."""
    print("==================================================")
    print(">> AWS SSO Profile Synchronizer & Agent Mapper")
    print("==================================================")
    sessions = get_sso_sessions()
    if not sessions:
        print("[-] No [sso-session] blocks found in ~/.aws/config")
        return

    account_map = {}
    generated_profiles = []

    for session_name, config in sessions.items():
        start_url = config.get('sso_start_url')
        region = config.get('sso_region')
        if not start_url or not region: continue
            
        print(f"\nProcessing SSO Session: \033[1;36m{session_name}\033[0m")
        token = get_cached_token(start_url)
        if not token:
            if not login_sso_session(session_name): continue
            token = get_cached_token(start_url)
            
        if not token:
            print(f"[-] Still couldn't find a valid token for {session_name}. Skipping.")
            continue
            
        print("[+] Token valid. Fetching accounts...")
        try:
            accounts_resp = run_aws_json_cmd(["aws", "sso", "list-accounts", "--access-token", token, "--region", region])
            accounts = accounts_resp.get("accountList", [])
        except Exception as e:
            print(f"[-] Error fetching accounts: {e}")
            continue

        for acc in accounts:
            acc_id = acc.get("accountId")
            acc_name = acc.get("accountName", "Unknown")
            print(f"    -> Found Account: {acc_name} ({acc_id})")
            try:
                roles_resp = run_aws_json_cmd(["aws", "sso", "list-account-roles", "--access-token", token, "--account-id", acc_id, "--region", region])
                roles = roles_resp.get("roleList", [])
            except Exception: continue

            for role in roles:
                role_name = role.get("roleName")
                clean_acc_name = sanitize(acc_name)
                clean_role_name = sanitize(role_name)
                profile_name = f"{session_name}-{clean_acc_name}-{clean_role_name}"
                if clean_role_name.startswith("aws"):
                    clean_role_name = clean_role_name[3:].strip('-')
                    profile_name = f"{session_name}-{clean_acc_name}-{clean_role_name}"
                
                print(f"       + Role: {role_name} => Profile: [profile {profile_name}]")
                if acc_id not in account_map: account_map[acc_id] = {}
                account_map[acc_id][role_name] = {"sso_session": session_name, "account_name": acc_name, "profile": profile_name}
                
                generated_profiles.append(f"[profile {profile_name}]\nsso_session = {session_name}\nsso_account_id = {acc_id}\nsso_role_name = {role_name}\nregion = {region}\n")

    with open(MAP_FILE, 'w', encoding='utf-8') as f: json.dump(account_map, f, indent=2)
    print(f"\n[+] Successfully created Agent Account Map at: {MAP_FILE}")

    MARKER_START = "# ==========================================\n# 🤖 AUTO-GENERATED PROFILES (DO NOT EDIT MANUALLY)\n# ==========================================\n"
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f: content = f.read()
    base_content = content.split(MARKER_START)[0] if MARKER_START in content else content + "\n\n"
    new_config = base_content + MARKER_START + "\n".join(generated_profiles)

    with open(CONFIG_FILE, 'w', encoding='utf-8') as f: f.write(new_config)
    print(f"[+] Successfully wrote {len(generated_profiles)} profile(s) to {CONFIG_FILE}")

def get_z_index():
    if os.path.exists(Z_INDEX_FILE):
        try:
            with open(Z_INDEX_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except Exception: pass
    return {}

def save_z_index(data):
    with open(Z_INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def cmd_learn(profile, path='.'):
    """Associate a profile with a directory."""
    abs_path = os.path.abspath(path)
    index = get_z_index()
    index[abs_path] = {
        "profile": profile,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    save_z_index(index)

def cmd_recall(path='.'):
    """Output the profile associated with a directory."""
    abs_path = os.path.abspath(path)
    index = get_z_index()
    if abs_path in index:
        print(index[abs_path].get("profile", ""))

def cmd_ui(out_file=None):
    """Interactive TUI for selecting an AWS Profile."""
    try:
        from InquirerPy import inquirer
    except ImportError:
        print("Please 'pip install InquirerPy' for the interactive TUI.")
        return

    profiles = []
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('[profile '):
                    profiles.append(line.split()[1].strip(']'))

    if not profiles:
        print("No profiles found in ~/.aws/config")
        return

    profiles.sort()
    learned = get_z_index().get(os.path.abspath('.'), {}).get("profile", "")
    current = os.environ.get("AWS_PROFILE", "")

    choices = []
    default_choice = None

    for p in profiles:
        title = p
        if p == learned:
            title = f"⭐ {p} (Learned here)"
            default_choice = p
        elif p == current:
            title = f"▶ {p} (Currently active)"
            
        choices.append({"name": title, "value": p})

    header = "☁️ AWS Profile Selector  •  by Sebastian Geraldes  •  github.com/sgeraldes/aws-sso-sync"

    try:
        answer = inquirer.fuzzy(
            message=header,
            choices=choices,
            default=default_choice,
            max_height="70%",
            instruction="",
            long_instruction="Type to search • Enter select • Esc cancel",
            keybindings={
                "interrupt": [{"key": "c-c"}, {"key": "escape"}],
            },
        ).execute()
    except KeyboardInterrupt:
        return

    if answer:
        cmd_learn(answer, '.')
        if out_file:
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(answer)
        else:
            print(answer)

def cmd_install():
    """Install shell hooks for Bash, Zsh, and PowerShell."""
    
    hook_dir = os.path.join(AWS_DIR, "sso-sync")
    os.makedirs(hook_dir, exist_ok=True)
    
    sh_hook_path = os.path.join(hook_dir, "hook.sh")
    ps1_hook_path = os.path.join(hook_dir, "hook.ps1")
    
    # Bash/Zsh hook
    sh_code = '''
# AWS SSO Sync - Shell Integration
awsp() {
    if [ -n "$1" ]; then
        export AWS_PROFILE=$1
        aws-sso-sync learn "$1" >/dev/null 2>&1
        echo -e "AWS_PROFILE set to: \\033[1;32m$AWS_PROFILE\\033[0m (Learned!)"
    else
        local tmp_file="/tmp/aws_sso_sync_selection_$$"
        aws-sso-sync ui --out "$tmp_file"
        if [ -f "$tmp_file" ]; then
            local selected=$(cat "$tmp_file")
            rm -f "$tmp_file"
            if [ -n "$selected" ]; then
                export AWS_PROFILE="$selected"
                echo -e "\\n\\033[1;32m☁️ AWS_PROFILE activated: $AWS_PROFILE\\033[0m\\n"
            fi
        fi
    fi
}

_aws_z_index_hook() {
    if [ "$_LAST_AWS_Z_PWD" != "$PWD" ]; then
        _LAST_AWS_Z_PWD="$PWD"
        local learned=$(aws-sso-sync recall 2>/dev/null)
        if [ -n "$learned" ] && [ "$AWS_PROFILE" != "$learned" ]; then
            export AWS_PROFILE="$learned"
            echo -e "\\033[2m☁️  [AWS Z-Index] Auto-restored profile: \\033[1;32m$learned\\033[0m"
        fi
    fi
}

if [ -n "$BASH_VERSION" ]; then
    if [[ ! "$PROMPT_COMMAND" == *"_aws_z_index_hook"* ]]; then
        PROMPT_COMMAND="_aws_z_index_hook; ${PROMPT_COMMAND:-}"
    fi
elif [ -n "$ZSH_VERSION" ]; then
    autoload -Uz add-zsh-hook
    add-zsh-hook chpwd _aws_z_index_hook
fi
'''
    
    with open(sh_hook_path, 'w', encoding='utf-8') as f:
        f.write(sh_code.strip())

    # PowerShell hook
    ps_code = '''
function awsp {
    param([string]$profileName)
    if ($profileName) {
        $env:AWS_PROFILE = $profileName
        aws-sso-sync learn $profileName | Out-Null
        Write-Host "AWS_PROFILE set to: $env:AWS_PROFILE (Learned!)" -ForegroundColor Green
    } else {
        $tmpFile = [System.IO.Path]::GetTempFileName()
        aws-sso-sync ui --out $tmpFile
        if (Test-Path $tmpFile) {
            $selected = Get-Content $tmpFile
            Remove-Item $tmpFile
            if (![string]::IsNullOrWhiteSpace($selected)) {
                $env:AWS_PROFILE = $selected
                Write-Host "`n☁️ AWS_PROFILE activated: $env:AWS_PROFILE`n" -ForegroundColor Green
            }
        }
    }
}

$global:AwsZIndexLastPwd = ""
function Invoke-AwsZIndexHook {
    if ($global:AwsZIndexLastPwd -ne $PWD.Path) {
        $global:AwsZIndexLastPwd = $PWD.Path
        $learned = aws-sso-sync recall 2>$null
        if (![string]::IsNullOrWhiteSpace($learned) -and $env:AWS_PROFILE -ne $learned) {
            $env:AWS_PROFILE = $learned
            Write-Host "`n☁️  [AWS Z-Index] Auto-restored profile: $learned" -ForegroundColor DarkGray
        }
    }
}

if (Test-Path "Function:\\prompt") {
    $originalPrompt = $function:prompt
    function prompt {
        Invoke-AwsZIndexHook
        & $originalPrompt
    }
} else {
    function prompt {
        Invoke-AwsZIndexHook
        "PS $($executionContext.SessionState.Path.CurrentLocation)$('>' * ($nestedPromptLevel + 1)) "
    }
}
'''
    
    with open(ps1_hook_path, 'w', encoding='utf-8') as f:
        f.write(ps_code.strip())

    print("[+] Wrote cross-platform hooks to ~/.aws/sso-sync/")

    # Inject into RC files
    def _sanitize_profile_content(content: str) -> str:
        """Repair legacy malformed insertions from earlier installer versions."""
        fixed = content.replace("\r\n", "\n")

        # Repair literal escaped newlines accidentally written as text
        fixed = fixed.replace("\\nsource ", "\nsource ")
        fixed = fixed.replace("\\n. \"", "\n. \"")
        fixed = fixed.replace("\"\\n", "\"\n")

        # Remove legacy repo-local integration lines (old approach)
        fixed_lines = []
        for line in fixed.split("\n"):
            if "shell_integration.sh" in line:
                continue
            if "shell_integration.ps1" in line:
                continue
            fixed_lines.append(line)

        return "\n".join(fixed_lines)

    def inject_source(rc_file, source_line):
        rc_path = os.path.expanduser(rc_file)

        if not os.path.exists(rc_path):
            with open(rc_path, 'w', encoding='utf-8') as f:
                f.write(source_line)
                f.write('\n')
            print(f"[+] Created {rc_file} and injected hook.")
            return

        with open(rc_path, 'r', encoding='utf-8') as f:
            content = f.read()

        sanitized = _sanitize_profile_content(content)
        if sanitized != content:
            with open(rc_path, 'w', encoding='utf-8') as f:
                f.write(sanitized)
            content = sanitized

        if source_line not in content:
            with open(rc_path, 'a', encoding='utf-8') as f:
                if not content.endswith('\n'):
                    f.write('\n')
                f.write(source_line)
                f.write('\n')
            print(f"[+] Injected hook into {rc_file}")
        else:
            print(f"[*] Hook already exists in {rc_file}")

    sh_source_line = f'source "{sh_hook_path}"'
    inject_source("~/.bashrc", sh_source_line)
    inject_source("~/.zshrc", sh_source_line)

    if os.name == 'nt':
        ps_source_line = f'. "{ps1_hook_path}"'
        
        try:
            pwsh_cmd = subprocess.run(['pwsh', '-NoProfile', '-Command', '"" + $PROFILE'], capture_output=True, text=True)
            if pwsh_cmd.returncode == 0 and pwsh_cmd.stdout.strip():
                ps_profile = pwsh_cmd.stdout.strip()
                os.makedirs(os.path.dirname(ps_profile), exist_ok=True)
                inject_source(ps_profile, ps_source_line)
        except Exception:
            pass

        try:
            ps_cmd = subprocess.run(['powershell', '-NoProfile', '-Command', '"" + $PROFILE'], capture_output=True, text=True)
            if ps_cmd.returncode == 0 and ps_cmd.stdout.strip():
                ps_profile_old = ps_cmd.stdout.strip()
                os.makedirs(os.path.dirname(ps_profile_old), exist_ok=True)
                inject_source(ps_profile_old, ps_source_line)
        except Exception:
            pass

    print("\n[+] Installation complete! Please restart your terminal or open a new tab.")


def main():
    parser = argparse.ArgumentParser(description="AWS SSO Synchronizer & Ambient Context Mapper")
    subparsers = parser.add_subparsers(dest="command")

    parser_sync = subparsers.add_parser("sync", help="Synchronize AWS SSO accounts and write to ~/.aws/config")

    parser_learn = subparsers.add_parser("learn", help="Learn the profile for the current directory")
    parser_learn.add_argument("profile", help="AWS Profile Name")
    parser_learn.add_argument("--path", default=".", help="Directory to associate (defaults to current)")

    parser_recall = subparsers.add_parser("recall", help="Print the learned profile for the directory")
    parser_recall.add_argument("--path", default=".", help="Directory to check (defaults to current)")

    parser_ui = subparsers.add_parser("ui", help="Interactive TUI for selecting a profile")
    parser_ui.add_argument("--out", help="File to write the selected profile to")

    parser_install = subparsers.add_parser("install", help="Install shell hooks for Bash, Zsh, and PowerShell")

    args = parser.parse_args()

    if args.command == "sync" or not args.command:
        cmd_sync()
    elif args.command == "learn":
        cmd_learn(args.profile, args.path)
    elif args.command == "recall":
        cmd_recall(args.path)
    elif args.command == "ui":
        cmd_ui(args.out)
    elif args.command == "install":
        cmd_install()

if __name__ == "__main__":
    main()
