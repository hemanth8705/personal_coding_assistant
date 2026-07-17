import subprocess
import sys
from pi.ai.base import ToolDefinition

DEFINITION = ToolDefinition(
    name="bash",
    description=(
        "Run a shell command and return its output. "
        "Use this to read files, list directories, run scripts, or interact with the system."
    ),
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to run",
            }
        },
        "required": ["command"],
    },
)


def execute(command: str) -> str:
    shell = True
    if sys.platform == "win32":
        # On Windows, try to use bash if available, otherwise fallback to default shell
        # But based on observed errors, let's prefer the default shell (cmd/powershell)
        # or at least handle the case where 'bash' is missing.
        args = command
    else:
        args = command
    
    try:
        result = subprocess.run(
            args,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
    except Exception as e:
        output = f"Error running command: {e}"
    
    return output.strip() or "(no output)"
