
### 🛰️ GitHub Auto Uploader

A powerful and user-friendly Python tool to automatically upload folders or ZIP archives to your GitHub repository — perfect for bot projects, code backups, or automation pipelines.

![GitHub](https://img.shields.io/github/license/Mr-Risov/github-auto-uploader?style=flat-square)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg?style=flat-square)
![Rich UI](https://img.shields.io/badge/UI-rich%20library-informational?style=flat-square)

---

## 🔧 Features

- ✅ Upload entire folders or `.zip` files directly to GitHub
- ✅ Smart zip extraction with confirmation
- ✅ Configuration saved in `config.json` for easy reuse
- ✅ Rich CLI with prompts, panels, and colored logs
- ✅ GitHub repository auto-creation (private/public)
- ✅ Detects invalid paths and offers advanced search
- ✅ Auto-logs all operations in `upload.log`
- ✅ Prompt-based config update without editing JSON manually
- ✅ GitHub Safe Directory handling on Termux/Linux/Windows

---

## ⬇️ Installation 

- Install git if not installed 

```bash
pkg install git
```


- Download the repository


```bash
git clone https://github.com/Mr-Risov/GitHub-Auto-Uploader.git
```


## 📦 Requirements

- Python 3.8 or newer
- Git must be installed and accessible via the command line

Install dependencies using:

```bash
pip install -r requirements.txt
````

---

## 🚀 Usage

```bash
python github_uploader.py
```

You'll be prompted to:

1. Enter your GitHub token and repo details
2. Choose folder or zip file path
3. Confirm visibility (public/private)
4. Upload it all — in style 🎉

---

## 🔐 GitHub Token Help

* Generate token from: [https://github.com/settings/tokens](https://github.com/settings/tokens)
* Required scopes: `repo`, `workflow`

---

## 📁 Folder & ZIP Support

* ZIPs are auto-detected and prompt you to extract
* Deep folder search supported on Android (`/sdcard/`), Windows (`C:/`, `D:/`), and Linux

---

## 📝 Configuration Example (`config.json`)

```json
{
  "token": "ghp_xxx",
  "username": "your-username",
  "repo_name": "your-repo",
  "folder_path": "/path/to/folder",
  "is_public": true,
  "commit_msg": "Initial upload"
}
```

---

## 🐞 Troubleshooting

* ❌ `fatal: detected dubious ownership`: Handled automatically with Git Safe Directory config
* ❌ No internet: Make sure you're connected to the internet before running
* ❌ Git not installed: Install Git via `pkg install git` (Termux) or your OS package manager

---

## 📄 License

MIT License © [Mr-Risov](https://github.com/Mr-Risov)

