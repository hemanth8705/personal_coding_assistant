from pi.ai.base import ToolDefinition

DEFINITION = ToolDefinition(
    name="edit",
    description=(
        "Replace an exact string in a file with new text. "
        "The old_string must match exactly once — use more surrounding context if it appears multiple times. "
        "Prefer this over write for making targeted changes to existing files."
    ),
    parameters={
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path to the file to edit",
            },
            "old_string": {
                "type": "string",
                "description": "The exact string to find and replace",
            },
            "new_string": {
                "type": "string",
                "description": "The string to replace it with",
            },
        },
        "required": ["path", "old_string", "new_string"],
    },
)


def execute(path: str, old_string: str, new_string: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        count = content.count(old_string)
        if count == 0:
            return f"Error: old_string not found in {path}"
        if count > 1:
            return f"Error: old_string appears {count} times in {path} — provide more context to make it unique"

        new_content = content.replace(old_string, new_string, 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return f"Edited {path} successfully"
    except FileNotFoundError:
        return f"Error: file not found: {path}"
    except Exception as e:
        return f"Error: {e}"
