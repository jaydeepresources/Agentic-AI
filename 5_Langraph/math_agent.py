import ast
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

import sympy as sp
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.types import Command, interrupt
from openai import OpenAIError
from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text


ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
CHAT_COMPLETIONS_URL = "https://integrate.api.nvidia.com/v1"
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
    "based on that result. Use the conversation history to understand follow-up "
    "questions. Do not treat ordinary ambiguity as a technical error; ask a "
    "concise clarifying question if the math problem cannot be translated into "
    "a definite expression."
)

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


class AgentState(MessagesState):
    tool_calls_used: int
    tool_decisions: dict[str, bool]


def _evaluate_node(node: ast.expr, node_count: list[int]) -> Any:
    node_count[0] += 1
    if node_count[0] > MAX_AST_NODES:
        raise ValueError("The expression is too complex.")

    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return sp.Rational(str(node.value))

    if isinstance(node, ast.Name):
        if node.id.startswith("__"):
            raise ValueError("Names beginning with underscores are not supported.")
        return _CONSTANTS.get(node.id, sp.Symbol(node.id))

    if isinstance(node, (ast.Tuple, ast.List)):
        return [_evaluate_node(element, node_count) for element in node.elts]

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        function = _FUNCTIONS.get(node.func.id)
        if function is None or node.keywords:
            raise ValueError("That math function is not supported.")
        arguments = [_evaluate_node(argument, node_count) for argument in node.args]
        if node.func.id == "factorial" and len(arguments) == 1:
            argument = arguments[0]
            if not isinstance(argument, sp.Basic) or argument.is_Integer is not True:
                raise ValueError("Factorial requires a non-negative integer.")
            if argument < 0:
                raise ValueError("Factorial requires a non-negative integer.")
            if argument > 1000:
                raise ValueError("Factorials are limited to inputs of 1000.")
        return function(*arguments)

    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        value = _evaluate_node(node.operand, node_count)
        return _UNARY_OPERATORS[type(node.op)](value)

    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate_node(node.left, node_count)
        right = _evaluate_node(node.right, node_count)
        if not isinstance(left, sp.Basic) or not isinstance(right, sp.Basic):
            raise ValueError("Arithmetic operators require scalar expressions.")
        if (
            isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod))
            and right.is_zero is True
        ):
            raise ZeroDivisionError("division by zero")
        if isinstance(node.op, ast.Pow) and right.is_number and bool(abs(right) > 100):
            raise ValueError("Exponents must be between -100 and 100.")
        return _BINARY_OPERATORS[type(node.op)](left, right)

    raise ValueError("Use only mathematical expressions and supported functions.")


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
        raise ValueError("Enter a non-empty math expression.")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise ValueError("The expression is too long.")

    try:
        parsed = ast.parse(expression, mode="eval")
    except SyntaxError as error:
        raise ValueError("The math expression is not valid.") from error

    result_text, approximation = _format_result(_evaluate_node(parsed.body, [0]))
    response: dict[str, Any] = {
        "ok": True,
        "expression": expression,
        "result": result_text,
    }
    if approximation is not None and approximation != result_text:
        response["approximation"] = approximation
    return response


def _classify_math_error(error: Exception) -> tuple[str, str]:
    if isinstance(error, ZeroDivisionError):
        return "division_by_zero", str(error)
    if isinstance(error, ValueError):
        details = str(error)
        if (
            "too large" in details
            or "numeric range" in details
            or "Exponents" in details
            or "limited to inputs" in details
        ):
            return "numeric_limit", details
        if "not valid" in details or "non-empty" in details:
            return "invalid_expression", details
        return "unsafe_expression", details
    if isinstance(error, OverflowError):
        return "numeric_limit", str(error)
    return "tool_call_error", str(error)


@tool("evaluate_math")
def evaluate_math_tool(expression: str) -> dict[str, Any]:
    """Evaluate a math expression using arithmetic and supported SymPy functions."""
    try:
        return evaluate_math(expression)
    except (ValueError, ArithmeticError, TypeError) as error:
        error_type, details = _classify_math_error(error)
        return {"ok": False, "error_type": error_type, "details": details}


@tool("out_of_scope")
def out_of_scope_tool(topic: str) -> dict[str, Any]:
    """Respond when the user's request is not about mathematics."""
    return {
        "ok": True,
        "message": (
            "I can help with mathematics questions and calculations. "
            "Please ask a math question, such as “What is 18% of 250?”"
        ),
    }


@tool("handle_errors")
def handle_errors_tool(error_type: str, details: str = "") -> dict[str, Any]:
    """Explain a genuine error reported by another tool."""
    messages = {
        "division_by_zero": "Division by zero is undefined.",
        "invalid_expression": (
            "I couldn't interpret that as a supported arithmetic expression."
        ),
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


TOOLS = [evaluate_math_tool, out_of_scope_tool, handle_errors_tool]
_TOOLS_BY_NAME = {math_tool.name: math_tool for math_tool in TOOLS}


def _latest_tool_calls(state: AgentState) -> list[dict[str, Any]]:
    messages = state["messages"]
    if not messages or not isinstance(messages[-1], AIMessage):
        return []
    return messages[-1].tool_calls


def _tool_limit_messages(tool_calls: list[dict[str, Any]]) -> list[ToolMessage]:
    return [
        ToolMessage(
            content=json.dumps(
                {
                    "ok": False,
                    "error_type": "tool_call_limit",
                    "details": f"At most {MAX_TOOL_CALLS} tool calls are allowed per question.",
                }
            ),
            name=call["name"],
            tool_call_id=call["id"],
        )
        for call in tool_calls
    ]


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "\n".join(
            block["text"]
            for block in content
            if isinstance(block, dict) and isinstance(block.get("text"), str)
        ).strip()
    return ""


def create_math_agent(
    api_key: str,
    *,
    model: Any | None = None,
    checkpointer: Any | None = None,
):
    chat_model = model or ChatOpenAI(
        model=MODEL_ID,
        base_url=CHAT_COMPLETIONS_URL,
        api_key=api_key,
        max_tokens=1024,
        timeout=120,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    tool_model = chat_model.bind_tools(TOOLS)

    def call_model(state: AgentState) -> dict[str, list[AnyMessage]]:
        response = tool_model.invoke(
            [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
        )
        return {"messages": [response]}

    def review_tool_calls(state: AgentState) -> dict[str, Any]:
        tool_calls = _latest_tool_calls(state)
        if state["tool_calls_used"] + len(tool_calls) > MAX_TOOL_CALLS:
            limit_messages = _tool_limit_messages(tool_calls)
            limit_messages.append(
                AIMessage(
                    content=(
                        f"I reached the limit of {MAX_TOOL_CALLS} tool calls "
                        "for this question."
                    )
                )
            )
            return {
                "messages": limit_messages,
                "tool_calls_used": MAX_TOOL_CALLS,
                "tool_decisions": {},
            }

        decisions: dict[str, bool] = {}
        for call in tool_calls:
            decision = interrupt(
                {
                    "tool_name": call["name"],
                    "arguments": call["args"],
                }
            )
            if not isinstance(decision, bool):
                raise ValueError("A tool review must resume with an approval decision.")
            decisions[call["id"]] = decision
        return {"tool_decisions": decisions}

    def execute_approved_tools(state: AgentState) -> dict[str, Any]:
        messages: list[ToolMessage] = []
        tool_calls = _latest_tool_calls(state)
        for call in tool_calls:
            if state["tool_decisions"].get(call["id"], False):
                result = _TOOLS_BY_NAME[call["name"]].invoke(call["args"])
                content = json.dumps(result, ensure_ascii=False, default=str)
            else:
                content = json.dumps(
                    {
                        "ok": False,
                        "message": "The human reviewer rejected this tool call; it was not executed.",
                    }
                )
            messages.append(
                ToolMessage(
                    content=content,
                    name=call["name"],
                    tool_call_id=call["id"],
                )
            )
        return {
            "messages": messages,
            "tool_calls_used": state["tool_calls_used"] + len(tool_calls),
            "tool_decisions": {},
        }

    def route_after_model(state: AgentState) -> str:
        return "review" if _latest_tool_calls(state) else "end"

    def route_after_review(state: AgentState) -> str:
        latest = state["messages"][-1]
        if isinstance(latest, AIMessage) and not latest.tool_calls:
            return "end"
        return "execute"

    builder = StateGraph(AgentState)
    builder.add_node("model", call_model)
    builder.add_node("review_tools", review_tool_calls)
    builder.add_node("execute_tools", execute_approved_tools)
    builder.add_edge(START, "model")
    builder.add_conditional_edges(
        "model",
        route_after_model,
        {"review": "review_tools", "end": END},
    )
    builder.add_conditional_edges(
        "review_tools",
        route_after_review,
        {"execute": "execute_tools", "end": END},
    )
    builder.add_edge("execute_tools", "model")
    return builder.compile(checkpointer=checkpointer or InMemorySaver())


def run_turn(
    graph: Any,
    question: str,
    thread_id: str,
    approve_tool: Callable[[dict[str, Any]], bool],
) -> str:
    config = {"configurable": {"thread_id": thread_id}}
    result = graph.invoke(
        {
            "messages": [HumanMessage(content=question)],
            "tool_calls_used": 0,
            "tool_decisions": {},
        },
        config,
    )
    while result.get("__interrupt__"):
        pending = result["__interrupt__"][0].value
        result = graph.invoke(
            Command(resume=approve_tool(pending)),
            config,
        )

    messages = result.get("messages")
    if not isinstance(messages, list):
        raise ValueError("LangGraph returned no conversation messages.")
    final_message = next(
        (
            message
            for message in reversed(messages)
            if isinstance(message, AIMessage) and not message.tool_calls
        ),
        None,
    )
    if final_message is None:
        raise ValueError("LangGraph returned no assistant response.")
    reply = _message_text(final_message.content)
    if not reply:
        raise ValueError("LangGraph returned an empty assistant response.")
    return reply


def _approve_tool_call(request: dict[str, Any]) -> bool:
    console.print(
        Panel(
            json.dumps(request["arguments"], indent=2, ensure_ascii=False, default=str),
            title=f"Tool approval required: {request['tool_name']}",
            border_style="yellow",
        )
    )
    answer = Prompt.ask(
        "[bold yellow]Approve this tool call?[/]",
        choices=["y", "n"],
        default="n",
    )
    return answer == "y"


def _show_welcome() -> None:
    console.print(
        Panel(
            Text(
                "Ask natural-language math questions. Each tool call pauses for "
                "your approval, and this session remembers earlier questions.",
                justify="center",
            ),
            title=Text("LangGraph NVIDIA Math Agent", style="bold cyan"),
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
    console.print(
        "[dim]Type /exit or /quit to leave. Approve each tool call with y or n.[/]\n"
    )


def _show_error(message: str) -> None:
    console.print(
        Panel(
            Text(message),
            title=Text("Request failed", style="bold red"),
            border_style="red",
            padding=(0, 1),
        )
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
    graph = create_math_agent(api_key)
    thread_id = "interactive-session"
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
            reply = run_turn(graph, question, thread_id, _approve_tool_call)
            console.print(
                Panel(
                    Markdown(reply),
                    title=Text("Assistant", style="bold green"),
                    border_style="green",
                    padding=(1, 2),
                )
            )
        except OpenAIError as error:
            _show_error(f"NVIDIA request failed: {error}")
        except ValueError as error:
            _show_error(str(error))


if __name__ == "__main__":
    sys.exit(main())
