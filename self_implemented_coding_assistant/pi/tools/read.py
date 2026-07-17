from pi.ai.base import ToolDefinition

DEFINITION = ToolDefinition(
    name="read",
    description="Read the contents of a file. Returns the file content with line numbers.",
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to read",
            },
            "offset": {
                "type": "integer",
                "description": "The line number to start reading from (default: 1)",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of lines to read (default: 500)",
            }
        },
        "required": ["path", "offset", "limit"],
    },
)


def execute(path: str, offset: int = 1, limit: int = 500) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        start_idx = max(0, offset - 1)
        end_idx = start_idx + limit

        subset = lines[start_idx:end_idx]
        if not subset and offset > 1:
            return f"Error: offset {offset} is beyond the end of the file (total lines: {len(lines)})"

        numbered = "".join(f"{start_idx + i + 1}\t{line}" for i, line in enumerate(subset))

        status = []
        if start_idx > 0:
            status.append(f"Started from line {offset}")
        if end_idx < len(lines):
            status.append(f"Truncated at line {end_idx}. Total lines: {len(lines)}. Use offset={end_idx + 1} to read more.")

        header = f"--- {path} " + (" | ".join(status) if status else "") + " ---\n"
        return header + (numbered or "(empty file)")
    except FileNotFoundError:
        return f"Error: file not found: {path}"
    except Exception as e:
        return f"Error: {e}"
