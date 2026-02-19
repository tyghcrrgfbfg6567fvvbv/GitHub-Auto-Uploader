#!/usr/bin/env python3
"""
GitHub Auto Uploader Pro
Upload local folders/zip files to GitHub with professional UI
Author: mr-risov/GitHub_Auto_Uploader
"""

import os
import sys
import subprocess
import json
import time
import zipfile
import requests
import readline  # For tab completion
import glob
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.box import ROUNDED, DOUBLE
from rich.align import Align
from github import Github, Auth, GithubException

console = Console()

CONFIG_FILE = "github_uploader_config.json"
UPLOADED_FLAG = ".uploaded_to_github"

# ==================== TAB COMPLETION SETUP ====================

class PathCompleter:
    """Custom tab completion for file paths"""
    
    def __init__(self):
        self.matches = []
    
    def complete(self, text, state):
        """Return next match or None"""
        if state == 0:
            # First call - generate matches
            if text.startswith("~"):
                text = os.path.expanduser("~") + text[1:]
            
            if os.path.isdir(text):
                # Complete contents of directory
                try:
                    items = os.listdir(text)
                    self.matches = [os.path.join(text, item) for item in items]
                except PermissionError:
                    self.matches = []
            else:
                # Complete using glob
                try:
                    self.matches = glob.glob(text + "*")
                except:
                    self.matches = []
            
            # Add trailing slashes to directories
            for i, match in enumerate(self.matches):
                if os.path.isdir(match):
                    self.matches[i] = match + os.sep
        
        try:
            return self.matches[state]
        except IndexError:
            return None

def setup_tab_completion():
    """Setup readline for tab completion"""
    completer = PathCompleter()
    readline.set_completer(completer.complete)
    readline.parse_and_bind("tab: complete")
    readline.set_completer_delims(" \t\n;")

def path_input_with_tab(prompt_text, default=""):
    """
    Get path input with tab completion and visual validation
    """
    setup_tab_completion()
    
    console.print(f"\n[bold blue]{prompt_text}[/bold blue]")
    console.print("[dim]Tips: Press TAB to autocomplete | Press Enter to confirm[/dim]")
    console.print("[dim]Examples: ~/Documents/myfolder or ./project or /home/user/code[/dim]")
    
    while True:
        try:
            user_input = input(f"{prompt_text}: ").strip()
            
            if not user_input:
                if default:
                    user_input = default
                else:
                    console.print("[red]⚠️  Path cannot be empty. Please enter a path.[/red]")
                    continue
            
            # Expand user home directory
            expanded_path = os.path.expanduser(user_input)
            absolute_path = os.path.abspath(expanded_path)
            
            # Check if path exists and show visual feedback
            if os.path.exists(absolute_path):
                if os.path.isdir(absolute_path):
                    try:
                        items = os.listdir(absolute_path)
                        files = [f for f in items if os.path.isfile(os.path.join(absolute_path, f))]
                        dirs = [d for d in items if os.path.isdir(os.path.join(absolute_path, d))]
                        
                        console.print(f"[green]✓ Found folder:[/green] [cyan]{absolute_path}[/cyan]")
                        console.print(f"   [dim]Contains: {len(files)} files, {len(dirs)} folders[/dim]")
                    except PermissionError:
                        console.print(f"[green]✓ Found folder:[/green] [cyan]{absolute_path}[/cyan] [dim](permission restricted)[/dim]")
                    return absolute_path
                elif os.path.isfile(absolute_path):
                    if absolute_path.lower().endswith('.zip'):
                        size = os.path.getsize(absolute_path)
                        size_mb = size / (1024 * 1024)
                        console.print(f"[green]✓ Found ZIP file:[/green] [cyan]{absolute_path}[/cyan]")
                        console.print(f"   [dim]Size: {size_mb:.2f} MB[/dim]")
                    else:
                        console.print(f"[yellow]⚠️  Found file (not ZIP):[/yellow] [cyan]{absolute_path}[/cyan]")
                    return absolute_path
            else:
                console.print(f"[red]✗ Not found:[/red] [cyan]{absolute_path}[/cyan]")
                
                # Suggest similar paths
                parent_dir = os.path.dirname(absolute_path) or "."
                if os.path.exists(parent_dir):
                    try:
                        items = os.listdir(parent_dir)
                        basename = os.path.basename(absolute_path).lower()
                        similar = [item for item in items if basename in item.lower() or item.lower() in basename]
                        if similar:
                            console.print(f"[yellow]   Did you mean one of these?[/yellow]")
                            for i, item in enumerate(similar[:5]):
                                console.print(f"      [dim]{i+1}. {os.path.join(parent_dir, item)}[/dim]")
                except:
                    pass
                
                retry = input("Try again? (y/n): ").strip().lower()
                if retry not in ['y', 'yes']:
                    return None
                    
        except KeyboardInterrupt:
            console.print("\n[yellow]Cancelled.[/yellow]")
            return None
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            return None

# ==================== UI FUNCTIONS ====================

def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print professional header"""
    clear_screen()
    console.print(Panel(
        Align.center(
            "[bold cyan]🚀 GITHUB AUTO UPLOADER PRO[/bold cyan]\n"
            "[dim]Professional Repository Management Tool[/dim]\n"
            "[bright_black]Version 3.0 | Secure • Fast • Reliable[/bright_black]\n"
            "[blue]github.com/mr-risov/GitHub_Auto_Uploader[/blue]"
        ),
        box=DOUBLE,
        border_style="bright_blue",
        padding=(1, 2)
    ))

def check_requirements():
    """Check if git is installed and internet is available"""
    with console.status("[bold green]Checking system requirements...") as status:
        result = subprocess.run("git --version", shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            console.print("[bold red]❌ Git is not installed. Please install Git first.[/bold red]")
            sys.exit(1)
        
        try:
            requests.get("https://github.com", timeout=5)
        except:
            console.print("[bold red]❌ No internet connection. Please check your connection.[/bold red]")
            sys.exit(1)

def load_config():
    """Load configuration from file"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_config(config):
    """Save configuration to file"""
    config_to_save = config.copy()
    if 'token' in config_to_save:
        del config_to_save['token']
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_to_save, f, indent=4)

def fetch_github_user(token):
    """Fetch GitHub user info using token"""
    try:
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        response = requests.get('https://api.github.com/user', headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                'login': data.get('login'),
                'name': data.get('name'),
                'email': data.get('email'),
                'id': data.get('id')
            }
        elif response.status_code == 401:
            console.print("[red]❌ Invalid GitHub token![/red]")
            return None
    except Exception as e:
        console.print(f"[red]❌ Error fetching user info: {e}[/red]")
        return None
    return None

# ==================== SELECTION INTERFACE ====================

def select_option_simple(options, message, default_index=0):
    """
    Simple, reliable selection using numbered list
    """
    if not options:
        return None
    
    clear_screen()
    print_header()
    
    table = Table(box=ROUNDED, title=f"[bold blue]{message}[/bold blue]", title_style="bold cyan")
    table.add_column("#", justify="center", style="bright_yellow", width=4)
    table.add_column("Option", style="white", min_width=20)
    
    for i, opt in enumerate(options):
        marker = "▶" if i == default_index else " "
        style = "bold bright_cyan" if i == default_index else "dim"
        table.add_row(f"{marker} {i+1}", f"[{style}]{opt}[/{style}]")
    
    console.print(table)
    console.print(f"\n[dim yellow]Enter number (1-{len(options)}) or press Enter for default ({default_index+1}): [/dim yellow]")
    
    while True:
        try:
            choice = input("> ").strip()
            
            if choice == "":
                return options[default_index]
            
            try:
                num = int(choice)
                if 1 <= num <= len(options):
                    return options[num - 1]
                else:
                    console.print(f"[red]Please enter a number between 1 and {len(options)}[/red]")
            except ValueError:
                console.print("[red]Please enter a valid number[/red]")
                
        except KeyboardInterrupt:
            console.print("\n[yellow]Cancelled.[/yellow]")
            sys.exit(0)

def select_visibility():
    """Select public or private repository"""
    result = select_option_simple(["Public", "Private"], "Repository Visibility", 0)
    return result == "Public"

# ==================== FILE OPERATIONS ====================

def extract_zip(zip_path):
    """Extract zip file and return folder path"""
    if not os.path.exists(zip_path):
        return None
    
    extract_to = os.path.splitext(zip_path)[0]
    
    with console.status(f"[bold green]Extracting {os.path.basename(zip_path)}...") as status:
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            console.print(f"[green]✓ Extracted to: {extract_to}[/green]")
            return extract_to
        except Exception as e:
            console.print(f"[red]❌ Failed to extract: {e}[/red]")
            return None

def setup_and_push(folder_path, repo_url, commit_msg, repo_name, username):
    """Initialize git, commit and push to GitHub"""
    
    if not os.path.exists(folder_path):
        console.print(f"[red]❌ Folder not found: {folder_path}[/red]")
        return False
    
    # Handle empty folder
    if not os.listdir(folder_path):
        console.print("[yellow]⚠️ Folder is empty, creating .gitkeep...[/yellow]")
        with open(os.path.join(folder_path, ".gitkeep"), "w") as f:
            f.write("# Placeholder\n")
    
    steps = [
        ("git init", "Initializing Git repository..."),
        (f"git remote add origin {repo_url}", "Adding remote origin..."),
        ("git add .", "Staging files..."),
        ('git config user.email "uploader@github.auto"', "Configuring git email..."),
        ('git config user.name "GitHub Auto Uploader"', "Configuring git user..."),
    ]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("[cyan]Setting up repository...", total=len(steps) + 3)
        
        for cmd, desc in steps:
            progress.update(task, description=f"[cyan]{desc}")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=folder_path)
            if result.returncode != 0 and "remote add" not in cmd:
                if "already exists" not in result.stderr:
                    console.print(f"[dim red]{result.stderr}[/dim red]")
            progress.advance(task)
            time.sleep(0.1)
        
        # Check for changes
        progress.update(task, description="[cyan]Checking for changes...")
        status_result = subprocess.run("git status --porcelain", shell=True, capture_output=True, text=True, cwd=folder_path)
        has_changes = bool(status_result.stdout.strip())
        progress.advance(task)
        
        # Commit if changes exist
        if has_changes:
            progress.update(task, description=f"[cyan]Committing...")
            commit_cmd = f'git commit -m "{commit_msg}"'
            subprocess.run(commit_cmd, shell=True, capture_output=True, cwd=folder_path)
            progress.advance(task)
        else:
            progress.advance(task)
            console.print("[yellow]⚠️ No changes to commit[/yellow]")
        
        # Set branch and push
        progress.update(task, description="[cyan]Setting main branch...")
        subprocess.run("git branch -M main", shell=True, capture_output=True, cwd=folder_path)
        progress.advance(task)
        
        progress.update(task, description="[cyan]Pushing to GitHub...")
        push_result = subprocess.run("git push -u origin main --force", shell=True, capture_output=True, text=True, cwd=folder_path)
        
        if push_result.returncode != 0:
            console.print(f"[red]❌ Push failed: {push_result.stderr}[/red]")
            return False
        
        progress.update(task, description="[green]✓ Upload complete!", completed=True)
    
    return True

def create_github_repo(g, repo_name, is_public):
    """Create GitHub repository or get existing one"""
    user = g.get_user()
    
    try:
        repo = user.get_repo(repo_name)
        console.print(f"[yellow]⚠️ Repository '{repo_name}' already exists.[/yellow]")
        return repo
    except GithubException:
        try:
            repo = user.create_repo(
                name=repo_name,
                private=not is_public,
                auto_init=False,
                description=f"Uploaded via GitHub Auto Uploader by mr-risov"
            )
            visibility = "Public" if is_public else "Private"
            console.print(f"[green]✓ Created {visibility} repository: {repo_name}[/green]")
            return repo
        except Exception as e:
            console.print(f"[red]❌ Failed to create repository: {e}[/red]")
            return None

# ==================== MAIN APPLICATION ====================

def main():
    """Main application flow"""
    print_header()
    check_requirements()
    
    config = load_config()
    token = os.environ.get("GITHUB_TOKEN")
    
    # ==================== NEW USER FLOW ====================
    if not config.get("username"):
        console.print(Panel(
            "[bold yellow]🔐 Welcome! Let's set up your GitHub access[/bold yellow]\n"
            "[dim]Your credentials will be saved locally for future uploads[/dim]",
            box=ROUNDED,
            border_style="yellow"
        ))
        
        console.print("\n[bold blue]Step 1: GitHub Authentication[/bold blue]")
        console.print("[dim]Create token at: https://github.com/settings/tokens[/dim]")
        console.print("[dim]Required scopes: repo (full control of private repositories)[/dim]\n")
        
        if not token:
            token = Prompt.ask("Enter GitHub Personal Access Token", password=True)
        
        if not token:
            console.print("[red]❌ Token is required![/red]")
            sys.exit(1)
        
        console.print("\n[blue]Verifying token...[/blue]")
        user_info = fetch_github_user(token)
        
        if user_info and user_info.get("login"):
            username = user_info["login"]
            console.print(f"[green]✓ Authenticated as: {username}[/green]")
            if user_info.get("name"):
                console.print(f"[dim]  Name: {user_info['name']}[/dim]")
        else:
            console.print("[red]❌ Could not fetch user info from token. Please check your token.[/red]")
            sys.exit(1)
        
        config.update({
            "username": username,
            "user_info": user_info
        })
        save_config(config)
        
        console.print("[green]✓ Authentication saved![/green]\n")
        
        console.print(Panel(
            "[bold blue]📁 Select Source Folder or ZIP File[/bold blue]\n"
            "[dim]Press TAB to autocomplete folder/file names[/dim]",
            box=ROUNDED
        ))
        
        folder_path = path_input_with_tab("Enter folder path or ZIP file path")
        
        if not folder_path:
            console.print("[red]❌ Valid path is required![/red]")
            sys.exit(1)
        
        if folder_path.lower().endswith('.zip'):
            extracted = extract_zip(folder_path)
            if not extracted:
                sys.exit(1)
            folder_path = extracted
        
        console.print(f"[green]✓ Selected: {folder_path}[/green]\n")
        
        default_repo = os.path.basename(folder_path)
        repo_name = Prompt.ask("Enter repository name", default=default_repo)
        
        if not repo_name:
            repo_name = default_repo
        
        is_public = select_visibility()
        
        commit_msg = Prompt.ask("Enter commit message", default="Initial upload via GitHub Auto Uploader")
        
        config.update({
            "folder_path": folder_path,
            "repo_name": repo_name,
            "is_public": is_public,
            "commit_msg": commit_msg
        })
        save_config(config)
    
    # ==================== RETURNING USER FLOW ====================
    else:
        username = config["username"]
        if not token:
            token = Prompt.ask("Enter GitHub Personal Access Token", password=True)

        if not token:
            console.print("[red]❌ Token is required![/red]")
            sys.exit(1)

        console.print(Panel(
            f"[bold green]👋 Welcome back, {username}![/bold green]",
            box=ROUNDED,
            border_style="green"
        ))
        
        action = select_option_simple(
            ["Upload to existing config", "Upload to new repository", "Update settings"],
            "What would you like to do?",
            0
        )
        
        if action == "Update settings":
            console.print("[green]✓ Settings updated![/green]")
            return
        
        elif action == "Upload to new repository":
            console.print("\n[bold blue]📁 New Repository Setup[/bold blue]")
            
            folder_path = path_input_with_tab("Enter folder name or path")
            
            if not folder_path:
                console.print("[red]❌ Path is required![/red]")
                sys.exit(1)
     
