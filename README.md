# GitHub Auto Uploader Pro

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)
[![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Latest Release](https://img.shields.io/github/v/release/Mr-Risov/GitHub-Auto-Uploader)](https://github.com/Mr-Risov/GitHub-Auto-Uploader/releases/latest)

## Overview

GitHub Auto Uploader Pro is a professional Python-based automation tool designed to streamline uploading local folders to GitHub repositories and downloading existing GitHub repositories to your device. It features an intuitive command-line interface with enhanced selection menus supporting keyboard navigation (including up/down arrows), robust validation, error handling, and cross-platform compatibility. The tool is built to work seamlessly on Windows, Linux, macOS, and other Python-supported environments.

Key enhancements include:
- **Professional UI**: Selection options use arrow key navigation (up/down) for intuitive menu traversal, with Enter to confirm. This is powered by the `inquirer` library, ensuring smooth operation across terminals.
- **Cross-Device Support**: Tested for compatibility on desktop OS (Windows, Linux, macOS). Mobile support is limited due to Python script nature but possible via Termux (Android) or similar environments.
- **Secure and Efficient**: Automatic token validation, secure config storage, and smart file handling.
- **Release Information**: Shows the selected repository's latest release number, title, and message before an upload.
- **Structured Release Messages**: Archive releases record new functions and bug fixes in separate sections.

## Current Architecture

The application is divided by responsibility instead of keeping all code in one script:

```text
github_uploader.py                     # Small executable entry point
github_auto_uploader/
├── app.py                             # Application flow and repository operations
├── core/
│   └── settings.py                    # Paths and upstream repository settings
├── services/
│   ├── security.py                    # Secret scanning, redaction, and recovery
│   └── updater.py                     # Release checks and safe Git updates
└── ui/
    ├── menu.py                        # Arrow/Enter selection and Q/R shortcuts
    └── renderer.py                    # Responsive terminal box renderer
```

Release numbers and notes are not embedded in the Python source. At startup and when refreshing, the app fetches the latest release and upstream commit from `Mr-Risov/GitHub-Auto-Uploader` through the GitHub API.

Updates are never forced over local work. Installation is allowed only when the worktree is clean and the upstream change can be applied as a fast-forward. Diverged or locally modified checkouts remain untouched.



## Features

- **Authentication & Security**:
  - **One-Time Setup**: Prompts for your GitHub token on the first run and automatically fetches your username.
  - **Masked Token Entry**: Token input displays `★` characters while typing or pasting.
  - **Multi-Account Support**: Save multiple GitHub accounts and switch between them from the main menu.
  - **Local Config Storage**: Credentials are saved in `config.json` for subsequent uses.
  - **Session-Based Uploads**: Every run asks for a repository name and folder path/name, ensuring flexibility.
  - **Push Protection**: Scans for known token, cloud-key, and private-key patterns before committing.
  - **Credential Redaction**: Authentication tokens are removed from logs and are never stored in the repository's `origin` URL.

- **Smart File Management**:
  - **Tab Completion**: Supports real-time folder/path autocompletion using the **TAB** key.
  - **Auto-Detect Folder**: If you provide just a folder name instead of a full path, the tool will automatically search your system to locate it.
  - **Git Automation**: Automatically initializes Git, handles `.gitkeep` for empty folders, commits changes, and performs a force-push to the `main` branch.
  - **Repository Download**: Select one of your GitHub repositories and clone it to a local destination folder. If the repo already exists locally, the tool can pull the latest changes.
  - **Repository Search**: Search repository names case-insensitively before upload, download, or deletion.

- **Professional UI**:
  - Consistent colors, spacing, headings, panels, and interactive prompts using `rich` and `inquirer`.
  - Compact session dashboard and navigation help designed for desktop and Termux terminals.
  - Responsive borders, labels, paths, and release cards that adapt to the current terminal width.
  - Real-time progress bars for Git operations.
  - Detailed logging to `upload.log`.
  - Displays application and repository release information in dedicated panels.
  - Supports **Q** to quit, **R** to refresh update information, and arrow keys plus Enter for selection.

- **Automatic Update Checks**:
  - Fetches the latest upstream release tag, title, notes, publication time, and commit.
  - Distinguishes up-to-date, local-ahead, update-available, diverged, unmanaged, and offline states.
  - Applies updates only through a clean, fast-forward-only Git workflow.

- **GitHub Releases**:
  - Displays the latest release number, title, and message for an existing repository.
  - Fetches existing releases and tags before archiving, then suggests the next unused numeric version.
  - Optionally archives the current remote state before uploading new content.
  - Generates release notes with dedicated `New Functions` and `Bug Fixes` sections.

## Installation

### Prerequisites
- Python 3.8 or higher.
- Git version control system.

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/Mr-Risov/GitHub-Auto-Uploader.git
   cd GitHub-Auto-Uploader
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Termux Installation

PyNaCl must use Termux's system libsodium package because standard PyPI wheels are not available for Android:

```bash
pkg install libsodium clang make pkg-config libffi
source "$HOME/myenv/bin/activate"
SODIUM_INSTALL=system python -m pip install -r requirements.txt
```

## Usage

1. **Launch the Tool**:
   ```bash
   python github_uploader.py
   ```
2. **First-Time Setup**: Enter your GitHub Personal Access Token when prompted. The tool will attempt to fetch your username automatically.
3. **Choose an Action**:
   - **Upload Folder to GitHub**: Create or update a GitHub repository from a local folder.
   - **Download Repository from GitHub**: Clone one of your GitHub repositories to your device.
   - **Delete a Repository**: Delete one of your GitHub repositories after confirmation.
   - **Switch GitHub Account**: Select a saved account or add a new GitHub token.
   - **Check for Updates**: Refresh upstream metadata and safely install a compatible update.
4. **Upload Flow**: Enter the name of the GitHub repository you wish to upload to.
5. **Select Folder/Path**:
   - Type the path to your folder and press **TAB** to autocomplete.
   - Or, just enter the folder name (e.g., `my-project`), and the tool will search your system for it.
6. **Review Release**: For an existing repository, review its latest release number and message, then optionally create an archive release with new-function and bug-fix notes.
7. **Finalize Upload**: Choose visibility (Public/Private) and enter a commit message.
8. **Download Flow**: Select a repository, then enter a destination folder. Leave the destination blank to clone into the current directory.

### Keyboard Navigation
- In selection menus:
  - **Up Arrow**: Move to previous option.
  - **Down Arrow**: Move to next option.
  - **Enter**: Confirm selection.
  - **Q**: Quit immediately from the main menu.
  - **R**: Refresh the upstream release and update status.
This logic is handled by the custom `inquirer` renderer in `github_auto_uploader/ui/menu.py`.

When selecting a repository:

- Press **/** or **S** to enter a repository-name search.
- Press **R** to clear the current repository filter.
- Press **Q** to return to the previous screen.
- Continue using **↑/↓** and **Enter** to select a filtered result.

### Responsive Display

All application panels use the shared `render_box(title, lines, width=None)` helper in `github_auto_uploader/ui/renderer.py`. The helper calls `shutil.get_terminal_size()` on every render and tracks `SIGWINCH` resize events instead of caching the startup dimensions. Each box uses `min(terminal width - margin, maximum box width)`, and its content is rewrapped for that exact width.

At 40 columns or wider, panels retain their normal padding. Below 40 columns, decorative padding is removed first; below 20 columns, borders are removed and the actual content continues wrapping rather than being truncated. The UI keeps sharp box-drawing corners, a dark background, and `#00FFFF` cyan accents at every supported width. Font size remains controlled by the terminal application; changing the font or window dimensions changes the measured terminal width used by the next render.

## Configuration Files
- `config.json`: Local config containing saved GitHub account usernames and tokens. This file is ignored by Git.
- `upload.log`: Local upload log file. This file is ignored by Git.



## Troubleshooting
- **Git Not Found**: Ensure Git is installed and in PATH.
- **Internet Issues**: Tool checks connectivity; retry if failed.
- **Token Invalid**: Regenerate and update config.
- **Cross-Device Errors**: On mobile, ensure terminal supports ANSI (e.g., Termux).
- **GH013 / Push Protection**: An existing `.gitignore` protects future commits but does not erase secrets from older commits. The CLI identifies paths that are already ignored, keeps every local project file, and can replace only the local `.git` history after explicit confirmation. Revoke or rotate any real credential that appeared in Git history.

## Security Notes
- Generate tokens at [github.com/settings/tokens](https://github.com/settings/tokens) with `repo` scope.
- `config.json` stores GitHub tokens locally so account switching can work. Do not commit, share, or upload this file.
- If you accidentally expose a token, revoke it immediately in your GitHub settings and create a new one.

## Contributing
Fork the repo, make changes, and submit a pull request. Follow standard Git workflow.

## License
MIT License. See [LICENSE](LICENSE) for details.

## Acknowledgments
Built with open-source libraries: Rich, PyGithub, Inquirer, and more.
