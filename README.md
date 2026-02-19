# GitHub Auto Uploader Pro

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)
[![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)

## Overview

GitHub Auto Uploader Pro is a professional Python-based automation tool designed to streamline the upload of local folders and files to GitHub repositories. It features an intuitive command-line interface with enhanced selection menus supporting keyboard navigation (including up/down arrows), robust validation, error handling, and cross-platform compatibility. The tool is built to work seamlessly on Windows, Linux, macOS, and other Python-supported environments.

Key enhancements include:
- **Professional UI**: Selection options use arrow key navigation (up/down) for intuitive menu traversal, with Enter to confirm. This is powered by the `inquirer` library, ensuring smooth operation across terminals.
- **Cross-Device Support**: Tested for compatibility on desktop OS (Windows, Linux, macOS). Mobile support is limited due to Python script nature but possible via Termux (Android) or similar environments.
- **Secure and Efficient**: Automatic token validation, secure config storage, and smart file handling.



## Features

- **Authentication & Security**:
  - **One-Time Setup**: Securely prompts for your GitHub token on the first run and automatically fetches your username.
  - **Secure Storage**: Credentials are saved in `config.json` for subsequent uses.
  - **Session-Based Uploads**: Every run asks for a repository name and folder path/name, ensuring flexibility.

- **Smart File Management**:
  - **Tab Completion**: Supports real-time folder/path autocompletion using the **TAB** key.
  - **Auto-Detect Folder**: If you provide just a folder name instead of a full path, the tool will automatically search your system to locate it.
  - **Git Automation**: Automatically initializes Git, handles `.gitkeep` for empty folders, commits changes, and performs a force-push to the `main` branch.

- **Professional UI**:
  - Interactive prompts using `rich` and `inquirer`.
  - Real-time progress bars for Git operations.
  - Detailed logging to `upload.log`.

## Installation

### Prerequisites
- Python 3.8 or higher.
- Git version control system.

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/Mr-Risov/github-auto-uploader-pro.git
   cd github-auto-uploader-pro
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Launch the Tool**:
   ```bash
   python github_uploader.py
   ```
2. **First-Time Setup**: Enter your GitHub Personal Access Token when prompted. The tool will attempt to fetch your username automatically.
3. **Specify Repository**: Enter the name of the GitHub repository you wish to upload to.
4. **Select Folder/Path**:
   - Type the path to your folder and press **TAB** to autocomplete.
   - Or, just enter the folder name (e.g., `my-project`), and the tool will search your system for it.
5. **Finalize**: Choose visibility (Public/Private) and enter a commit message.

### Keyboard Navigation
- In selection menus:
  - **Up Arrow**: Move to previous option.
  - **Down Arrow**: Move to next option.
  - **Enter**: Confirm selection.
  - Shortcuts (e.g., 'q' for quit) are also supported.
This logic is handled professionally via `inquirer` and `keyboard` libraries, ensuring responsiveness across devices.

## Configuration Files
- `config.json`: Primary config with username, repo, and visibility. The GitHub token is not stored in this file.



## Troubleshooting
- **Git Not Found**: Ensure Git is installed and in PATH.
- **Internet Issues**: Tool checks connectivity; retry if failed.
- **Token Invalid**: Regenerate and update config.
- **Cross-Device Errors**: On mobile, ensure terminal supports ANSI (e.g., Termux).

## Security Notes
- It is highly recommended to use the `GITHUB_TOKEN` environment variable to provide your GitHub token, especially in production or automated environments.
- Generate tokens at [github.com/settings/tokens](https://github.com/settings/tokens) with `repo` scope.
- Avoid sharing your environment variables or exposing them in your shell's history.

## Contributing
Fork the repo, make changes, and submit a pull request. Follow standard Git workflow.

## License
MIT License. See [LICENSE](LICENSE) for details.

## Acknowledgments
Built with open-source libraries: Rich, PyGithub, Inquirer, and more.