import os
import sys
import subprocess
import json
import time
import zipfile
import requests
import readline
import glob
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.prompt import Prompt
from rich.box import ROUNDED
from github import Github, Auth, UnknownObjectException

console = Console()
CONFIG_FILE = "config.json"
LOG_FILE = "upload.log"

# ==================== PATH COMPLETION SETUP ====================

class PathCompleter:
    """Custom tab completion for file paths"""
    def __init__(self):
        self.matches = []
    
    def complete(self, text, state):
        if state == 0:
            if text.startswith("~"):
                text = os.path.expanduser("~") + text[1:]
            
            if os.path.isdir(text):
                try:
                    items = os.listdir(text)
                    self.matches = [os.path.join(text, item) for item in items]
                except PermissionError:
                    self.matches = []
            else:
                try:
                    self.matches = glob.glob(text + "*")
                except:
                    self.matches = []
            
            for i, match in enumerate(self.matches):
                if os.path.isdir(match):
                    self.matches[i] = match + os.sep
        
        try:
            return self.matches[state]
        except IndexError:
            return None

def setup_tab_completion():
    completer = PathCompleter()
    readline.set_completer(completer.complete)
    if 'libedit' in readline.__doc__:
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")
    readline.set_completer_delims(" \t\n;")

# ==================== CORE FUNCTIONS ====================

def log(message):
    with open(LOG_FILE, "a") as f:
        f.write(f"[{time.ctime()}] {message}\n")

def check_git_installed():
    try:
        subprocess.run(["git", "--version"], capture_output=True, text=True, check=True)
    except:
        console.print("[bold red]❌ Git is not installed. Please install Git first.[/bold red]")
        sys.exit(1)

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def fetch_github_username(token):
    try:
        headers = {'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'}
        response = requests.get('https://api.github.com/user', headers=headers, timeout=10)
        if response.status_code == 200:
            return response.json().get('login')
    except:
        pass
    return None

def auto_detect_folder(folder_name):
    """Automatically detect a folder by name in the system"""
    console.print(f"[blue]🔍 Searching for folder: '{folder_name}'...[/blue]")
    
    # Check current directory first
    if os.path.isdir(folder_name):
        return os.path.abspath(folder_name)
    
    # Search common locations based on OS
    if os.name == 'nt':
        search_roots = [f"{chr(drive)}:\\" for drive in range(ord('C'), ord('Z') + 1) if os.path.exists(f"{chr(drive)}:\\")]
    else:
        search_roots = [os.path.expanduser("~"), '/']

    for root_dir in search_roots:
        try:
            for root, dirs, _ in os.walk(root_dir):
                if folder_name in dirs:
                    found_path = os.path.join(root, folder_name)
                    console.print(f"[green]✅ Found: {found_path}[/green]")
                    return found_path
                # Limit depth for performance
                if root.count(os.sep) - root_dir.count(os.sep) > 3:
                    del dirs[:]
        except:
            continue
    return None

def run_command(command, cwd=None):
    result = subprocess.run(command, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        log(f"Error executing {' '.join(command)}: {result.stderr}")
    return result

def handle_gitignore(folder):
    """Detect common heavy/sensitive files and offer to create a .gitignore"""
    common_ignores = [".env", "node_modules", "__pycache__", ".venv", "venv", ".git"]
    found_to_ignore = []
    
    for item in common_ignores:
        if os.path.exists(os.path.join(folder, item)):
            found_to_ignore.append(item)
            
    if found_to_ignore:
        console.print(f"\n[yellow]🔍 I found some files/folders that are usually ignored: {', '.join(found_to_ignore)}[/yellow]")
        if Prompt.ask("Do you want to create/update .gitignore to exclude these?", choices=["Yes", "No"], default="Yes") == "Yes":
            gitignore_path = os.path.join(folder, ".gitignore")
            existing_content = ""
            if os.path.exists(gitignore_path):
                with open(gitignore_path, "r") as f:
                    existing_content = f.read()
            
            with open(gitignore_path, "a") as f:
                if not existing_content.endswith("\n") and existing_content:
                    f.write("\n")
                for item in found_to_ignore:
                    if item not in existing_content:
                        f.write(f"{item}/\n" if os.path.isdir(os.path.join(folder, item)) else f"{item}\n")
            console.print("[green]✅ .gitignore updated![/green]")

def setup_git_and_push(folder, repo_url, commit_message):
    if not os.path.exists(folder):
        console.print(f"[bold red]❌ Folder '{folder}' does not exist![/bold red]")
        sys.exit(1)

    # Handle gitignore before staging
    handle_gitignore(folder)

    steps = [
        (["git", "init"], "Initializing Git..."),
        (["git", "remote", "remove", "origin"], "Resetting remote..."),
        (["git", "remote", "add", "origin", repo_url], "Adding remote..."),
        (["git", "add", "."], "Staging files..."),
        (["git", "config", "user.email", "auto@upload.bot"], "Setting email..."),
        (["git", "config", "user.name", "GitUploaderBot"], "Setting name..."),
    ]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task("[cyan]Processing Git", total=len(steps) + 2)
        
        for cmd, desc in steps:
            progress.update(task, description=f"[cyan]{desc}", advance=1)
            run_command(cmd, cwd=folder)
        
        # Check for changes and commit
        status = run_command(["git", "status", "--porcelain"], cwd=folder)
        if status.stdout.strip():
            progress.update(task, description="[cyan]Committing...", advance=0.5)
            run_command(["git", "commit", "-m", commit_message], cwd=folder)
        
        progress.update(task, description="[cyan]Pushing to GitHub...", advance=1)
        run_command(["git", "branch", "-M", "main"], cwd=folder)
        push = run_command(["git", "push", "-u", "origin", "main", "--force"], cwd=folder)
        
        if push.returncode == 0:
            progress.update(task, description="[green]Done!", completed=True)
            return True
        else:
            console.print(f"[bold red]❌ Push failed: {push.stderr}[/bold red]")
            return False

# ==================== MAIN FLOW ====================

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel("[bold blue]🚀 GITHUB AUTO UPLOADER PRO[/bold blue]", box=ROUNDED))
    
    check_git_installed()
    config = load_config()
    
    # 1. First time setup: Authentication
    if not config.get("token") or not config.get("username"):
        console.print("\n[bold cyan]🔐 Initial Authentication Setup[/bold cyan]")
        token = Prompt.ask("Enter GitHub Personal Access Token", password=True)
        
        username = fetch_github_username(token)
        if not username:
            console.print("[yellow]⚠️  Could not auto-fetch username.[/yellow]")
            username = Prompt.ask("Enter your GitHub username")
        else:
            console.print(f"[green]✅ Authenticated as: {username}[/green]")
        
        config["token"] = token
        config["username"] = username
        save_config(config)
    
    token = config["token"]
    username = config["username"]
    
    # 2. Ask for Repo Name every time
    repo_name = Prompt.ask("\n📦 Enter repository name")
    
    # 3. Ask for Folder Name or Path with Tab Completion
    setup_tab_completion()
    console.print("\n[bold cyan]📁 Enter folder name or path (Press TAB to autocomplete):[/bold cyan]")
    try:
        folder_input = input("> ").strip()
    except EOFError:
        sys.exit(0)
    
    folder_path = None
    if os.path.exists(folder_input):
        folder_path = os.path.abspath(folder_input)
    else:
        # If it's just a name, try to find it
        folder_path = auto_detect_folder(folder_input)
        
    if not folder_path or not os.path.isdir(folder_path):
        console.print(f"[bold red]❌ Error: Could not find directory '{folder_input}'[/bold red]")
        sys.exit(1)
        
    is_public = Prompt.ask("Repository visibility", choices=["Public", "Private"], default="Public") == "Public"
    commit_msg = Prompt.ask("Enter commit message", default="Upload via Auto Uploader")
    
    # 4. Perform Upload
    g = Github(auth=Auth.Token(token))
    try:
        user = g.get_user()
        try:
            repo = user.get_repo(repo_name)
            console.print(f"[yellow]✓ Using existing repository: {repo_name}[/yellow]")
        except UnknownObjectException:
            console.print(f"[blue]✨ Creating new repository: {repo_name}...[/blue]")
            repo = user.create_repo(repo_name, private=not is_public)
        
        repo_url = f"https://{token}@github.com/{username}/{repo_name}.git"
        if setup_git_and_push(folder_path, repo_url, commit_msg):
            console.print(f"\n[bold green]✅ Success! Repository URL: https://github.com/{username}/{repo_name}[/bold green]")
            
    except Exception as e:
        console.print(f"[bold red]❌ Error: {str(e)}[/bold red]")

if __name__ == "__main__":
    main()
