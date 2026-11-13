import argparse
import json
import sys
from typing import Any

from mcp.server import MCPServer
from math_tools import (
    MathInputError,
    classify_math_error,
    evaluate_math as evaluate_math_expression,
    handle_errors as explain_math_error,
    out_of_scope as respond_out_of_scope,
)
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
console = Console()
mcp = MCPServer(
    "Math Tools",
    instructions="A local MCP server for evaluating safe SymPy math expressions.",
)


def _show_tool_result(
    name: str, arguments: dict[str, Any], result: dict[str, Any]
) -> None:
    console.print(
        Panel(
            Syntax(
                json.dumps(
                    {"tool": name, "arguments": arguments, "result": result},
                    indent=2,
                    ensure_ascii=False,
                    allow_nan=False,
                ),
                "json",
                theme="monokai",
                word_wrap=True,
            ),
            title=Text(f"MCP tool called · {name}", style="bold cyan"),
            border_style="cyan",
            padding=(0, 1),
        )
    )


@mcp.tool()
def evaluate_math(expression: str) -> dict[str, Any]:
    """Evaluate math questions using arithmetic and supported SymPy functions.

    Translate word problems into the expression that answers them. Use x, y,
    or other variable names for symbols; common functions include sqrt, sin,
    cos, tan, log, exp, factor, expand, simplify, solve, diff, integrate, and
    limit. Only whitelisted math functions and arithmetic syntax are accepted;
    do not use attributes, imports, or other code.

    Args:
        expression: A math expression, such as '(12 + 8) * 3',
            'diff(x**2, x)', or 'solve(x**2 - 4, x)'.
    """
    try:
        result = evaluate_math_expression(expression)
    except (MathInputError, ArithmeticError, TypeError) as error:
        error_type, details = classify_math_error(error)
        result = {"ok": False, "error_type": error_type, "details": details}
    _show_tool_result("evaluate_math", {"expression": expression}, result)
    return result


@mcp.tool()
def out_of_scope(topic: str) -> dict[str, Any]:
    """Use when the user's request is not a mathematics question."""
    result = respond_out_of_scope(topic)
    _show_tool_result("out_of_scope", {"topic": topic}, result)
    return result


@mcp.tool()
def handle_errors(error_type: str, details: str = "") -> dict[str, Any]:
    """Explain a genuine math-tool error reported during a calculation."""
    result = explain_math_error(error_type, details)
    _show_tool_result(
        "handle_errors",
        {"error_type": error_type, "details": details},
        result,
    )
    return result


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Rich Math MCP server.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Local interface to bind.")
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"HTTP port to listen on (default: {DEFAULT_PORT}).",
    )
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535.")
    return args


def _show_startup(host: str, port: int) -> None:
    console.print(
        Panel(
            Text(
                "The SymPy math tool is ready for MCP clients.",
                justify="center",
                style="bold green",
            ),
            title=Text("Math MCP Server", style="bold cyan"),
            subtitle=f"http://{host}:{port}/mcp",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    tools = Table(
        title="Exposed MCP tools",
        box=box.ROUNDED,
        header_style="bold cyan",
        border_style="blue",
    )
    tools.add_column("Tool", style="bold")
    tools.add_column("Purpose")
    tools.add_row("evaluate_math", "Evaluate safe SymPy expressions")
    tools.add_row("out_of_scope", "Respond to non-math requests")
    tools.add_row("handle_errors", "Explain a reported tool error")
    console.print(tools)
    console.print("[dim]Press Ctrl+C to stop the server.[/]\n")


def main() -> int:
    args = _parse_args()
    _show_startup(args.host, args.port)
    try:
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    except KeyboardInterrupt:
        console.print("\n[dim]Math MCP server stopped.[/]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
