from __future__ import annotations

import ast
import operator


class CalcTool:
    _ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.FloorDiv: operator.floordiv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }

    def execute(self, **kwargs) -> str:
        expression = str(kwargs.get("expression", "")).strip()
        if not expression:
            return "No expression provided."
        try:
            value = self._eval(expression)
        except Exception as exc:
            return f"Calculation failed: {exc}"
        return str(value)

    def _eval(self, expression: str):
        node = ast.parse(expression, mode="eval").body
        return self._eval_node(node)

    def _eval_node(self, node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in self._ops:
            return self._ops[type(node.op)](
                self._eval_node(node.left), self._eval_node(node.right)
            )
        if isinstance(node, ast.UnaryOp) and type(node.op) in self._ops:
            return self._ops[type(node.op)](self._eval_node(node.operand))
        raise ValueError("Unsupported expression.")
