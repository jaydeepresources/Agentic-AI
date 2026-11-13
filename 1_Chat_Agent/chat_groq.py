import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq, GroqError
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
MODEL_ID = "openai/gpt-oss-120b"
MAX_TURNS = 10
SYSTEM_PROMPT = "You are a friendly, helpful assistant. Respond clearly and concisely."

console = Console()


def main() -> int:
    load_dotenv(dotenv_path=ENV_PATH)
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("Groq")
    if not api_key:
        console.print(
            "[bold red]Groq API key not found.[/] Set GROQ_API_KEY in the project .env file."
        )
        return 1

    client = Groq(api_key=api_key)
    history = [{"role": "system", "content": SYSTEM_PROMPT}]

    console.print(
        Panel(
            Text("A friendly chat, powered by Groq", style="bold cyan", justify="center"),
            subtitle=f"[dim]{MODEL_ID}[/]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print("[dim]Chat for up to 10 turns. Type /exit to leave.[/]\n")

    turn = 0
    while turn < MAX_TURNS:
        try:
            user_message = Prompt.ask(
                f"[bold green]You[/] [dim]({turn + 1}/{MAX_TURNS})[/]"
            ).strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Chat ended.[/]")
            return 0

        if user_message.lower() in {"/exit", "/quit"}:
            break
        if not user_message:
            continue

        try:
            response = client.chat.completions.create(
                model=MODEL_ID,
                messages=[*history, {"role": "user", "content": user_message}],
                max_completion_tokens=2048,
                include_reasoning=False,
            )
        except GroqError as error:
            console.print(
                Panel(
                    f"{type(error).__name__}: {error}",
                    title="Groq request failed",
                    border_style="red",
                )
            )
            continue

        if not response.choices:
            console.print("[bold red]Groq returned no chat choices.[/]")
            continue

        choice = response.choices[0]
        content = choice.message.content
        if not isinstance(content, str) or not content.strip():
            console.print(
                "[bold red]Groq returned no reply text[/] "
                f"[dim](finish_reason={choice.finish_reason!r})[/]"
            )
            continue

        history.extend(
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": content},
            ]
        )
        turn += 1
        console.print(
            Panel(
                Markdown(content.strip()),
                title="[bold cyan]Groq[/]",
                border_style="cyan",
                padding=(1, 2),
            )
        )

    console.print("\n[bold cyan]Thanks for chatting![/]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
