#!/usr/bin/env bash
# ==============================================================================
# GitHub Auto Uploader Pro - Universal Advanced Installer
# Supports: Linux (Debian, Ubuntu, Kali, Arch Linux, Fedora, CentOS, openSUSE, Alpine),
#           Android Termux, macOS, and POSIX environments.
# ==============================================================================

set -e

REPO_URL="https://github.com/Mr-Risov/GitHub-Auto-Uploader.git"
INSTALL_DIR="${HOME}/.Github-Auto-Uploader"
SCRIPT_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"

echo "============================================================"
echo "🚀 GITHUB AUTO UPLOADER PRO - UNIVERSAL INSTALLER"
echo "============================================================"

# ------------------------------------------------------------------------------
# 1. OS & Environment Detection
# ------------------------------------------------------------------------------
OS_NAME="$(uname -s 2>/dev/null || echo "Unknown")"
IS_TERMUX=0
IS_MAC=0
IS_LINUX=0

if [ -n "$TERMUX_VERSION" ] || [ -d "/data/data/com.termux" ]; then
    IS_TERMUX=1
    echo "[✓] Environment: Android Termux"
elif [ "$OS_NAME" = "Darwin" ]; then
    IS_MAC=1
    echo "[✓] Environment: macOS ($OS_NAME)"
else
    IS_LINUX=1
    echo "[✓] Environment: Linux ($OS_NAME)"
fi

# Detect package manager
SUDO_CMD=""
if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then
    SUDO_CMD="sudo"
fi

install_packages() {
    echo "==> Ensuring required system packages are installed..."
    if [ "$IS_TERMUX" -eq 1 ]; then
        pkg update -y || true
        pkg install -y git python python-pip libsodium clang make pkg-config libffi || true
    elif command -v apt-get >/dev/null 2>&1; then
        $SUDO_CMD apt-get update -y || true
        $SUDO_CMD apt-get install -y git python3 python3-venv python3-pip build-essential || true
    elif command -v pacman >/dev/null 2>&1; then
        $SUDO_CMD pacman -Sy --noconfirm git python python-pip python-virtualenv base-devel || true
    elif command -v dnf >/dev/null 2>&1; then
        $SUDO_CMD dnf install -y git python3 python3-pip python3-virtualenv gcc gcc-c++ make || true
    elif command -v yum >/dev/null 2>&1; then
        $SUDO_CMD yum install -y git python3 python3-pip gcc make || true
    elif command -v zypper >/dev/null 2>&1; then
        $SUDO_CMD zypper --non-interactive install git python3 python3-pip python3-virtualenv || true
    elif command -v apk >/dev/null 2>&1; then
        $SUDO_CMD apk add --no-cache git python3 py3-pip py3-virtualenv build-base libffi-dev || true
    elif [ "$IS_MAC" -eq 1 ] && command -v brew >/dev/null 2>&1; then
        brew install git python libsodium || true
    fi
}

# Check if git or python is missing
if ! command -v git >/dev/null 2>&1 || (! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1); then
    install_packages
fi

# Determine base python command
BASE_PYTHON=""
if command -v python3 >/dev/null 2>&1; then
    BASE_PYTHON="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
    BASE_PYTHON="$(command -v python)"
elif [ -x "/data/data/com.termux/files/usr/bin/python" ]; then
    BASE_PYTHON="/data/data/com.termux/files/usr/bin/python"
elif [ -x "/usr/bin/python3" ]; then
    BASE_PYTHON="/usr/bin/python3"
fi

if [ -z "$BASE_PYTHON" ]; then
    echo "[!] Python was not found. Attempting package installation..."
    install_packages
    BASE_PYTHON="$(command -v python3 || command -v python || true)"
    if [ -z "$BASE_PYTHON" ]; then
        echo "[ERROR] Python 3 is required but could not be installed automatically." >&2
        exit 1
    fi
fi
echo "[✓] Using Base Python: $BASE_PYTHON ($($BASE_PYTHON --version 2>&1))"

# ------------------------------------------------------------------------------
# 2. Setup Application Files in ~/.Github-Auto-Uploader
# ------------------------------------------------------------------------------
echo "==> Syncing GitHub Auto Uploader into $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

if [ -n "$SCRIPT_SRC" ] && [ -f "$SCRIPT_SRC/github_uploader.py" ] && [ -d "$SCRIPT_SRC/github_auto_uploader" ]; then
    echo "[✓] Copying files from local repository ($SCRIPT_SRC)..."
    cp -r "$SCRIPT_SRC/github_auto_uploader" "$INSTALL_DIR/"
    cp "$SCRIPT_SRC/github_uploader.py" "$INSTALL_DIR/"
    cp "$SCRIPT_SRC/requirements.txt" "$INSTALL_DIR/"
    cp "$SCRIPT_SRC/install.sh" "$INSTALL_DIR/" 2>/dev/null || true
    cp "$SCRIPT_SRC/LICENSE" "$INSTALL_DIR/" 2>/dev/null || true
    cp "$SCRIPT_SRC/README.md" "$INSTALL_DIR/" 2>/dev/null || true
    if [ -f "$SCRIPT_SRC/config.json" ] && [ ! -f "$INSTALL_DIR/config.json" ]; then
        cp "$SCRIPT_SRC/config.json" "$INSTALL_DIR/"
    fi
else
    echo "[✓] Downloading newest version from GitHub..."
    TMP_CLONE=$(mktemp -d 2>/dev/null || mktemp -d -t 'ghupload')
    git clone --depth 1 "$REPO_URL" "$TMP_CLONE"
    cp -r "$TMP_CLONE/github_auto_uploader" "$INSTALL_DIR/"
    cp "$TMP_CLONE/github_uploader.py" "$INSTALL_DIR/"
    cp "$TMP_CLONE/requirements.txt" "$INSTALL_DIR/"
    cp "$TMP_CLONE/install.sh" "$INSTALL_DIR/" 2>/dev/null || true
    cp "$TMP_CLONE/LICENSE" "$INSTALL_DIR/" 2>/dev/null || true
    cp "$TMP_CLONE/README.md" "$INSTALL_DIR/" 2>/dev/null || true
    rm -rf "$TMP_CLONE"
fi

# Preserve existing configuration / accounts if available
if [ ! -f "$INSTALL_DIR/config.json" ]; then
    for cand in "/data/data/com.termux/files/home/GitHub-Auto-Uploader/config.json" \
                "/data/data/com.termux/files/home/.Github-Auto-Uploader/config.json" \
                "/root/GitHub-Auto-Uploader/config.json" \
                "/root/.Github-Auto-Uploader/config.json"; do
        if [ -f "$cand" ]; then
            cp "$cand" "$INSTALL_DIR/config.json"
            echo "[✓] Preserved existing accounts and tokens from $cand"
            break
        fi
    done
fi

# ------------------------------------------------------------------------------
# 3. Virtual Environment Detection & Automatic Creation (~/myenv)
# ------------------------------------------------------------------------------
echo "==> Detecting Python virtual environment..."
MYENV_DIR=""

is_valid_venv() {
    local vpath="$1"
    [ -n "$vpath" ] && [ -d "$vpath" ] && [ -x "$vpath/bin/python" ] && [ -f "$vpath/bin/activate" ]
}

VENV_CANDIDATES=(
    "${VIRTUAL_ENV:-}"
    "${HOME}/myenv"
    "/data/data/com.termux/files/home/myenv"
    "${HOME}/.myenv"
    "${HOME}/venv"
    "${HOME}/.venv"
    "${INSTALL_DIR}/venv"
)

for cand in "${VENV_CANDIDATES[@]}"; do
    if is_valid_venv "$cand"; then
        MYENV_DIR="$cand"
        echo "[✓] Found existing virtual environment: $MYENV_DIR"
        break
    fi
done

# If no valid venv found, automatically create ~/myenv
if [ -z "$MYENV_DIR" ]; then
    MYENV_DIR="${HOME}/myenv"
    echo "==> Creating virtual environment at: $MYENV_DIR..."
    rm -rf "$MYENV_DIR"
    
    if ! "$BASE_PYTHON" -m venv "$MYENV_DIR" 2>/dev/null; then
        echo "[!] Standard venv module needed additional packages. Installing..."
        install_packages
        if ! "$BASE_PYTHON" -m venv "$MYENV_DIR" 2>/dev/null; then
            if command -v virtualenv >/dev/null 2>&1; then
                virtualenv "$MYENV_DIR"
            else
                "$BASE_PYTHON" -m pip install --user virtualenv 2>/dev/null || true
                "$BASE_PYTHON" -m virtualenv "$MYENV_DIR" 2>/dev/null || true
            fi
        fi
    fi
fi

if is_valid_venv "$MYENV_DIR"; then
    VENV_PYTHON="$MYENV_DIR/bin/python"
    VENV_PIP="$MYENV_DIR/bin/python -m pip"
    echo "[✓] Virtual environment ready: $MYENV_DIR"
else
    echo "[!] Warning: Could not create full venv in $MYENV_DIR. Falling back to base Python."
    VENV_PYTHON="$BASE_PYTHON"
    VENV_PIP="$BASE_PYTHON -m pip"
fi

# Persist venv path so github command always uses this source automatically
echo "$MYENV_DIR" > "$INSTALL_DIR/.venv_path"

# ------------------------------------------------------------------------------
# 4. Install Dependencies into the Virtual Environment
# ------------------------------------------------------------------------------
echo "==> Upgrading pip and installing requirements into virtual environment..."
$VENV_PIP install --upgrade pip setuptools wheel --quiet 2>/dev/null || true

if [ "$IS_TERMUX" -eq 1 ]; then
    SODIUM_INSTALL=system $VENV_PIP install -r "$INSTALL_DIR/requirements.txt" --quiet 2>/dev/null || \
    $VENV_PIP install -r "$INSTALL_DIR/requirements.txt" --quiet 2>/dev/null || true
else
    $VENV_PIP install -r "$INSTALL_DIR/requirements.txt" --quiet 2>/dev/null || true
fi

# Verify core dependencies
if ! "$VENV_PYTHON" -c "import requests, rich, inquirer, github" 2>/dev/null; then
    echo "==> Installing missing core dependencies..."
    $VENV_PIP install requests rich inquirer PyGithub || true
fi

# ------------------------------------------------------------------------------
# 5. Install Global 'github' Launcher & Typo Wrappers
# ------------------------------------------------------------------------------
BIN_DIRS=()
if [ -d "/data/data/com.termux/files/usr/bin" ] && [ -w "/data/data/com.termux/files/usr/bin" ]; then
    BIN_DIRS+=("/data/data/com.termux/files/usr/bin")
fi
if [ -d "/usr/local/bin" ] && [ -w "/usr/local/bin" ]; then
    BIN_DIRS+=("/usr/local/bin")
fi
mkdir -p "$HOME/.local/bin"
BIN_DIRS+=("$HOME/.local/bin")

TYPO_COMMANDS=("gthub" "gihub" "githb" "gitub" "ghub" "githup" "git-hub" "githubb" "githhub" "guthub" "githun")

for bdir in "${BIN_DIRS[@]}"; do
    echo "==> Installing launcher into $bdir/github"
    cat << 'EOF' > "$bdir/github"
#!/usr/bin/env bash
export GITHUB_UPLOADER_CWD="$(pwd -P 2>/dev/null || pwd)"

if [ -d "$HOME/.Github-Auto-Uploader" ]; then
    APP_DIR="$HOME/.Github-Auto-Uploader"
elif [ -d "/data/data/com.termux/files/home/.Github-Auto-Uploader" ]; then
    APP_DIR="/data/data/com.termux/files/home/.Github-Auto-Uploader"
elif [ -d "/root/.Github-Auto-Uploader" ]; then
    APP_DIR="/root/.Github-Auto-Uploader"
else
    APP_DIR="$HOME/.Github-Auto-Uploader"
fi

export GITHUB_UPLOADER_DIR="$APP_DIR"
export PYTHONPATH="$APP_DIR:$PYTHONPATH"

# Auto-detect and source virtual environment
VENV_PATH=""
if [ -f "$APP_DIR/.venv_path" ]; then
    VENV_PATH="$(cat "$APP_DIR/.venv_path" 2>/dev/null || true)"
fi
if [ -z "$VENV_PATH" ] || [ ! -x "$VENV_PATH/bin/python" ]; then
    for cand in "$HOME/myenv" "/data/data/com.termux/files/home/myenv" "$HOME/.myenv" "$HOME/venv" "$HOME/.venv"; do
        if [ -x "$cand/bin/python" ]; then
            VENV_PATH="$cand"
            break
        fi
    done
fi

PYTHON_EXEC=""
if [ -n "$VENV_PATH" ] && [ -x "$VENV_PATH/bin/python" ]; then
    if [ -f "$VENV_PATH/bin/activate" ]; then
        source "$VENV_PATH/bin/activate"
    fi
    PYTHON_EXEC="$VENV_PATH/bin/python"
elif [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    PYTHON_EXEC="$VIRTUAL_ENV/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_EXEC="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
    PYTHON_EXEC="$(command -v python)"
fi

if [ -z "$PYTHON_EXEC" ]; then
    echo "Error: Python interpreter not found." >&2
    exit 1
fi

exec "$PYTHON_EXEC" "$APP_DIR/github_uploader.py" "$@"
EOF
    chmod +x "$bdir/github"

    # Install typo wrappers
    for typo in "${TYPO_COMMANDS[@]}"; do
        cat << 'EOF' > "$bdir/$typo"
#!/usr/bin/env bash
echo -e "\033[1;33mTypo detected ('$(basename "$0")'). Did you mean '\033[1;32mgithub\033[1;33m'? Launching github...\033[0m"
sleep 1
exec github "$@"
EOF
        chmod +x "$bdir/$typo"
    done
done

# ------------------------------------------------------------------------------
# 6. Configure Shell RC Files (.bashrc / .zshrc)
# ------------------------------------------------------------------------------
RC_FILES=("$HOME/.bashrc" "$HOME/.zshrc" "/root/.bashrc" "/data/data/com.termux/files/home/.bashrc" "/data/data/com.termux/files/home/.zshrc")

SHELL_SNIPPET="
# >>> GitHub Auto Uploader Config >>>
export PATH=\"\$HOME/.local/bin:\$PATH\"
if [ -d \"$MYENV_DIR\" ]; then
    alias myenv=\"source $MYENV_DIR/bin/activate\"
    alias deactive=\"deactivate\"
fi
alias gthub=\"github\"
alias gihub=\"github\"
alias githb=\"github\"
alias gitub=\"github\"
alias ghub=\"github\"
alias githup=\"github\"
alias git-hub=\"github\"
alias githubb=\"github\"
alias githhub=\"github\"
alias guthub=\"github\"

if ! declare -F command_not_found_handle >/dev/null 2>&1; then
    command_not_found_handle() {
        case \"\$1\" in
            gthub*|gihub*|githb*|gitub*|ghub*|githup*|githubb*|githhub*|git-hub*|guthub*|githun*|gythub*|gothub*)
                echo -e \"\\033[1;33mCommand '\$1' not found. Did you mean '\\033[1;32mgithub\\033[1;33m'? [Y/n]\\033[0m \"
                read -r -n 1 res
                echo
                if [[ -z \"\$res\" || \"\$res\" =~ ^[Yy]$ ]]; then
                    github \"\${@:2}\"
                    return \$?
                fi
                return 127
                ;;
            *)
                if [ -x /data/data/com.termux/files/usr/libexec/termux/command-not-found ]; then
                    /data/data/com.termux/files/usr/libexec/termux/command-not-found \"\$1\"
                    return \$?
                elif [ -x /usr/lib/command-not-found ]; then
                    /usr/lib/command-not-found -- \"\$1\"
                    return \$?
                else
                    echo \"\$1: command not found\" >&2
                    return 127
                fi
                ;;
        esac
    }
fi
# <<< GitHub Auto Uploader Config <<<
"

for rc in "${RC_FILES[@]}"; do
    if [ -f "$rc" ]; then
        if ! grep -q "GitHub Auto Uploader Config" "$rc"; then
            echo "$SHELL_SNIPPET" >> "$rc"
            echo "[✓] Configured shell alias and typo handler in $rc"
        fi
    fi
done

echo ""
echo "============================================================"
echo "✅ Installation Complete!"
echo "📁 Source Directory: $INSTALL_DIR"
echo "🐍 Virtual Environment: $MYENV_DIR"
echo "🚀 Next time in ANY folder: simply type 'github'"
echo "💡 Typo Protection: 'gthub', 'gihub', 'gitub' will auto-launch github!"
echo "============================================================"
echo ""

# ------------------------------------------------------------------------------
# 7. Launch GitHub Auto Uploader immediately with source
# ------------------------------------------------------------------------------
echo "==> Launching GitHub Auto Uploader Pro with $MYENV_DIR source..."
sleep 1

if [ -t 0 ]; then
    exec "$VENV_PYTHON" "$INSTALL_DIR/github_uploader.py" "$@"
elif [ -e /dev/tty ] && [ -r /dev/tty ]; then
    exec "$VENV_PYTHON" "$INSTALL_DIR/github_uploader.py" "$@" </dev/tty
else
    echo "[✓] Installation complete! Type 'github' in any folder to start."
fi
