import os
import re
from pi.ai.base import ToolDefinition

DEFINITION = ToolDefinition(
    name="grep",
    description=(
        "Search for a text pattern inside a file or all files in a directory. "
        "Returns matching lines with file path and line number. "
        "Use this instead of read when you need to find something specific across files."
    ),
    parameters={
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Text or regex pattern to search for",
            },
            "path": {
                "type": "string",
                "description": "File or directory to search in",
            },
            "file_pattern": {
                "type": "string",
                "description": "Filter files by extension, e.g. '*.py' (only applies when path is a directory)",
            },
        },
        "required": ["pattern", "path"],
    },
)


def execute(pattern: str, path: str, file_pattern: str = "*") -> str:
    import fnmatch

    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error:
        regex = re.compile(re.escape(pattern), re.IGNORECASE)

    if os.path.isfile(path):
        files = [path]
    elif os.path.isdir(path):
        files = []
        for root, dirs, filenames in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for name in filenames:
                if fnmatch.fnmatch(name, file_pattern):
                    files.append(os.path.join(root, name))
    else:
        return f"Error: path not found: {path}"

    matches = []
    for filepath in sorted(files):
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                for i, line in enumerate(f, 1):
                    if regex.search(line):
                        matches.append(f"{filepath}:{i}: {line.rstrip()}")
        except Exception:
            pass

    if not matches:
        return f"No matches found for '{pattern}' in {path}"

    result = "\n".join(matches[:100])
    if len(matches) > 100:
        result += f"\n... ({len(matches) - 100} more matches truncated)"
    return result
