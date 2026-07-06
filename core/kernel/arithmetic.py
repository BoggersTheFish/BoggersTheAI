"""Structurally safe arithmetic parsing and evaluation."""

from __future__ import annotations

import ast
import operator
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


class ArithmeticParseError(ValueError):
    """Raised when input is outside the arithmetic grammar."""


_OPS: dict[type[ast.AST], Callable[..., int | float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


@dataclass(frozen=True, slots=True)
class ArithmeticReceipt:
    expression: str
    parsed_kind: str
    computed: Any
    expected: Any
    passed: bool


class SafeArithmeticEvaluator:
    """Allowlisted AST evaluator for integer arithmetic propositions."""

    def evaluate_expression(self, expression: str) -> int | float:
        expression = expression.strip()
        if not expression:
            raise ArithmeticParseError("empty arithmetic expression")
        try:
            parsed = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            raise ArithmeticParseError(str(exc)) from exc
        return self._eval_node(parsed.body)

    def verify(self, proposition: str) -> ArithmeticReceipt:
        expr = proposition.strip()
        lower = expr.lower()

        parity = re.fullmatch(r"(.+?)\s+is\s+(even|odd)", lower)
        if parity:
            value = self.evaluate_expression(parity.group(1))
            if not isinstance(value, int) or isinstance(value, bool):
                raise ArithmeticParseError("parity requires an integer expression")
            expected_even = parity.group(2) == "even"
            computed = value % 2 == 0
            return ArithmeticReceipt(
                expression=expr,
                parsed_kind="parity",
                computed=computed,
                expected=expected_even,
                passed=computed == expected_even,
            )

        divisibility = re.fullmatch(r"(.+?)\s+is\s+divisible\s+by\s+(.+)", lower)
        if divisibility is None:
            divisibility = re.fullmatch(r"(.+?)\s+divisible\s+by\s+(.+)", lower)
        if divisibility:
            left = self.evaluate_expression(divisibility.group(1))
            right = self.evaluate_expression(divisibility.group(2))
            if (
                not isinstance(left, int)
                or isinstance(left, bool)
                or not isinstance(right, int)
                or isinstance(right, bool)
            ):
                raise ArithmeticParseError("divisibility requires integers")
            if right == 0:
                raise ArithmeticParseError("division by zero")
            computed = left % right == 0
            return ArithmeticReceipt(
                expression=expr,
                parsed_kind="divisibility",
                computed=computed,
                expected=True,
                passed=computed,
            )

        if "=" in expr and "==" not in expr:
            left_raw, right_raw = expr.split("=", 1)
            left = self.evaluate_expression(left_raw)
            right = self.evaluate_expression(right_raw)
            return ArithmeticReceipt(
                expression=expr,
                parsed_kind="equality",
                computed=left,
                expected=right,
                passed=left == right,
            )

        value = self.evaluate_expression(expr)
        return ArithmeticReceipt(
            expression=expr,
            parsed_kind="truthy_expression",
            computed=value,
            expected=True,
            passed=bool(value),
        )

    def _eval_node(self, node: ast.AST) -> int | float:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise ArithmeticParseError(
                    "only integer and float literals are allowed"
                )
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            op = _OPS[type(node.op)]
            return op(self._eval_node(node.left), self._eval_node(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            op = _OPS[type(node.op)]
            return op(self._eval_node(node.operand))
        raise ArithmeticParseError(
            f"unsupported arithmetic syntax: {node.__class__.__name__}"
        )
