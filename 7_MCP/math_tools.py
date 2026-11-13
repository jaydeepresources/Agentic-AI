import ast
from typing import Any

import sympy as sp


MAX_EXPRESSION_LENGTH = 512
MAX_AST_NODES = 100

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


def classify_math_error(error: Exception) -> tuple[str, str]:
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
