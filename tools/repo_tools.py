"""
Repo Tools
==========
Reads the codebase to give agents context, and writes output files back.
"""

import os
from pathlib import Path
from typing import Optional


# File extensions agents are allowed to read
READABLE_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx", ".json", ".sql",
    ".md", ".env.example", ".prisma", ".css", ".scss",
}

# Directories to skip when scanning
SKIP_DIRS = {
    "node_modules", ".git", ".next", "dist", "build",
    "__pycache__", ".cache", "coverage", ".turbo",
}

# Max chars to read per file (avoid huge files blowing context)
MAX_FILE_CHARS = 8_000


class RepoTools:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path

    def scan_structure(self) -> str:
        """Returns a tree-like string of the repo structure."""
        lines = []
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            level = len(Path(root).relative_to(self.repo_path).parts)
            indent = "  " * level
            folder_name = Path(root).name
            if level == 0:
                lines.append(f"{self.repo_path.name}/")
            else:
                lines.append(f"{indent}{folder_name}/")
            for f in files:
                lines.append(f"{indent}  {f}")
        return "\n".join(lines[:200])  # cap at 200 lines

    def read_key_files(self) -> str:
        """Reads the most important files in the repo and returns their content."""
        priority_files = [
            "package.json",
            "prisma/schema.prisma",
            "schema.sql",
            "README.md",
            "src/app/layout.tsx",
            "src/app/page.tsx",
            "app/layout.tsx",
            "app/page.tsx",
            "src/lib/db.ts",
            "src/lib/supabase.ts",
            "lib/supabase.ts",
            "lib/db.ts",
            "src/types/index.ts",
            "types/index.ts",
        ]

        output = []
        for rel_path in priority_files:
            full_path = self.repo_path / rel_path
            if full_path.exists():
                content = self._read_file(full_path)
                output.append(f"\n--- {rel_path} ---\n{content}")

        # Also grab any API route files
        for api_dir in ["src/app/api", "app/api", "pages/api"]:
            api_path = self.repo_path / api_dir
            if api_path.exists():
                for f in api_path.rglob("*.ts"):
                    content = self._read_file(f)
                    rel = f.relative_to(self.repo_path)
                    output.append(f"\n--- {rel} ---\n{content}")

        return "\n".join(output) if output else "(no key files found)"

    def read_file(self, relative_path: str) -> Optional[str]:
        """Read a specific file from the repo."""
        full_path = self.repo_path / relative_path
        if full_path.exists():
            return self._read_file(full_path)
        return None

    def write_file(self, relative_path: str, content: str) -> bool:
        """Write a file to the repo."""
        full_path = self.repo_path / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
        print(f"  ✍️  Written: {relative_path}")
        return True

    def write_files(self, files: dict[str, str]) -> list[str]:
        """Write multiple files. files = {relative_path: content}"""
        written = []
        for path, content in files.items():
            if self.write_file(path, content):
                written.append(path)
        return written

    def _read_file(self, path: Path) -> str:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            if len(content) > MAX_FILE_CHARS:
                content = content[:MAX_FILE_CHARS] + f"\n... (truncated, {len(content)} chars total)"
            return content
        except Exception as e:
            return f"(error reading file: {e})"
