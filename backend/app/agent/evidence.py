"""What the agent has actually seen. Every claim in a final answer must point back to something in here."""
from __future__ import annotations

import ast
import operator
import re
from dataclasses import dataclass, field

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}


class CalcError(ValueError):
    pass


@dataclass
class Evidence:
    facts: dict[str, dict] = field(default_factory=dict)   # F1, F2 ...: one figure from the SEC's structured data
    calcs: dict[str, dict] = field(default_factory=dict)   # K1, K2 ...: one calculation and its result
    texts: dict[str, str] = field(default_factory=dict)    # T1, T2 ...: filing text the agent was shown
    _counts: dict[str, int] = field(default_factory=lambda: {"F": 0, "K": 0, "T": 0})

    def _next(self, prefix: str) -> str:
        self._counts[prefix] += 1
        return f"{prefix}{self._counts[prefix]}"

    def add_fact(self, row: dict) -> str:
        key = self._next("F")
        self.facts[key] = row
        return key

    def add_text(self, text: str, meta: dict | None = None) -> str:
        key = self._next("T")
        self.texts[key] = text
        return key

    def value_of(self, ref: str) -> float | None:
        if ref in self.facts:
            return float(self.facts[ref]["value"])
        if ref in self.calcs:
            return float(self.calcs[ref]["result"])
        return None

    def calculate(self, expression: str) -> tuple[str, float]:
        """Plain arithmetic over earlier figures (F#) and results (K#). Nothing else is allowed."""
        if len(expression) > 200:
            raise CalcError("That expression is too long.")
        used: list[str] = []

        def walk(node: ast.AST) -> float:
            if isinstance(node, ast.Expression):
                return walk(node.body)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                return float(node.value)
            if isinstance(node, ast.Name):
                value = self.value_of(node.id)
                if value is None:
                    raise CalcError(f"'{node.id}' is not a figure you have retrieved. Use ids like F1 or K1.")
                used.append(node.id)
                return value
            if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
                inner = walk(node.operand)
                return -inner if isinstance(node.op, ast.USub) else inner
            if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
                left, right = walk(node.left), walk(node.right)
                if isinstance(node.op, ast.Div) and right == 0:
                    raise CalcError("Division by zero.")
                return _OPS[type(node.op)](left, right)
            raise CalcError("Only numbers, F#/K# ids and + - * / ( ) are allowed.")

        try:
            result = walk(ast.parse(expression.strip(), mode="eval"))
        except SyntaxError as error:
            raise CalcError("That is not a valid arithmetic expression.") from error
        key = self._next("K")
        self.calcs[key] = {"expression": expression.strip(), "result": result, "inputs": sorted(set(used))}
        return key, result


def normalize(text: str) -> str:
    """Make quotes comparable: same case, same spacing, straight quotes and dashes."""
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-").replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip().lower()
