import ast
import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
import sympy as sp


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
CHAT_COMPLETIONS_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL_ID = "nvidia/nemotron-3.5-super-vl-120b-a12b"
MAX_TOOL_CALLS = 10
MAX_EXPRESSION_LENGTH = 512
MAX_AST_NODES = 100
console = Console()

SYSTEM_PROMPT = (
    "You are a mathematics assistant. For every user message, use exactly one "
    "tool first: call evaluate_math for a mathematical question, translating "
    "word problems into a precise SymPy-compatible expression; call out_of_scope "
    "for requests that are not mathematical. Never calculate mentally or "
    "answer before using a tool. If a tool result reports ok=false, call "
    "handle_errors with its error_type and details, then explain the result "
    "briefly. After a successful tool result, give a clear, concise answer "
    "based on that result. Do not treat ordinary ambiguity as a technical "
    "error; ask a concise clarifying question if the math problem cannot be "
    "translated into a definite expression."
)

TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "evaluate_math",
            "description": (
                "Evaluate a mathematical question using a mathematical "
                "expression. Translate word problems into the expression that "
                "answers them. Use x, y, or other variable names for symbols; "
                "common functions include sqrt, sin, cos, tan, log, exp, "
                "factor, expand, simplify, solve, diff, integrate, and limit. "
                "Only whitelisted math functions and arithmetic syntax are "
                "accepted; do not use attributes, imports, or other code."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": (
                            "A math expression, such as '(12 + 8) * 3', "
                            "'diff(x**2, x)', or 'solve(x**2 - 4, x)'."
                        ),
                    }
                },
                "required": ["expression"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "out_of_scope",
            "description": (
                "Use when the user's request is not a mathematics question."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "A brief description of the unrelated topic.",
                    }
                },
                "required": ["topic"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "handle_errors",
            "description": (
                "Use only for a genuine error reported by another tool, such "
                "as invalid arithmetic or division by zero."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "error_type": {
                        "type": "string",
                        "description": "The error_type returned by the tool.",
                    },
                    "details": {
                        "type": "string",
                        "description": "The details returned by the tool.",
                    },
                },
                "required": ["error_type"],
                "additionalProperties": False,
            },
        },
    },
]

_BINARY_OPERATORS: dict[type[ast.operator], Any] = {
    ast.Add: lambda left, right: left + right,
    ast.Sub: lambda left, right: left - right,
    ast.Mult: lambda left, right: left * right,
    ast.Div: lambda left, right: left / right,
    ast.FloorDiv: lambda left, right: left // right,
    ast.Mod: lambda left, right: left % right,
    ast.Pow: lambda left, right: left**right,
}
_UNARY_OPERATORS: dict[type[ast.unaryop], Any] = {
    ast.UAdd: lambda value: value,
    ast.USub: lambda value: -value,
}
_CONSTANTS = {
    "pi": sp.pi,
    "E": sp.E,
    "I": sp.I,
    "oo": sp.oo,
}
_FUNCTIONS = {
    "sqrt": sp.sqrt,
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "asin": sp.asin,
    "acos": sp.acos,
    "atan": sp.atan,
    "log": sp.log,
    "ln": sp.log,
    "exp": sp.exp,
    "abs": sp.Abs,
    "factorial": sp.factorial,
    "floor": sp.floor,
    "ceiling": sp.ceiling,
    "simplify": sp.simplify,
    "factor": sp.factor,
    "expand": sp.expand,
    "solve": sp.solve,
    "solveset": sp.solveset,
    "diff": sp.diff,
    "integrate": sp.integrate,
    "limit": sp.limit,
    "Eq": sp.Eq,
    "Ne": sp.Ne,
    "Lt": sp.Lt,
    "Le": sp.Le,
    "Gt": sp.Gt,
    "Ge": sp.Ge,
}


class MathInputError(ValueError):
    """Raised when an expression is outside the supported math syntax."""


def _evaluate_node(node: ast.expr, node_count: list[int]) -> Any:
    node_count[0] += 1
    if node_count[0] > MAX_AST_NODES:
        raise MathInputError("The expression is too complex.")

    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return sp.Rational(str(node.value))

    if isinstance(node, ast.Name):
        if node.id.startswith("__"):
            raise MathInputError("Names beginning with underscores are not supported.")
        return _CONSTANTS.get(node.id, sp.Symbol(node.id))

    if isinstance(node, (ast.Tuple, ast.List)):
        return [_evaluate_node(element, node_count) for element in node.elts]

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        function = _FUNCTIONS.get(node.func.id)
        if function is None or node.keywords:
            raise MathInputError("That math function is not supported.")
        arguments = [_evaluate_node(argument, node_count) for argument in node.args]
        if node.func.id == "factorial" and len(arguments) == 1:
            argument = arguments[0]
            if not isinstance(argument, sp.Basic) or argument.is_Integer is not True:
                raise MathInputError("Factorial requires a non-negative integer.")
            if argument < 0:
                raise MathInputError("Factorial requires a non-negative integer.")
            if argument > 1000:
                raise MathInputError("Factorials are limited to inputs of 1000.")
        return function(*arguments)

    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        value = _evaluate_node(node.operand, node_count)
        return _UNARY_OPERATORS[type(node.op)](value)

    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate_node(node.left, node_count)
        right = _evaluate_node(node.right, node_count)
        if not isinstance(left, sp.Basic) or not isinstance(right, sp.Basic):
            raise MathInputError("Arithmetic operators require scalar expressions.")
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and right.is_zero is True:
            raise ZeroDivisionError("division by zero")
        if (
            isinstance(node.op, ast.Pow)
            and right.is_number
            and bool(abs(right) > 100)
        ):
            raise MathInputError("Exponents must be between -100 and 100.")
        return _BINARY_OPERATORS[type(node.op)](left, right)

    raise MathInputError(
        "Use only mathematical expressions and supported functions."
    )


def _format_result(result: Any) -> tuple[str, str | None]:
    if isinstance(result, list):
        return f"[{', '.join(sp.sstr(item) for item in result)}]", None
    result_text = sp.sstr(result)
    if (
        isinstance(result, sp.Expr)
        and result.is_number
        and not result.free_symbols
        and result.is_Rational is not True
        and result.is_finite is not False
    ):
        return result_text, str(sp.N(result, 12))
    return result_text, None


def evaluate_math(expression: str) -> dict[str, Any]:
    if not isinstance(expression, str) or not expression.strip():
        raise MathInputError("Enter a non-empty math expression.")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise MathInputError("The expression is too long.")

    try:
        parsed = ast.parse(expression, mode="eval")
    except SyntaxError as error:
        raise MathInputError("The math expression is not valid.") from error

    result_text, approximation = _format_result(_evaluate_node(parsed.body, [0]))
    response: dict[str, Any] = {
        "ok": True,
        "expression": expression,
        "result": result_text,
    }
    if approximation is not None and approximation != result_text:
        response["approximation"] = approximation
    return response


def out_of_scope(topic: str = "") -> dict[str, Any]:
    return {
        "ok": True,
        "message": (
            "I can help with mathematics questions and calculations. "
            "Please ask a math question, such as “What is 18% of 250?”"
        ),
    }


def handle_errors(error_type: str, details: str = "") -> dict[str, Any]:
    messages = {
        "division_by_zero": "Division by zero is undefined.",
        "invalid_expression": "I couldn't interpret that as a supported arithmetic expression.",
        "unsafe_expression": "That expression uses unsupported or unsafe math syntax.",
        "numeric_limit": "That calculation exceeds the safe numeric limits.",
        "tool_call_error": "The calculation request was incomplete or malformed.",
        "tool_call_limit": "I reached the limit of 10 tool calls for this question.",
    }
    return {
        "ok": False,
        "message": messages.get(
            error_type,
            "I couldn't complete that calculation because a tool encountered an error.",
        ),
    }


def _classify_math_error(error: Exception) -> tuple[str, str]:
    if isinstance(error, ZeroDivisionError):
        return "division_by_zero", str(error)
    if isinstance(error, MathInputError):
        if (
            "too large" in str(error)
            or "numeric range" in str(error)
            or "Exponents" in str(error)
            or "limited to inputs" in str(error)
        ):
            return "numeric_limit", str(error)
        if "not valid" in str(error) or "non-empty" in str(error):
            return "invalid_expression", str(error)
        return "unsafe_expression", str(error)
    if isinstance(error, OverflowError):
        return "numeric_limit", str(error)
    return "tool_call_error", str(error)


def _dispatch_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "evaluate_math":
        try:
            expression = arguments.get("expression")
            return evaluate_math(expression)
        except (MathInputError, ArithmeticError, TypeError) as error:
            error_type, details = _classify_math_error(error)
            return {
                "ok": False,
                "error_type": error_type,
                "details": details,
            }

    if name == "out_of_scope":
        return out_of_scope(str(arguments.get("topic", "")))

    if name == "handle_errors":
        error_type = arguments.get("error_type")
        if not isinstance(error_type, str):
            return handle_errors("tool_call_error")
        details = arguments.get("details", "")
        return handle_errors(
            error_type,
            details if isinstance(details, str) else "",
        )

    return {
        "ok": False,
        "error_type": "tool_call_error",
        "details": f"Unknown tool: {name}",
    }


def request_completion(
    api_key: str, messages: list[dict[str, Any]]
) -> dict[str, Any]:
    request = Request(
        CHAT_COMPLETIONS_URL,
        data=json.dumps(
            {
                "model": MODEL_ID,
                "messages": messages,
                "tools": TOOLS,
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


def _tool_error_result(error: str) -> dict[str, Any]:
    return {
        "ok": False,
        "error_type": "tool_call_error",
        "details": error,
    }


def _show_tool_step(
    tool_call_number: int,
    name: str,
    arguments: dict[str, Any],
    result: dict[str, Any],
) -> None:
    call = {"tool": name, "arguments": arguments}
    console.print(
        Panel(
            Syntax(
                json.dumps(call, indent=2, ensure_ascii=False),
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

    succeeded = result.get("ok") is True
    console.print(
        Panel(
            Syntax(
                json.dumps(result, indent=2, ensure_ascii=False),
                "json",
                theme="monokai",
                word_wrap=True,
            ),
            title=Text(
                "Tool result",
                style="bold green" if succeeded else "bold red",
            ),
            border_style="green" if succeeded else "red",
            padding=(0, 1),
        )
    )


def _show_welcome() -> None:
    console.print(
        Panel(
            Text(
                "Ask a natural-language math question.\n"
                f"Up to {MAX_TOOL_CALLS} tool calls are allowed per question.",
                justify="center",
            ),
            title=Text("NVIDIA Math Agent", style="bold cyan"),
            subtitle=Text(MODEL_ID, style="dim"),
            border_style="cyan",
            padding=(1, 2),
        )
    )

    tools = Table(
        title="Available tools",
        box=box.ROUNDED,
        header_style="bold cyan",
        border_style="blue",
    )
    tools.add_column("Tool", style="bold")
    tools.add_column("Purpose")
    tools.add_row("evaluate_math", "Calculate with SymPy")
    tools.add_row("out_of_scope", "Respond to non-math requests")
    tools.add_row("handle_errors", "Explain genuine tool errors")
    console.print(tools)
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


def run_agent(api_key: str, question: str, verbose: bool = False) -> str:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    tool_calls_used = 0

    while True:
        message = request_completion(api_key, messages)
        tool_calls = message.get("tool_calls", [])
        if not isinstance(tool_calls, list):
            raise ValueError("NVIDIA returned malformed tool calls.")
        if not tool_calls:
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
            raise ValueError("NVIDIA returned neither a reply nor a tool call.")

        if tool_calls_used + len(tool_calls) > MAX_TOOL_CALLS:
            return handle_errors("tool_call_limit")["message"]

        assistant_message = {
            "role": "assistant",
            "content": message.get("content"),
            "tool_calls": tool_calls,
        }
        messages.append(assistant_message)

        for tool_call in tool_calls:
            tool_calls_used += 1
            if not isinstance(tool_call, dict):
                result = _tool_error_result("Malformed tool call.")
                tool_call_id = ""
                name = "<invalid>"
                arguments = {}
            else:
                tool_call_id = tool_call.get("id")
                function = tool_call.get("function")
                if not isinstance(function, dict):
                    result = _tool_error_result("Malformed tool function.")
                    name = "<invalid>"
                    arguments = {}
                else:
                    name = function.get("name")
                    raw_arguments = function.get("arguments", "{}")
                    try:
                        arguments = json.loads(raw_arguments)
                        if not isinstance(arguments, dict):
                            raise ValueError("Tool arguments must be a JSON object.")
                        if not isinstance(name, str):
                            raise ValueError("Tool name must be a string.")
                        result = _dispatch_tool(name, arguments)
                    except (json.JSONDecodeError, TypeError, ValueError) as error:
                        arguments = {}
                        result = _tool_error_result(str(error))

            if not isinstance(tool_call_id, str) or not tool_call_id:
                raise ValueError("NVIDIA returned a tool call without an ID.")
            if verbose:
                _show_tool_step(tool_calls_used, name, arguments, result)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )


def main() -> int:
    load_dotenv(dotenv_path=ENV_PATH)
    api_key = os.getenv("NVIDIA_AI_KEY") or os.getenv("NVIDIA_API_KEY")
    if not api_key:
        _show_error(
            "NVIDIA API key not found. Set NVIDIA_AI_KEY or NVIDIA_API_KEY "
            "in the project-root .env file."
        )
        return 1

    _show_welcome()

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
            reply = run_agent(api_key, question, verbose=True)
            console.print(
                Panel(
                    Markdown(reply),
                    title=Text("Assistant", style="bold green"),
                    border_style="green",
                    padding=(1, 2),
                )
            )
        except HTTPError as error:
            _show_error(
                f"NVIDIA returned HTTP {error.code}: {error.reason}. "
                f"{handle_errors('tool_call_error')['message']}"
            )
        except URLError as error:
            _show_error(
                f"Could not connect to NVIDIA: {error.reason}. "
                f"{handle_errors('tool_call_error')['message']}"
            )
        except TimeoutError:
            _show_error(
                "The NVIDIA request timed out. "
                f"{handle_errors('tool_call_error')['message']}"
            )
        except (json.JSONDecodeError, ValueError) as error:
            _show_error(
                f"{error}. {handle_errors('tool_call_error')['message']}"
            )


if __name__ == "__main__":
    sys.exit(main())
