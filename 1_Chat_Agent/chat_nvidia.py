import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
CHAT_COMPLETIONS_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL_ID = "nvidia/nemotron-3.5-super-vl-120b-a12b"
MAX_TURNS = 10
SYSTEM_PROMPT = "You are a friendly, helpful assistant. Respond clearly and concisely."

console = Console()


def request_reply(api_key: str, messages: list[dict[str, str]]) -> str:
    request = Request(
        CHAT_COMPLETIONS_URL,
        data=json.dumps(
            {
                "model": MODEL_ID,
                "messages": messages,
                "max_tokens": 2048,
                "chat_template_kwargs": {"enable_thinking": False},
                "stream": False,
            }
        ).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=120) as response:
        payload = json.load(response)

    if not isinstance(payload, dict):
        raise ValueError("NVIDIA returned an unexpected chat response.")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ValueError("NVIDIA returned no chat choices.")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise ValueError("NVIDIA returned a malformed chat message.")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise ValueError(
            "NVIDIA returned no reply text "
            f"(finish_reason={choices[0].get('finish_reason')!r})."
        )
    return content.strip()


def main() -> int:
    load_dotenv(dotenv_path=ENV_PATH)
    api_key = os.getenv("NVIDIA_AI_KEY") or os.getenv("NVIDIA_API_KEY")
    if not api_key:
        console.print(
            "[bold red]NVIDIA API key not found.[/] Set NVIDIA_AI_KEY or "
            "NVIDIA_API_KEY in the project .env file."
        )
        return 1

    history = [{"role": "system", "content": SYSTEM_PROMPT}]
    console.print(
        Panel(
            Text(
                "A friendly chat, powered by NVIDIA",
                style="bold green",
                justify="center",
            ),
            subtitle=f"[dim]{MODEL_ID}[/]",
            border_style="green",
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
            reply = request_reply(
                api_key,
                [*history, {"role": "user", "content": user_message}],
            )
        except HTTPError as error:
            console.print(
                f"[bold red]NVIDIA API error:[/] HTTP {error.code}: {error.reason}"
            )
            continue
        except URLError as error:
            console.print(f"[bold red]Could not connect to NVIDIA:[/] {error.reason}")
            continue
        except TimeoutError:
            console.print("[bold red]NVIDIA request timed out.[/]")
            continue
        except (json.JSONDecodeError, ValueError) as error:
            console.print(f"[bold red]Could not read NVIDIA reply:[/] {error}")
            continue

        history.extend(
            [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": reply},
            ]
        )
        turn += 1
        console.print(
            Panel(
                Markdown(reply),
                title="[bold green]NVIDIA[/]",
                border_style="green",
                padding=(1, 2),
            )
        )

    console.print("\n[bold green]Thanks for chatting![/]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
