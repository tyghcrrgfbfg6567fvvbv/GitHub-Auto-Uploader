#!/usr/bin/env bash
# GitHub Auto Uploader Installer
set -e

REPO_URL="https://github.com/Mr-Risov/GitHub-Auto-Uploader.git"
INSTALL_DIR="${HOME}/.Github-Auto-Uploader"
SCRIPT_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Installing GitHub Auto Uploader Pro..."
mkdir -p "$INSTALL_DIR"

# Copy / Sync files into ~/.Github-Auto-Uploader
if [ -f "$SCRIPT_SRC/github_uploader.py" ] && [ -d "$SCRIPT_SRC/github_auto_uploader" ]; then
    echo "==> Installing from local source: $SCRIPT_SRC"
    cp -r "$SCRIPT_SRC/github_auto_uploader" "$INSTALL_DIR/"
    cp "$SCRIPT_SRC/github_uploader.py" "$INSTALL_DIR/"
    cp "$SCRIPT_SRC/requirements.txt" "$INSTALL_DIR/"
    cp "$SCRIPT_SRC/LICENSE" "$INSTALL_DIR/" 2>/dev/null || true
    cp "$SCRIPT_SRC/README.md" "$INSTALL_DIR/" 2>/dev/null || true
    if [ -f "$SCRIPT_SRC/config.json" ] && [ ! -f "$INSTALL_DIR/config.json" ]; then
        cp "$SCRIPT_SRC/config.json" "$INSTALL_DIR/"
    fi
else
    echo "==> Cloning latest version from GitHub..."
    TMP_CLONE=$(mktemp -d)
    git clone --depth 1 "$REPO_URL" "$TMP_CLONE"
    cp -r "$TMP_CLONE/github_auto_uploader" "$INSTALL_DIR/"
    cp "$TMP_CLONE/github_uploader.py" "$INSTALL_DIR/"
    cp "$TMP_CLONE/requirements.txt" "$INSTALL_DIR/"
    cp "$TMP_CLONE/LICENSE" "$INSTALL_DIR/" 2>/dev/null || true
    cp "$TMP_CLONE/README.md" "$INSTALL_DIR/" 2>/dev/null || true
    rm -rf "$TMP_CLONE"
fi

# Ensure existing config.json is preserved
if [ ! -f "$INSTALL_DIR/config.json" ]; then
    for cand in "/data/data/com.termux/files/home/GitHub-Auto-Uploader/config.json" "/root/GitHub-Auto-Uploader/config.json"; do
        if [ -f "$cand" ]; then
            cp "$cand" "$INSTALL_DIR/config.json"
            break
        fi
    done
fi

# Create launcher script
LAUNCHER_CONTENT='#!/usr/bin/env bash
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

PYTHON_EXEC=""
if [ -x "/data/data/com.termux/files/home/myenv/bin/python" ]; then
    PYTHON_EXEC="/data/data/com.termux/files/home/myenv/bin/python"
elif [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    PYTHON_EXEC="$VIRTUAL_ENV/bin/python"
elif [ -x "$APP_DIR/venv/bin/python" ]; then
    PYTHON_EXEC="$APP_DIR/venv/bin/python"
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
'

# Install launcher into available bin directories
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

PYTHON_EXEC=""
if [ -x "/data/data/com.termux/files/home/myenv/bin/python" ]; then
    PYTHON_EXEC="/data/data/com.termux/files/home/myenv/bin/python"
elif [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    PYTHON_EXEC="$VIRTUAL_ENV/bin/python"
elif [ -x "$APP_DIR/venv/bin/python" ]; then
    PYTHON_EXEC="$APP_DIR/venv/bin/python"
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

    # Create typo symlinks/wrappers so typos work instantly everywhere
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

# Add aliases and smart command_not_found_handle to shell rc files
RC_FILES=("$HOME/.bashrc" "$HOME/.zshrc" "/root/.bashrc" "/data/data/com.termux/files/home/.bashrc" "/data/data/com.termux/files/home/.zshrc")

SHELL_SNIPPET='
# >>> GitHub Auto Uploader Config >>>
export PATH="$HOME/.local/bin:$PATH"
alias gthub="github"
alias gihub="github"
alias githb="github"
alias gitub="github"
alias ghub="github"
alias githup="github"
alias git-hub="github"
alias githubb="github"
alias githhub="github"
alias guthub="github"

if ! declare -F command_not_found_handle >/dev/null 2>&1; then
    command_not_found_handle() {
        case "$1" in
            gthub*|gihub*|githb*|gitub*|ghub*|githup*|githubb*|githhub*|git-hub*|guthub*|githun*|gythub*|gothub*)
                echo -e "\033[1;33mCommand '\''$1'\'' not found. Did you mean '\''\033[1;32mgithub\033[1;33m'\''? [Y/n]\033[0m "
                read -r -n 1 res
                echo
                if [[ -z "$res" || "$res" =~ ^[Yy]$ ]]; then
                    github "${@:2}"
                    return $?
                fi
                return 127
                ;;
            *)
                if [ -x /data/data/com.termux/files/usr/libexec/termux/command-not-found ]; then
                    /data/data/com.termux/files/usr/libexec/termux/command-not-found "$1"
                    return $?
                elif [ -x /usr/lib/command-not-found ]; then
                    /usr/lib/command-not-found -- "$1"
                    return $?
                else
                    echo "$1: command not found" >&2
                    return 127
                fi
                ;;
        esac
    }
fi
# <<< GitHub Auto Uploader Config <<<
'

for rc in "${RC_FILES[@]}"; do
    if [ -f "$rc" ]; then
        if ! grep -q "GitHub Auto Uploader Config" "$rc"; then
            echo "$SHELL_SNIPPET" >> "$rc"
            echo "==> Updated $rc with aliases and typo helper"
        fi
    fi
done

echo ""
echo "============================================================"
echo "✅ GitHub Auto Uploader Pro installed successfully!"
echo "📁 Stored in: $INSTALL_DIR"
echo "🚀 Run from ANY folder by simply typing: github"
echo "💡 Typos like 'gthub', 'gihub', 'gitub' will automatically prompt/launch github!"
echo "============================================================"
