import os
import sys
import subprocess
import json
import time
import zipfile
import requests
import readline
import glob
import inquirer
import shutil
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.prompt import Prompt
from rich.box import ROUNDED, DOUBLE_EDGE
from rich.table import Table
from rich.text import Text
from github import Github, Auth, UnknownObjectException

console = Console()
CONFIG_FILE = "config.json"
LOG_FILE = "upload.log"

# ==================== UI HELPERS ====================

def print_header():
    os.system('cls' if os.name == 'nt' else 'clear')
    console.print(Panel.fit(
        "[bold blue]🚀 GITHUB AUTO UPLOADER PRO[/bold blue]\n"
        "[dim]Version 2.0 • Advanced Automation Tool[/dim]",
        box=DOUBLE_EDGE,
        border_style="bright_blue",
        padding=(1, 4)
    ))

def print_step(message):
    console.print(f"\n[bold cyan]▶ {message}[/bold cyan]")

def print_success(message):
    console.print(Panel(f"[bold green]✅ {message}[/bold green]", border_style="green", expand=False))

def print_error(message):
    console.print(Panel(f"[bold red]❌ {message}[/bold red]", border_style="red", expand=False))

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
        print_error("Git is not installed. Please install Git first.")
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
            
    # Check for large files (> 50MB)
    large_files = []
    for root, dirs, files in os.walk(folder):
        # Skip directories already marked for ignore or common hidden ones
        dirs[:] = [d for d in dirs if d not in common_ignores and not d.startswith('.')]
        for file in files:
            file_path = os.path.join(root, file)
            try:
                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                if size_mb > 50:
                    rel_path = os.path.relpath(file_path, folder)
                    large_files.append((rel_path, size_mb))
            except:
                continue

    if found_to_ignore:
        console.print(f"\n[yellow]🔍 I found some files/folders that are usually ignored: {', '.join(found_to_ignore)}[/yellow]")
        questions = [
            inquirer.List('choice',
                          message="Do you want to create/update .gitignore to exclude these?",
                          choices=['Yes', 'No'],
                          default='Yes'),
        ]
        answer = inquirer.prompt(questions)
        if answer and answer['choice'] == "Yes":
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

    if large_files:
        console.print(f"\n[yellow]⚠️  Detected large files (> 50MB) that might fail GitHub upload:[/yellow]")
        for rel_path, size_mb in large_files:
            color = "red" if size_mb > 100 else "yellow"
            console.print(f"   [{color}]- {rel_path} ({size_mb:.2f} MB)[/{color}]")
        
        questions = [
            inquirer.List('choice',
                          message="Do you want to add these large files to .gitignore?",
                          choices=['Yes', 'No'],
                          default='Yes'),
        ]
        answer = inquirer.prompt(questions)
        if answer and answer['choice'] == "Yes":
            gitignore_path = os.path.join(folder, ".gitignore")
            existing_content = ""
            if os.path.exists(gitignore_path):
                with open(gitignore_path, "r") as f:
                    existing_content = f.read()
            
            with open(gitignore_path, "a") as f:
                if not existing_content.endswith("\n") and existing_content:
                    f.write("\n")
                for rel_path, _ in large_files:
                    if rel_path not in existing_content:
                        f.write(f"{rel_path}\n")
            console.print("[green]✅ Large files added to .gitignore![/green]")

def setup_git_and_push(folder, repo_url, commit_message):
    if not os.path.exists(folder):
        print_error(f"Folder '{folder}' does not exist!")
        return False

    handle_gitignore(folder)

    steps = [
        (["git", "init"], "Initializing Git..."),
        (["git", "remote", "remove", "origin"], "Resetting remote..."),
        (["git", "remote", "add", "origin", repo_url], "Adding remote..."),
        (["git", "rm", "-r", "--cached", "."], "Cleaning index..."),
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
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task("[cyan]Processing Git", total=len(steps) + 2)
        
        for cmd, desc in steps:
            progress.update(task, description=f"[cyan]{desc}", advance=1)
            run_command(cmd, cwd=folder)
        
        status = run_command(["git", "status", "--porcelain"], cwd=folder)
        if status.stdout.strip():
            progress.update(task, description="[cyan]Committing...", advance=0.5)
            run_command(["git", "commit", "-m", commit_message], cwd=folder)
        
        progress.update(task, description="[cyan]Pushing to GitHub...", advance=1)
        run_command(["git", "branch", "-M", "main"], cwd=folder)
        push = run_command(["git", "push", "-u", "origin", "main", "--force"], cwd=folder)
        
        if push.returncode == 0:
            return True
        else:
            progress.stop()
            if any(x in push.stderr for x in ["Large files detected", "exceeds GitHub's file size limit", "pre-receive hook declined"]):
                console.print(f"\n[bold red]❌ Push failed due to large files in history.[/bold red]")
                console.print("[yellow]Note: Deleting files isn't enough; they remain in Git's history.[/yellow]")
                
                questions = [
                    inquirer.List('choice',
                                  message="How to proceed?",
                                  choices=['🔄 Attempt Fresh Push (Clean history)', '❌ Cancel'],
                                  default='🔄 Attempt Fresh Push (Clean history)')
                ]
                ans = inquirer.prompt(questions)
                if ans and "Fresh Push" in ans['choice']:
                    console.print("[blue]🧹 Cleaning up history...[/blue]")
                    git_dir = os.path.join(folder, ".git")
                    if os.path.exists(git_dir):
                        shutil.rmtree(git_dir)
                    return setup_git_and_push(folder, repo_url, commit_message)
            else:
                print_error(f"Push failed: {push.stderr}")
            
            return False

def delete_repository(g):
    """Fetch and delete a repository with confirmation"""
    try:
        user = g.get_user()
        with console.status("[blue]Fetching repositories...[/blue]"):
            repos = [repo.name for repo in user.get_repos()]
        
        if not repos:
            console.print("[yellow]⚠️ No repositories found.[/yellow]")
            return

        choices = sorted(repos) + ["🔙 Back to Main Menu"]
        questions = [
            inquirer.List('repo',
                          message="Select repository to DELETE",
                          choices=choices,
                          carousel=True)
        ]
        ans = inquirer.prompt(questions)
        if not ans or "Back" in ans['repo']:
            return
            
        repo_name = ans['repo']
        
        confirm_q = [
            inquirer.List('confirm',
                          message=f"Are you ABSOLUTELY sure you want to delete '{repo_name}'?",
                          choices=['No', 'Yes'],
                          default='No')
        ]
        conf = inquirer.prompt(confirm_q)
        if conf and conf['confirm'] == 'Yes':
            repo = user.get_repo(repo_name)
            repo.delete()
            print_success(f"Repository '{repo_name}' deleted!")
        else:
            console.print("[blue]Operation cancelled.[/blue]")
            
    except Exception as e:
        print_error(f"Error deleting repository: {str(e)}")

def create_archive_release(repo):
    """Create a release of the current remote state before overwriting"""
    try:
        try:
            repo.get_commits().get_page(0)
        except:
            return

        console.print("\n[cyan]📦 Archiving current remote version...[/cyan]")
        version = Prompt.ask("Enter version tag (e.g., v1.0.old)", default=f"v{int(time.time())}")
        
        repo.create_git_release(
            tag=version,
            name=f"Archive: {version}",
            message="Automatic archive before fresh upload.",
            draft=False,
            prerelease=False
        )
        print_success(f"Archive release '{version}' created!")
    except Exception as e:
        console.print(f"[yellow]⚠️ Could not create archive: {str(e)}[/yellow]")

def show_system_info(username):
    table = Table(title="System Information", box=ROUNDED, header_style="bold blue")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="magenta")
    
    table.add_row("Authenticated As", username)
    table.add_row("Platform", sys.platform)
    table.add_row("Python Version", sys.version.split()[0])
    table.add_row("Config Location", os.path.abspath(CONFIG_FILE))
    
    console.print(table)

# ==================== MAIN FLOW ====================

def main():
    print_header()
    check_git_installed()
    config = load_config()
    
    if not config.get("token") or not config.get("username"):
        print_step("Initial Authentication Setup")
        token = Prompt.ask("Enter GitHub Personal Access Token", password=True)
        username = fetch_github_username(token)
        if not username:
            username = Prompt.ask("Enter your GitHub username")
        config["token"] = token
        config["username"] = username
        save_config(config)
    
    token = config["token"]
    username = config["username"]
    g = Github(auth=Auth.Token(token))

    while True:
        print_header()
        show_system_info(username)
        
        menu_q = [
            inquirer.List('action',
                          message="What would you like to do?",
                          choices=[
                              "🚀 Upload Folder to GitHub",
                              "🗑️  Delete a Repository",
                              "⚙️  Reset Authentication",
                              "🚪 Exit"
                          ],
                          carousel=True)
        ]
        ans = inquirer.prompt(menu_q)
        if not ans: break
        choice = ans['action']

        if "Exit" in choice:
            sys.exit(0)
        elif "Reset" in choice:
            if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
            print_success("Configuration reset! Restart the script.")
            sys.exit(0)
        elif "Delete" in choice:
            delete_repository(g)
            input("\nPress Enter to return...")
            continue
            
        # --- UPLOAD FLOW ---
        while True: # Repo selection loop
            try:
                user = g.get_user()
                with console.status("[blue]Fetching your repositories...[/blue]"):
                    existing_repos = [repo.name for repo in user.get_repos()]
                
                repo_choices = ["✨ Create New Repository"] + sorted(existing_repos) + ["🔙 Back to Main Menu"]
                repo_q = [inquirer.List('repo', message="Select repository", choices=repo_choices, carousel=True)]
                repo_ans = inquirer.prompt(repo_q)
                if not repo_ans or "Back" in repo_ans['repo']: break
                
                repo_name = repo_ans['repo']
                if repo_name == "✨ Create New Repository":
                    repo_name = Prompt.ask("\n📦 Enter new repository name")
                
                # Folder selection loop
                while True:
                    current_dirs = [d for d in os.listdir('.') if os.path.isdir(d) and not d.startswith('.')]
                    folder_choices = ["📁 Manual Entry / Search", "🔙 Back to Repo Selection"] + sorted(current_dirs)
                    
                    folder_q = [inquirer.List('folder', message="Select folder", choices=folder_choices, carousel=True)]
                    folder_ans = inquirer.prompt(folder_q)
                    if not folder_ans or "Back" in folder_ans['folder']: break
                    
                    folder_selection = folder_ans['folder']
                    folder_path = None
                    
                    if "Manual Entry" in folder_selection:
                        setup_tab_completion()
                        console.print("\n[bold cyan]📁 Enter path (Press TAB to autocomplete):[/bold cyan]")
                        try: folder_input = input("> ").strip()
                        except EOFError: break
                        if os.path.exists(folder_input): folder_path = os.path.abspath(folder_input)
                        else: folder_path = auto_detect_folder(folder_input)
                    else:
                        folder_path = os.path.abspath(folder_selection)
                        
                    if not folder_path or not os.path.isdir(folder_path):
                        print_error("Invalid directory.")
                        continue
                    
                    # Final settings
                    vis_q = [inquirer.List('visibility', message="Visibility", choices=['Public', 'Private'], default='Public')]
                    vis_ans = inquirer.prompt(vis_q)
                    is_public = vis_ans['visibility'] == "Public"
                    commit_msg = Prompt.ask("Enter commit message", default="Upload via Auto Uploader")
                    
                    # Execute
                    try:
                        repo_exists = False
                        try:
                            repo = user.get_repo(repo_name)
                            repo_exists = True
                            print_success(f"Targeting: {repo_name}")
                            
                            archive_q = [inquirer.List('archive', message="Archive current remote as Release?", choices=['Yes', 'No'], default='No')]
                            arc_ans = inquirer.prompt(archive_q)
                            if arc_ans and arc_ans['archive'] == 'Yes':
                                create_archive_release(repo)
                        except UnknownObjectException:
                            print_step(f"Creating new repository: {repo_name}...")
                            repo = user.create_repo(repo_name, private=not is_public)
                        
                        repo_url = f"https://{token}@github.com/{username}/{repo_name}.git"
                        if setup_git_and_push(folder_path, repo_url, commit_msg):
                            print_success(f"Upload Complete: https://github.com/{username}/{repo_name}")
                            input("\nPress Enter to return...")
                            return main() # Full reset
                    except Exception as e:
                        print_error(f"Error: {str(e)}")
                        input("\nPress Enter to return...")
                    break # Break folder loop
                break # Break repo loop
            except Exception as e:
                print_error(f"Session error: {str(e)}")
                break

if __name__ == "__main__":
    main()
