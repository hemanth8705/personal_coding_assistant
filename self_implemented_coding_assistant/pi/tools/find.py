import os
import fnmatch
from pi.ai.base import ToolDefinition

DEFINITION = ToolDefinition(
    name="find",
    description=(
        "Find files by name pattern within a directory tree. "
        "Use this to locate files by extension (e.g. '*.py') or partial name. "
        "Use 'grep' to search file contents. Use 'find' to locate files by name."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Root directory to search in",
            },
            "pattern": {
                "type": "string",
                "description": "Filename glob pattern, e.g. '*.py', 'config.*', 'test_*'",
            },
            "recursive": {
                "type": "boolean",
                "description": "Search subdirectories recursively (default: true)",
            },
        },
        "required": ["path", "pattern"],
    },
)


def execute(path: str, pattern: str, recursive: bool = True) -> str:
    if not os.path.isdir(path):
        return f"Error: directory not found: {path}"

    matches = []
    if recursive:
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            for name in files:
                if fnmatch.fnmatch(name, pattern):
                    matches.append(os.path.join(root, name))
    else:
        for name in os.listdir(path):
            full = os.path.join(path, name)
            if os.path.isfile(full) and fnmatch.fnmatch(name, pattern):
                matches.append(full)

    if not matches:
        return f"No files matching '{pattern}' found in {path}"

    matches.sort()
    result = "\n".join(matches[:200])
    if len(matches) > 200:
        result += f"\n... ({len(matches) - 200} more results truncated)"
    return result
