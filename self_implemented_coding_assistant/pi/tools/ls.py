import os
from pi.ai.base import ToolDefinition

DEFINITION = ToolDefinition(
    name="ls",
    description="List files and directories at a path. Use '.' for the current directory.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path to list",
            },
            "recursive": {
                "type": "boolean",
                "description": "Whether to list subdirectories recursively",
            },
        },
        "required": ["path", "recursive"],
    },
)


def execute(path: str, recursive: bool = False) -> str:
    try:
        if not recursive:
            dirs = []
            files = []
            with os.scandir(path) as it:
                for entry in it:
                    if entry.is_dir():
                        dirs.append(f"  {entry.name}/")
                    else:
                        size = entry.stat().st_size
                        files.append(f"  {entry.name}  ({_format_size(size)})")
            dirs.sort()
            files.sort()
            lines = [f"{os.path.abspath(path)}"] + dirs + files
            return "\n".join(lines) or "(empty directory)"
        else:
            lines = [f"{os.path.abspath(path)}"]
            for root, dirs, filenames in os.walk(path):
                dirs[:] = sorted([d for d in dirs if not d.startswith(".")])
                rel = os.path.relpath(root, path)
                level = 0 if rel == '.' else len(rel.split(os.sep))
                indent = "  " * (level + 1)
                for d in sorted(dirs):
                    lines.append(f"{indent}{d}/")
                for f in sorted(filenames):
                    lines.append(f"{indent}{f}")
                # limit output size
                if len(lines) > 500:
                    lines.append("  ... (truncated)")
                    break
            return "\n".join(lines)
    except FileNotFoundError:
        return f"Error: directory not found: {path}"
    except Exception as e:
        return f"Error: {e}"


def _format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.1f} MB"
