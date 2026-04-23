"""
mini_pascal_semantic.py
Backward-compatibility wrapper — re-exports everything from compiler.semantic
so that existing imports continue to work unchanged.

Prefer importing from the ``compiler`` package directly:
  from compiler import analyze, SemanticResult, SemanticError
"""
from compiler.semantic import analyze, SemanticResult, SemanticError  # noqa: F401
