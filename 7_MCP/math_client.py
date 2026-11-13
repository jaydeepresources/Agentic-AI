import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from mcp import Client, MCPError
from mcp.types import CallToolResult, TextContent, Tool
from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
CHAT_COMPLETIONS_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL_ID = "nvidia/nemotron-3.5-super-vl-120b-a12b"
DEFAULT_SERVER_URL = "http://127.0.0.1:8000/mcp"
MAX_TOOL_CALLS = 10
console = Console()

SYSTEM_PROMPT = (
    "You are a mathematics assistant connected to a local MCP server. For every "
    "user message, use exactly one tool first: call evaluate_math for a "
    "mathematical question, translating word problems into a precise "
    "SymPy-compatible expression; call out_of_scope for requests that are not "
    "mathematical. Never calculate mentally or answer before using a tool. "
    "If a tool result reports ok=false, call handle_errors with its error_type "
    "and details, then explain the result briefly. After a successful tool "
    "result, give a clear, concise answer based on that result. Do not treat "
    "ordinary ambiguity as a technical error; ask a concise clarifying "
    "question if the math problem cannot be translated into a definite "
    "expression."
)


def openai_tool_definitions(tools: list[Tool]) -> list[dict[str, Any]]:
    definitions = []
    for tool in tools:
        definitions.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.input_schema,
                },
            }
        )
    return definitions


def request_completion(
    api_key: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> dict[str, Any]:
    request = Request(
        CHAT_COMPLETIONS_URL,
        data=json.dumps(
            {
                "model": MODEL_ID,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
                "max_tokens": 1024,
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
    return message


def _tool_error_details(result: CallToolResult) -> str:
    return "\n".join(
        block.text for block in result.content if isinstance(block, TextContent)
    )


def _tool_result_for_model(result: CallToolResult) -> dict[str, Any]:
    if result.is_error:
        details = _tool_error_details(result) or "The MCP tool returned an error."
        lowered = details.lower()
        if "division by zero" in lowered:
            error_type = "division_by_zero"
        elif "numeric range" in lowered or "exponents must" in lowered:
            error_type = "numeric_limit"
        else:
            error_type = "tool_call_error"
        return {"ok": False, "error_type": error_type, "details": details}
    if isinstance(result.structured_content, dict):
        return result.structured_content
    return {"content": _tool_error_details(result)}


def _show_tool_step(
    tool_call_number: int,
    name: str,
    arguments: dict[str, Any],
    result: dict[str, Any],
) -> None:
    console.print(
        Panel(
            Syntax(
                json.dumps(
                    {"tool": name, "arguments": arguments},
                    indent=2,
                    ensure_ascii=False,
                ),
                "json",
                theme="monokai",
                word_wrap=True,
            ),
            title=Text(
                f"Action {tool_call_number}/{MAX_TOOL_CALLS} · {name}",
                style="bold cyan",
            ),
            border_style="cyan",
            padding=(0, 1),
        )
    )
    succeeded = result.get("ok") is not False
    console.print(
        Panel(
            Syntax(
                json.dumps(result, indent=2, ensure_ascii=False),
                "json",
                theme="monokai",
                word_wrap=True,
            ),
            title=Text(
                "MCP tool result",
                style="bold green" if succeeded else "bold red",
            ),
            border_style="green" if succeeded else "red",
            padding=(0, 1),
        )
    )


async def run_agent(
    api_key: str,
    question: str,
    client: Client,
    tools: list[Tool],
) -> str:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    tool_definitions = openai_tool_definitions(tools)
    available_tools = {tool.name for tool in tools}
    tool_calls_used = 0

    while True:
        message = request_completion(api_key, messages, tool_definitions)
        tool_calls = message.get("tool_calls", [])
        if not isinstance(tool_calls, list):
            raise ValueError("NVIDIA returned malformed tool calls.")
        if not tool_calls:
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
            raise ValueError("NVIDIA returned neither a reply nor a tool call.")

        if tool_calls_used + len(tool_calls) > MAX_TOOL_CALLS:
            return (
                f"I reached the limit of {MAX_TOOL_CALLS} tool calls for this "
                "question. Please try a simpler calculation."
            )

        messages.append(
            {
                "role": "assistant",
                "content": message.get("content"),
                "tool_calls": tool_calls,
            }
        )

        for tool_call in tool_calls:
            tool_calls_used += 1
            if not isinstance(tool_call, dict):
                raise ValueError("NVIDIA returned a malformed tool call.")
            tool_call_id = tool_call.get("id")
            function = tool_call.get("function")
            if not isinstance(tool_call_id, str) or not tool_call_id:
                raise ValueError("NVIDIA returned a tool call without an ID.")
            if not isinstance(function, dict):
                raise ValueError("NVIDIA returned a malformed tool function.")
            name = function.get("name")
            if not isinstance(name, str):
                raise ValueError("NVIDIA returned a tool call without a name.")

            raw_arguments = function.get("arguments", "{}")
            try:
                arguments = json.loads(raw_arguments)
            except (json.JSONDecodeError, TypeError) as error:
                raise ValueError("NVIDIA returned invalid tool arguments.") from error
            if not isinstance(arguments, dict):
                raise ValueError("Tool arguments must be a JSON object.")

            if name in available_tools:
                result = await client.call_tool(name, arguments)
                tool_result = _tool_result_for_model(result)
            else:
                tool_result = {
                    "ok": False,
                    "error_type": "tool_call_error",
                    "details": f"The MCP server does not expose a tool named {name!r}.",
                }

            _show_tool_step(tool_calls_used, name, arguments, tool_result)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": json.dumps(tool_result, ensure_ascii=False),
                }
            )


def _show_welcome(server_url: str, tools: list[Tool]) -> None:
    console.print(
        Panel(
            Text(
                "Ask a natural-language math question.\n"
                f"Up to {MAX_TOOL_CALLS} MCP tool calls are allowed per question.",
                justify="center",
            ),
            title=Text("MCP Math Client", style="bold cyan"),
            subtitle=f"{MODEL_ID} · {server_url}",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    table = Table(
        title="Tools discovered from the MCP server",
        box=box.ROUNDED,
        header_style="bold cyan",
        border_style="blue",
    )
    table.add_column("Tool", style="bold")
    table.add_column("What it does")
    for tool in tools:
        table.add_row(tool.name, tool.description or "No description provided.")
    console.print(table)
    console.print("[dim]Type /exit or /quit to leave.[/]\n")


def _show_error(message: str) -> None:
    console.print(
        Panel(
            Text(message),
            title=Text("Request failed", style="bold red"),
            border_style="red",
            padding=(0, 1),
        )
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Rich NVIDIA MCP client.")
    parser.add_argument(
        "--server-url",
        default=os.getenv("MCP_SERVER_URL", DEFAULT_SERVER_URL),
        help=f"MCP Streamable HTTP endpoint (default: {DEFAULT_SERVER_URL}).",
    )
    return parser.parse_args()


async def _interactive_session(
    api_key: str, server_url: str
) -> int:
    async with Client(server_url) as client:
        listing = await client.list_tools()
        if not listing.tools:
            raise ValueError("The MCP server did not expose any tools.")
        tools = listing.tools
        _show_welcome(server_url, tools)

        while True:
            try:
                question = Prompt.ask("[bold cyan]You[/]").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Session ended.[/]")
                return 0

            if question.lower() in {"/exit", "/quit"}:
                console.print("[dim]Goodbye.[/]")
                return 0
            if not question:
                continue

            try:
                reply = await run_agent(api_key, question, client, tools)
                console.print(
                    Panel(
                        Markdown(reply),
                        title=Text("Assistant", style="bold green"),
                        border_style="green",
                        padding=(1, 2),
                    )
                )
            except HTTPError as error:
                _show_error(f"NVIDIA returned HTTP {error.code}: {error.reason}")
            except URLError as error:
                _show_error(f"Could not connect to NVIDIA: {error.reason}")
            except TimeoutError:
                _show_error("The NVIDIA request timed out.")
            except (json.JSONDecodeError, ValueError) as error:
                _show_error(str(error))


def main() -> int:
    load_dotenv(dotenv_path=ENV_PATH)
    api_key = os.getenv("NVIDIA_AI_KEY") or os.getenv("NVIDIA_API_KEY")
    if not api_key:
        _show_error(
            "NVIDIA API key not found. Set NVIDIA_AI_KEY or NVIDIA_API_KEY "
            "in the project-root .env file."
        )
        return 1

    args = _parse_args()
    try:
        return asyncio.run(_interactive_session(api_key, args.server_url))
    except (MCPError, OSError, TimeoutError) as error:
        _show_error(f"Could not connect to the MCP server: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
