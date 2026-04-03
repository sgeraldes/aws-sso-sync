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
    # Silent success output for seamless bash integration

def cmd_recall(path='.'):
    """Output the profile associated with a directory."""
    abs_path = os.path.abspath(path)
    index = get_z_index()
    if abs_path in index:
        print(index[abs_path].get("profile", ""))

def cmd_ui(out_file=None):
    """Interactive TUI for selecting an AWS Profile."""
    try:
        import questionary
    except ImportError:
        print("Please 'pip install questionary' for the interactive TUI.")
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
            default_choice = title
        elif p == current:
            title = f"▶ {p} (Currently active)"
            
        choices.append(questionary.Choice(title, value=p))

    answer = questionary.select(
        "Select AWS Profile (Start typing to search):",
        choices=choices,
        default=default_choice,
        use_indicator=True,
    ).ask()

    if answer:
        cmd_learn(answer, '.')
        if out_file:
            with open(out_file, 'w', encoding='utf-8') as f:
                f.write(answer)
        else:
            print(answer)

def main():
    parser = argparse.ArgumentParser(description="AWS SSO Synchronizer & Ambient Context Mapper")
    subparsers = parser.add_subparsers(dest="command")

    # Command: sync
    parser_sync = subparsers.add_parser("sync", help="Synchronize AWS SSO accounts and write to ~/.aws/config")

    # Command: learn
    parser_learn = subparsers.add_parser("learn", help="Learn the profile for the current directory")
    parser_learn.add_argument("profile", help="AWS Profile Name")
    parser_learn.add_argument("--path", default=".", help="Directory to associate (defaults to current)")

    # Command: recall
    parser_recall = subparsers.add_parser("recall", help="Print the learned profile for the directory")
    parser_recall.add_argument("--path", default=".", help="Directory to check (defaults to current)")

    # Command: ui
    parser_ui = subparsers.add_parser("ui", help="Interactive TUI for selecting a profile")
    parser_ui.add_argument("--out", help="File to write the selected profile to")

    args = parser.parse_args()

    if args.command == "sync" or not args.command:
        cmd_sync()
    elif args.command == "ui":
        cmd_ui(args.out)
    elif args.command == "learn":
        cmd_learn(args.profile, args.path)
    elif args.command == "recall":
        cmd_recall(args.path)

if __name__ == "__main__":
    main()