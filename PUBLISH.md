# How to Publish RelayAI

## Step 1 — Push to GitHub

```bash
# Inside the relayai folder
git init
git add .
git commit -m "Initial release v1.0.0"

# Create a new repo on github.com named "relayai" then:
git remote add origin https://github.com/YOURUSERNAME/relayai.git
git branch -M main
git push -u origin main
```

---

## Step 2 — Claim the name on PyPI (do this first)

1. Go to https://pypi.org/account/register and create an account
2. Enable 2FA on your PyPI account (required for publishing)
3. Go to https://pypi.org/manage/account/token and create an API token
4. Save the token somewhere safe

---

## Step 3 — Publish to PyPI manually (first time)

```bash
# Install build tools
pip install build twine

# Build the package
python -m build

# Upload to PyPI (paste your token when asked)
twine upload dist/*
```

After this, anyone can run:
```bash
pip install relayai
```

---

## Step 4 — Connect PyPI to GitHub (for auto-publishing)

1. Go to your GitHub repo → Settings → Secrets → Actions
2. Add secret: Name = `PYPI_API_TOKEN`, Value = your PyPI token
3. Now every time you create a GitHub Release, it auto-publishes to PyPI

---

## Step 5 — Enable branch protection on GitHub

1. Go to repo → Settings → Branches
2. Add rule for `main` branch
3. Enable: "Require a pull request before merging"
4. This prevents anyone (including you accidentally) from pushing bad code directly

---

## Step 6 — Create your first GitHub Release

1. Go to your repo → Releases → Create a new release
2. Tag: `v1.0.0`
3. Title: `RelayAI v1.0.0 — Initial Release`
4. Describe what it does
5. Click Publish Release
6. GitHub Actions will automatically build and push to PyPI

---

## After publishing — update README with install badge

Add this to the top of README.md:

```markdown
[![PyPI version](https://badge.fury.io/py/relayai.svg)](https://badge.fury.io/py/relayai)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
```
