from rich.console import Console
from pi.ai.base import ToolDefinition

console = Console()

DEFINITION = ToolDefinition(
    name="ask_user",
    description=(
        "Ask the user a clarifying question and wait for their response before continuing. "
        "Use this when the task is ambiguous, multiple valid approaches exist, "
        "or you need confirmation before an irreversible action."
    ),
    parameters={
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The question to ask the user",
            }
        },
        "required": ["question"],
    },
)


def execute(question: str) -> str:
    console.print(f"\n[bold yellow]Pi:[/bold yellow] {question}")
    try:
        answer = input("You: ").strip()
    except (KeyboardInterrupt, EOFError):
        return "User did not respond."
    return answer if answer else "No answer provided."
