import os
import sys
import subprocess
import json
import platform
import webbrowser
import urllib.request
import time
import zipfile
import requests
import inquirer
import logging
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.progress import track, Progress, BarColumn, TextColumn, TimeRemainingColumn, SpinnerColumn
from rich.table import Table
from rich import print
from rich.box import ROUNDED, MINIMAL
from github import Github
from github import Auth

console = Console()

CONFIG_FILE = "config.json"
LOG_FILE = "upload.log"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

def log(message, level=logging.INFO):
    """Enhanced logging function"""
    logging.log(level, message)
    # Also write to legacy log file for backward compatibility
    with open(LOG_FILE, "a") as f:
        f.write(f"[{time.ctime()}] {message}\n")

def log_debug(message):
    """Log debug messages"""
    log(f"DEBUG: {message}", logging.DEBUG)

def log_error(message):
    """Log error messages"""
    log(f"ERROR: {message}", logging.ERROR)

def log_warning(message):
    """Log warning messages"""
    log(f"WARNING: {message}", logging.WARNING)

def check_git_installed():
    log_debug("Checking if Git is installed...")
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, text=True, check=True)
        log_debug(f"Git version: {result.stdout.strip()}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        log_error("Git is not installed")
        console.print("[bold red]❌ Git is not installed. Please install Git first.[/bold red]")
        sys.exit(1)

def check_internet():
    log_debug("Checking internet connectivity...")
    try:
        urllib.request.urlopen("https://github.com", timeout=5)
        log_debug("Internet connection verified")
    except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
        log_error(f"No internet connection: {str(e)}")
        console.print(f"[red]❌ No internet connection: {str(e)}. Please check and try again.[/red]")
        sys.exit(1)

def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

def log(message, level=logging.INFO):
    """Enhanced logging function"""
    logging.log(level, message)
    # Also write to legacy log file for backward compatibility
    with open(LOG_FILE, "a") as f:
        f.write(f"[{time.ctime()}] {message}\n")

def log_debug(message):
    """Log debug messages"""
    log(f"DEBUG: {message}", logging.DEBUG)

def log_error(message):
    """Log error messages"""
    log(f"ERROR: {message}", logging.ERROR)

def log_warning(message):
    """Log warning messages"""
    log(f"WARNING: {message}", logging.WARNING)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    # Create a copy of the config to avoid modifying the original dict
    config_to_save = config.copy()
    # Remove sensitive and transient data from the config before saving
    for key in ['token', 'repo_name', 'folder_path', 'is_public', 'commit_msg']:
        if key in config_to_save:
            del config_to_save[key]
    with open(CONFIG_FILE, "w") as f:
        json.dump(config_to_save, f, indent=4)

def run_command(command, cwd=None):
    result = subprocess.run(command, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        console.print(Panel(
            f"[bold red]❌ Error running: {' '.join(command)}[/bold red]\n\n"
            f"[bright_red]{result.stderr.strip()}[/bright_red]",
            box=ROUNDED,
            border_style="bright_red"
        ))
    else:
        # Only show success for important commands, not all of them to avoid clutter
        important_commands = ["git push", "git commit", "git clone", "git init"]
        if any(cmd in " ".join(command) for cmd in important_commands):
            console.print(f"[green]✅ Successfully executed: {command[0]}[/green]")
    return result

def search_folder(input_path):
    input_path = input_path.strip().replace("  ", " ").lstrip("/\\")
    
    # Check if the input_path is a relative path that exists in current directory
    if input_path and os.path.exists(input_path):
        return os.path.abspath(input_path)
    
    # Check if input_path is referring to current directory
    if input_path == "." or input_path == os.path.basename(os.getcwd()):
        return os.getcwd()
    
    if os.name != 'nt' and "/sdcard" in input_path:
        possible_paths = [
            f"/storage/emulated/0/{input_path.split('/sdcard/')[-1]}",
            f"/sdcard/{input_path.split('/sdcard/')[-1]}"
        ]
        for p in possible_paths:
            if os.path.exists(p):
                return os.path.abspath(p)

    drives = ['C:/', 'D:/', 'E:/'] if os.name == 'nt' else ['/']
    for drive in drives:
        for root, dirs, _ in os.walk(drive):
            if input_path.lower() in root.lower():
                return os.path.abspath(root)
    return None

def create_repo(g, username, repo_name, private):
    user = g.get_user()
    try:
        repo = user.get_repo(repo_name)
        console.print(f"[yellow]✓ Repository '{repo_name}' already exists.[/yellow]")
        return repo
    except Exception as e:
        console.print(f"[yellow]⚠️  Repository '{repo_name}' creation failed or already exists: {str(e)}[/yellow]")
        try:
            repo = user.get_repo(repo_name)
            console.print(f"[yellow]✓ Repository '{repo_name}' already exists.[/yellow]")
            return repo
        except Exception as get_repo_error:
            console.print(f"[bold red]❌ Failed to access repository '{repo_name}': {str(get_repo_error)}[/bold red]")
            sys.exit(1)

def setup_git(folder, repo_url, commit_message):
    # Check if the folder exists before proceeding
    if not os.path.exists(folder):
        console.print(f"[bold red]❌ Error: Folder '{folder}' does not exist![/bold red]")
        sys.exit(1)
    
    if not os.path.isdir(folder):
        console.print(f"[bold red]❌ Error: '{folder}' is not a directory![/bold red]")
        sys.exit(1)
        
    # Check if the folder is empty
    if not os.listdir(folder):
        console.print("[yellow]⚠️  Warning: Folder is empty. Creating a placeholder file...[/yellow]")
        placeholder_file = os.path.join(folder, ".gitkeep")
        with open(placeholder_file, "w") as f:
            f.write("# Placeholder file to allow Git to track the empty directory\n")
    
    run_command(["git", "config", "--global", "--add", "safe.directory", folder])
    
    # Check if there are changes to commit
    check_changes_result = run_command(["git", "status", "--porcelain"], cwd=folder)
    has_changes = bool(check_changes_result.stdout.strip())
    
    steps = [
        (["git", "init"], "Initializing Git repository..."),
        (["git", "remote", "remove", "origin"], "Removing existing remote..."),
        (["git", "remote", "add", "origin", repo_url], "Adding remote origin..."),
        (["git", "add", "."], "Staging files..."),
        (["git", "config", "user.email", "auto@upload.bot"], "Configuring email..."),
        (["git", "config", "user.name", "GitUploaderBot"], "Configuring username...")
    ]
    
    # Only add commit step if there are changes
    if has_changes:
        steps.append((["git", "commit", "-m", commit_message], "Committing changes..."))
    else:
        console.print("[yellow]⚠️  No changes to commit, checking if we need to force push[/yellow]")
    
    steps.extend([
        (["git", "branch", "-M", "main"], "Setting main branch..."),
        (["git", "pull", "origin", "main", "--allow-unrelated-histories"], "Pulling latest changes...")
    ])
    
    # Create a progress bar for git operations
    total_steps = len(steps) + 2  # +2 for the push operations
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
    ) as progress:
        task = progress.add_task("[cyan]Performing Git Operations", total=total_steps)
        
        # Execute initial steps
        for step_cmd, step_desc in steps:
            progress.update(task, description=f"[cyan]{step_desc}", advance=1)
            result = run_command(step_cmd, cwd=folder)
            if result.returncode != 0 and "remote remove" not in " ".join(step_cmd) and "pull" not in " ".join(step_cmd) :
                # Special handling for commit command when there are no changes
                if 'commit' in step_cmd and not has_changes:
                    console.print("[yellow]⚠️  Skipping commit (no changes to commit)[/yellow]")
                    continue  # Skip commit when no changes exist
                console.print(f"[bold red]❌ Failed to execute: {' '.join(step_cmd)}[/bold red]")
                sys.exit(1)
            log(f"Executed: {' '.join(step_cmd)}")
        
        # Final push step - try normal push first, then force push if needed
        progress.update(task, description="[cyan]Pushing to GitHub...", advance=1)
        push_result = run_command(["git", "push", "-u", "origin", "main"], cwd=folder)
        
        if push_result.returncode != 0:
            # Check if the error is due to no commits existing yet
            if "does not match any" in push_result.stderr:
                console.print("[yellow]⚠️  No commits yet, attempting to push with initial commit...[/yellow]")
                # Make an initial commit and try again
                run_command(["git", "add", "."], cwd=folder)
                commit_result = run_command(["git", "commit", "-m", commit_message], cwd=folder)
                if commit_result.returncode == 0:
                    # Retry the push
                    retry_push_result = run_command(["git", "push", "-u", "origin", "main"], cwd=folder)
                    if retry_push_result.returncode == 0:
                        progress.update(task, description="[green]Push completed successfully!", advance=1)
                        console.print("\n[green]✓ Push successful![/green]")
                        return
                    else:
                        console.print(f"[bold red]❌ Failed to push after initial commit: {retry_push_result.stderr}[/bold red]")
                        sys.exit(1)
                else:
                    console.print(f"[bold red]❌ Failed to make initial commit: {commit_result.stderr}[/bold red]")
                    sys.exit(1)
            elif "non-fast-forward" in push_result.stderr or "behind its remote counterpart" in push_result.stderr:
                progress.update(task, description="[yellow]Force pushing to GitHub...", advance=1)
                force_push_result = run_command(["git", "push", "-u", "origin", "main", "--force"], cwd=folder)
                if force_push_result.returncode != 0:
                    console.print(f"[bold red]❌ Failed to push even with force: {force_push_result.stderr}[/bold red]")
                    sys.exit(1)
                else:
                    console.print("[green]✓ Force push successful![/green]")
            else:
                console.print(f"[bold red]❌ Failed to push to GitHub: {push_result.stderr}[/bold red]")
                sys.exit(1)
        else:
            progress.update(task, description="[green]Push completed successfully!", advance=1)
            console.print("\n[green]✓ Push successful![/green]")
    
    log("Git operations completed: push to GitHub")

def extract_if_zip(path):
    if path.endswith(".zip") and os.path.exists(path):
        questions = [inquirer.List('choice',
                                  message="Detected a zip file. Do you want to extract it?",
                                  choices=['Yes', 'No'],
                                  default='Yes')]
        answers = inquirer.prompt(questions)
        if answers and answers['choice'] == 'Yes':
            extract_folder = os.path.splitext(path)[0]
            with zipfile.ZipFile(path, 'r') as zip_ref:
                zip_ref.extractall(extract_folder)
            console.print(f"[green]✓ Extracted to: {extract_folder}[/green]")
            return extract_folder
    return path

def prompt_update_config(config):
    updated = False
    for key in ["username", "repo_name", "folder_path", "is_public", "commit_msg"]:
        current_value = config.get(key)
        update_choice, _ = selection_handler.select_option(
            options=["Yes", "No"],
            message=f"Do you want to update {key}?",
            default_index=1  # Default to No
        )
        
        if update_choice == "Yes":
            if key == "is_public":
                new_value = selection_handler.select_visibility("New repository visibility")
            else:
                new_value = Prompt.ask(f"Enter new value for {key}", default=str(current_value) if current_value else None)
            config[key] = new_value
            updated = True
    return updated

def validate_token(token):
    """Validate GitHub token format"""
    if not token or not isinstance(token, str):
        return False, "Token must be a non-empty string"
    
    # Basic format validation (GitHub tokens usually start with 'ghp_' or 'github_pat_')
    if not (token.startswith('ghp_') or token.startswith('github_pat_') or len(token) >= 40):
        console.print("[yellow]⚠️  Token format looks unusual, but proceeding anyway...[/yellow]")
    
    return True, "Valid token format"

def validate_username(username):
    """Validate GitHub username"""
    if not username or not isinstance(username, str):
        return False, "Username must be a non-empty string"
    
    if not username.replace('-', '').replace('_', '').isalnum():
        return False, "Username contains invalid characters"
    
    if len(username) > 39:
        return False, "Username too long (max 39 characters)"
    
    return True, "Valid username"

def validate_repo_name(repo_name):
    """Validate repository name"""
    if not repo_name or not isinstance(repo_name, str):
        return False, "Repository name must be a non-empty string"
    
    # Check for invalid characters
    invalid_chars = [' ', '~', '^', ':', '?', '*', '[', ']', '@', '{', '}', '\\']
    if any(char in repo_name for char in invalid_chars):
        return False, f"Repository name contains invalid characters: {', '.join([char for char in invalid_chars if char in repo_name])}"
    
    if len(repo_name) > 100:
        return False, "Repository name too long (max 100 characters)"
    
    if repo_name.startswith('.') or repo_name.endswith('.git'):
        return False, "Repository name cannot start with '.' or end with '.git'"
    
    return True, "Valid repository name"

def sanitize_path(path):
    """Sanitize and validate file path"""
    if not path or not isinstance(path, str):
        return None, "Path must be a non-empty string"
    
    # Normalize path
    path = os.path.normpath(path.strip())
    
    # Prevent directory traversal attacks
    if '..' in path.split(os.sep):
        return None, "Path contains directory traversal sequences"
    
    # Check if path is absolute and convert if needed
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    
    return path, "Valid path"

def auto_detect_folder(folder_name):
    """Automatically detect a folder by name in the system"""
    if os.name == 'nt':
        # On Windows, check common drives
        drives = [f"{chr(drive)}:\\" for drive in range(ord('C'), ord('Z') + 1) if os.path.exists(f"{chr(drive)}:\\")]
    else:
        # On Unix-like systems, start from root
        drives = ['/']

    for drive in drives:
        for root, dirs, _ in os.walk(drive):
            if folder_name in dirs:
                return os.path.join(root, folder_name)
    return None

def validate_and_sanitize_inputs(config):
    """Validate and sanitize all configuration inputs"""
    errors = []
    
    # Validate username
    if 'username' in config:
        is_valid, msg = validate_username(config['username'])
        if not is_valid:
            errors.append(f"Username validation error: {msg}")
    
    # Validate repository name
    if 'repo_name' in config:
        is_valid, msg = validate_repo_name(config['repo_name'])
        if not is_valid:
            errors.append(f"Repository name validation error: {msg}")
    
    # Validate folder path
    if 'folder_path' in config:
        sanitized_path, msg = sanitize_path(config['folder_path'])
        if sanitized_path is None:
            errors.append(f"Folder path validation error: {msg}")
        else:
            config['folder_path'] = sanitized_path
    
    return errors

def fetch_github_user_info(token):
    """Fetch user information from GitHub API using the provided token"""
    try:
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHub-Uploader'
        }
        response = requests.get('https://api.github.com/user', headers=headers, timeout=10)
        
        if response.status_code == 200:
            user_data = response.json()
            return {
                'login': user_data.get('login'),
                'id': user_data.get('id'),
                'name': user_data.get('name'),
                'email': user_data.get('email'),
                'bio': user_data.get('bio'),
                'company': user_data.get('company'),
                'location': user_data.get('location'),
                'public_repos': user_data.get('public_repos'),
                'followers': user_data.get('followers'),
                'following': user_data.get('following'),
                'created_at': user_data.get('created_at')
            }
        elif response.status_code == 401:
            console.print("[red]❌ Invalid GitHub token. Please check your token and try again.[/red]")
            return None
        elif response.status_code == 403:
            console.print("[red]❌ GitHub API rate limit exceeded or insufficient permissions.[/red]")
            return None
        else:
            console.print(f"[red]⚠️  Could not fetch user info: {response.status_code} - {response.text}[/red]")
            return None
    except requests.exceptions.Timeout:
        console.print("[red]⚠️  Request timed out. Please check your internet connection.[/red]")
        return None
    except requests.exceptions.ConnectionError:
        console.print("[red]⚠️  Connection error. Please check your internet connection.[/red]")
        return None
    except requests.exceptions.RequestException as e:
        console.print(f"[red]⚠️  Request error: {str(e)}[/red]")
        return None
    except Exception as e:
        console.print(f"[red]⚠️  Unexpected error fetching user info: {str(e)}[/red]")
        return None

class SelectionHandler:
    """Enhanced selection handler with consistent UX and advanced features"""
    
    def __init__(self):
        self.console = Console()

    def select_option(self, options, message, default_index=0, allow_custom=False, custom_prompt=None):
        if not options:
            raise ValueError("Options list cannot be empty")

        if allow_custom:
            options.append("Custom Input")

        questions = [
            inquirer.List('choice',
                          message=message,
                          choices=options,
                          default=options[default_index] if default_index < len(options) else None,
                          carousel=True)
        ]
        
        try:
            answers = inquirer.prompt(questions)
            if answers:
                choice = answers['choice']
                if choice == "Custom Input":
                    return Prompt.ask(custom_prompt or "Enter custom value"), "custom"
                return choice, "selected"
            else:
                # User cancelled the prompt (e.g., with Ctrl+C)
                return None, "cancelled"
        except Exception as e:
            self.console.print(f"[red]❌ Error during selection: {str(e)}[/red]")
            # Fallback to simple text input
            return Prompt.ask(message), "fallback"
    
    def confirm_action(self, message, default=True):
        """Enhanced confirmation dialog"""
        default_text = "Y/n" if default else "y/N"
        while True:
            try:
                choice = Prompt.ask(f"{message} [{default_text}]", default="y" if default else "n").lower().strip()
                if choice in ['', 'y', 'yes']:
                    return True
                elif choice in ['n', 'no']:
                    return False
                else:
                    self.console.print("[red]Please enter 'y' for yes or 'n' for no[/red]")
            except KeyboardInterrupt:
                return False
    
    def select_visibility(self, message="Repository visibility", default_public=True):
        """Specialized visibility selection"""
        options = ["Public", "Private"]
        default_index = 0 if default_public else 1
        
        selected, _ = self.select_option(
            options=options,
            message=message,
            default_index=default_index
        )
        
        return selected == "Public"
    

# Global selection handler instance
selection_handler = SelectionHandler()

def main():
    clear_terminal()
    
    # Professional header with branding
    console.print(Panel(
        "[bold blue]🚀 GITHUB AUTO UPLOADER PRO[/bold blue]\n"
        "[dim]Professional Repository Management Tool[/dim]\n"
        "[bright_black]Version 2.0 | Secure • Reliable • Efficient[/bright_black]",
        box=ROUNDED,
        padding=(1, 2),
        border_style="bright_blue"
    ))
    
    # System checks with progress indication
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True
    ) as progress:
        task = progress.add_task(description="Checking system requirements...", total=None)
        
        check_git_installed()
        check_internet()
        
        progress.update(task, description="System requirements verified! ✅")
        time.sleep(0.5)  # Brief pause for visual effect
    
    console.print("\n[i]Initializing upload process...[/i]\n", style="bold yellow")

    config = load_config()
    token = os.environ.get("GITHUB_TOKEN")

    # For first-time setup (no config), prioritize authentication setup first
    if not token:
        console.print("\n[bold cyan]🔐 Initial Authentication Setup[/bold cyan]")
        token = Prompt.ask("Enter GitHub token (or 'h' for help)", password=True)
        if token.lower() == 'h':
            webbrowser.open("https://github.com/settings/tokens")
            token = Prompt.ask("Paste your GitHub token", password=True)

    # Fetch user information automatically
    console.print("\n[blue]🔍 Fetching user information...[/blue]")
    user_info = fetch_github_user_info(token)
    if user_info:
        username = user_info['login']  # Use the fetched username
        console.print(f"[green]✅ Logged in as: {username}[/green]")
        console.print(f"[dim]Name: {user_info['name'] or 'Not provided'}[/dim]")
    else:
        # Fallback to manual entry if API call fails
        console.print("[red]❌ Could not fetch user info from token. Please enter your GitHub username.[/red]")
        username = Prompt.ask("Enter GitHub username")

    # Add token to config for in-memory use (it will be stripped before saving)
    config['token'] = token
    
    # For first time, store only authentication info initially
    config.update({
        "username": username,
        "user_info": user_info
    })
    save_config(config)
    console.print("[green]✓ Authentication configured. Now specify repository and folder for upload.[/green]")
    
    # Now check if we're looking for a specific folder (rat-tg) only if no folder_path was set yet
    auto_detected_path = auto_detect_folder("rat-tg")
    if auto_detected_path and not config.get("folder_path"):  # Only auto-detect if no folder was previously set
        table = Table(box=MINIMAL, show_header=False)
        table.add_column(style="bold green")
        table.add_column(style="white")
        table.add_row("📁 Detected Folder:", f"[green]{auto_detected_path}[/green]")
        table.add_row("📦 Repository:", "[blue]Rat-to-tg[/blue]")
        console.print(table)
        
        # Use enhanced selection handler
        proceed, _ = selection_handler.select_option(
            options=["Yes", "No"],
            message="Would you like to proceed with uploading this folder?",
            default_index=0
        )
        
        if proceed == "Yes":
            # Set defaults for rat-tg upload
            folder_path = auto_detected_path
            repo_name = "Rat-to-tg"  # Default repo name for rat-tg
            console.print(f"\n[blue]📝 Repository name set to: {repo_name}[/blue]")
            
            # Ask if they want to use the default repo name or enter a different one
            use_default, _ = selection_handler.select_option(
                options=["Yes", "No"],
                message=f"Use repository name '{repo_name}'?",
                default_index=0,
                allow_custom=True,
                custom_prompt="Enter repository name:"
            )
            
            if use_default == "No":
                repo_name = Prompt.ask("Enter repository name")
                
            is_public = selection_handler.select_visibility("Upload as public repo?")
            commit_msg = Prompt.ask("Enter commit message", default="Upload by bot")

            # Update config with upload-specific details
            config.update({
                "repo_name": repo_name,
                "folder_path": folder_path,
                "is_public": is_public,
                "commit_msg": commit_msg
            })
            console.print("\n[green]✓ Upload configuration set for this session![/green]")
        else:
            # User chose not to use auto-detected folder, ask for folder manually
            console.print("\n[blue]🔄 Manual Configuration Mode[/blue]")
            repo_name = Prompt.ask("Enter repository name")
            folder = Prompt.ask("Enter folder path to upload (or .zip file)")
            folder_path = search_folder(folder)
            while not folder_path or not os.path.exists(folder_path):
                console.print(f"[red]❌ Path '{folder}' not found on your system![/red]")
                folder = Prompt.ask("Enter folder path to upload")
                folder_path = search_folder(folder)

            folder_path = extract_if_zip(folder_path)
            is_public = selection_handler.select_visibility()
            commit_msg = Prompt.ask("Enter commit message", default="Upload by bot")

            # Update config with upload-specific details
            config.update({
                "repo_name": repo_name,
                "folder_path": folder_path,
                "is_public": is_public,
                "commit_msg": commit_msg
            })
            console.print("\n[green]✓ Upload configuration set for this session![/green]")
    else:
        # Normal flow when config exists or auto-detection is skipped
        if not config.get("repo_name") or not config.get("folder_path"):
            # Missing essential upload info, ask for them
            console.print("\n[blue]🔄 Configuration Setup[/blue]")
            repo_name = Prompt.ask("Enter repository name")
            folder = Prompt.ask("Enter folder path to upload (or .zip file)")
            folder_path = search_folder(folder)
            while not folder_path or not os.path.exists(folder_path):
                console.print(f"[red]❌ Path '{folder}' not found on your system![/red]")
                folder = Prompt.ask("Enter folder path to upload")
                folder_path = search_folder(folder)

            folder_path = extract_if_zip(folder_path)
            is_public = selection_handler.select_visibility()
            commit_msg = Prompt.ask("Enter commit message", default="Upload by bot")

            # Update config with upload-specific details
            config.update({
                "repo_name": repo_name,
                "folder_path": folder_path,
                "is_public": is_public,
                "commit_msg": commit_msg
            })
            console.print("\n[green]✓ Upload configuration set for this session![/green]")
        else:
            # Config has all required info, check if user wants to update
            console.print("\n[blue]🔄 Configuration Options[/blue]")
            update_config, _ = selection_handler.select_option(
                options=["Yes", "No"],
                message="Do you want to update existing config?",
                default_index=0
            )
            
            if update_config == "Yes":
                if prompt_update_config(config):
                    console.print("[green]✓ Config updated for this session.[/green]")
            else:
                upload_another, _ = selection_handler.select_option(
                    options=["Yes", "No"],
                    message="Do you want to upload in another repo?",
                    default_index=0
                )
                
                if upload_another == "Yes":
                    config["repo_name"] = Prompt.ask("Enter new repository name")
                    console.print("[green]✓ Repository info updated for this session.[/green]")
                else:
                    if os.path.exists(config.get("folder_path", "")):
                        existing_files = os.listdir(config["folder_path"])
                        if existing_files:
                            console.print(f"\n[yellow]📁 Files in current upload directory:[/yellow]")
                            for file in existing_files[:5]:  # Show first 5 files
                                console.print(f"  • {file}")
                            if len(existing_files) > 5:
                                console.print(f"  ... and {len(existing_files)-5} more files")
                            
                            action_choice, _ = selection_handler.select_option(
                                options=["Replace files", "Upload to another repo"],
                                message="What would you like to do?",
                                default_index=0
                            )
                            
                            if action_choice == "Upload to another repo":
                                config["repo_name"] = Prompt.ask("Enter new repository name")
                                save_config(config)

    # Display upload summary
    console.print("\n", end="")
    
    # Build user info section if available
    username = config.get('username', 'Unknown User')
    user_info_section = f"[white]Username:[/white] [green]{username}[/green]"
    if config.get('user_info'):
        user_info = config['user_info']
        user_details = f"\n[white]User Details:[/white] [dim]{user_info.get('name', 'No name')} ({user_info.get('login', 'unknown')})[/dim]"
        if user_info.get('company'):
            user_details += f"\n[white]Company:[/white] [dim]{user_info['company']}[/dim]"
        if user_info.get('location'):
            user_details += f"\n[white]Location:[/white] [dim]{user_info['location']}[/dim]"
        if user_info.get('email'):
            user_details += f"\n[white]Email:[/white] [dim]{user_info['email']}[/dim]"
        user_info_section += user_details
    
    console.print(Panel(
        f"[bold cyan]📤 UPLOAD SUMMARY[/bold cyan]\n\n"
        f"[white]Repository:[/white] [blue]{config['repo_name']}[/blue]\n"
        f"{user_info_section}\n"
        f"[white]Folder:[/white] [yellow]{config['folder_path']}[/yellow]\n"
        f"[white]Visibility:[/white] {'[green]Public[/green]' if config['is_public'] else '[red]Private[/red]'}\n"
        f"[white]Commit Message:[/white] [magenta]{config['commit_msg']}[/magenta]",
        box=ROUNDED,
        border_style="bright_yellow"
    ))
    
    # Use enhanced confirmation
    proceed = selection_handler.confirm_action("Proceed with upload?", default=True)
    
    if proceed:
        token = config["token"]
        username = config["username"]
        repo_name = config["repo_name"]
        folder_path = config["folder_path"]
        is_public = config["is_public"]
        commit_msg = config["commit_msg"]

        folder_path = extract_if_zip(folder_path)
        g = Github(auth=Auth.Token(token))
        repo = create_repo(g, username, repo_name, not is_public)
        repo_url = f"https://{token}@github.com/{username}/{repo_name}.git"
        setup_git(folder_path, repo_url, commit_msg)

        console.print(Panel(
            "[bold green]✅ SUCCESS![/bold green]\n\n"
            "[white]Files have been uploaded to GitHub successfully![/white]\n\n"
            f"[bright_black]Repository: {username}/{repo_name}[/bright_black]",
            box=ROUNDED,
            border_style="bright_green"
        ))
        log("Upload complete.")
    else:
        console.print("[yellow]Upload cancelled by user.[/yellow]")

if __name__ == "__main__":
    main()