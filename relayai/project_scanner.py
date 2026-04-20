import os
from pathlib import Path

# Files/folders to always ignore
IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    ".env", "dist", "build", ".next", ".nuxt", "target", ".idea",
    ".vscode", "coverage", ".pytest_cache", ".mypy_cache"
}

IGNORE_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".class", ".jar",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".pdf",
    ".zip", ".tar", ".gz", ".lock", ".bin", ".exe"
}

# Files worth reading for context
READABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
    ".json", ".yaml", ".yml", ".toml", ".env", ".md",
    ".txt", ".sh", ".sql", ".go", ".rs", ".java", ".cpp",
    ".c", ".h", ".rb", ".php", ".swift", ".kt"
}

MAX_FILE_SIZE = 50_000   # 50KB per file
MAX_TOTAL_SIZE = 200_000  # 200KB total context


def scan_project(root: str = ".") -> dict:
    """
    Scan current project directory and return structure + key file contents.
    """
    root_path = Path(root).resolve()
    tree = _build_tree(root_path)
    files = _read_key_files(root_path)
    project_type = _detect_project_type(root_path)

    return {
        "root": str(root_path),
        "name": root_path.name,
        "type": project_type,
        "tree": tree,
        "files": files,
    }


def _build_tree(root: Path, prefix: str = "", max_depth: int = 4, depth: int = 0) -> str:
    """Build a visual directory tree."""
    if depth > max_depth:
        return ""

    lines = []
    try:
        entries = sorted(root.iterdir(), key=lambda x: (x.is_file(), x.name))
    except PermissionError:
        return ""

    entries = [e for e in entries if e.name not in IGNORE_DIRS and not e.name.startswith(".")]

    for i, entry in enumerate(entries):
        is_last = i == len(entries) - 1
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{entry.name}")

        if entry.is_dir() and entry.name not in IGNORE_DIRS:
            extension = "    " if is_last else "│   "
            subtree = _build_tree(entry, prefix + extension, max_depth, depth + 1)
            if subtree:
                lines.append(subtree)

    return "\n".join(lines)


def _read_key_files(root: Path) -> dict:
    """Read contents of important files for project context."""
    files = {}
    total_size = 0

    # Priority files to always include if they exist
    priority_files = [
        "README.md", "package.json", "requirements.txt", "setup.py",
        "pyproject.toml", "Cargo.toml", "go.mod", "pom.xml",
        ".env.example", "docker-compose.yml", "Dockerfile",
        "main.py", "index.py", "app.py", "server.py", "index.js",
        "main.js", "app.js", "index.ts", "main.ts", "app.ts"
    ]

    for filename in priority_files:
        path = root / filename
        if path.exists() and path.is_file():
            content = _safe_read(path)
            if content and total_size + len(content) < MAX_TOTAL_SIZE:
                files[str(path.relative_to(root))] = content
                total_size += len(content)

    # Then scan remaining files up to limit
    for path in root.rglob("*"):
        if total_size >= MAX_TOTAL_SIZE:
            break
        if not path.is_file():
            continue
        if any(part in IGNORE_DIRS for part in path.parts):
            continue
        if path.suffix in IGNORE_EXTENSIONS:
            continue
        if path.suffix not in READABLE_EXTENSIONS:
            continue

        rel_path = str(path.relative_to(root))
        if rel_path in files:
            continue

        content = _safe_read(path)
        if content and total_size + len(content) < MAX_TOTAL_SIZE:
            files[rel_path] = content
            total_size += len(content)

    return files


def _safe_read(path: Path) -> str:
    """Safely read a file, returning None on failure."""
    try:
        if path.stat().st_size > MAX_FILE_SIZE:
            return None
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return None


def _detect_project_type(root: Path) -> str:
    """Detect what kind of project this is."""
    markers = {
        "Python": ["requirements.txt", "setup.py", "pyproject.toml", "main.py", "app.py"],
        "Node.js": ["package.json", "index.js", "app.js"],
        "TypeScript": ["tsconfig.json", "index.ts"],
        "React": ["src/App.jsx", "src/App.tsx", "src/index.jsx"],
        "Next.js": ["next.config.js", "next.config.ts"],
        "Go": ["go.mod", "main.go"],
        "Rust": ["Cargo.toml", "src/main.rs"],
        "Java": ["pom.xml", "build.gradle"],
    }

    for project_type, files in markers.items():
        if any((root / f).exists() for f in files):
            return project_type

    return "Unknown"


def format_for_claude(project: dict) -> str:
    """Format project context into a string for Claude's system prompt."""
    parts = [
        f"## Current Project: {project['name']}",
        f"Type: {project['type']}",
        f"Location: {project['root']}",
        "",
        "### Project Structure:",
        "```",
        project["tree"] or "(empty directory)",
        "```",
    ]

    if project["files"]:
        parts.append("\n### Key Files:")
        for filename, content in project["files"].items():
            ext = Path(filename).suffix.lstrip(".")
            parts.append(f"\n**{filename}:**")
            parts.append(f"```{ext}")
            parts.append(content[:3000])  # Cap each file at 3000 chars
            if len(content) > 3000:
                parts.append("... (truncated)")
            parts.append("```")

    return "\n".join(parts)
